import asyncio
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from sonar.feed_probe import ProbeStats, collect, init_db, parse_event


def launch(mint: str = "mint-1", *, pool: str = "pump", timestamp: float = 1_791_000_000_000) -> str:
    return json.dumps({
        "txType": "create", "pool": pool, "poolId": "pool-1", "mint": mint,
        "timestamp": timestamp, "signature": "signature-1",
    })


class ProbeTest(unittest.TestCase):
    def test_parsing_and_malformed_messages(self):
        event = parse_event(launch())
        self.assertEqual((event.kind, event.pool, event.pool_id, event.mint), ("create", "pump", "pool-1", "mint-1"))
        self.assertEqual(event.signature, "signature-1")
        self.assertEqual(parse_event(launch(pool="pump-amm")).pool, "pump-amm")
        self.assertEqual(parse_event(launch().replace('"txType"', '"action"').encode()).kind, "create")
        with closing(sqlite3.connect(":memory:")) as db:
            init_db(db, compare_portal=False)
            stats = ProbeStats(db)
            for message in ('not JSON', '[]', '{}', '{"txType":"create","pool":"pump"}', '{"txType":"buy","timestamp":true}'):
                stats.observe(message)
            self.assertEqual(stats.malformed, 5)
            self.assertEqual(stats.messages, 5)
            self.assertFalse(stats.counts)

    def test_launch_deduplication_and_age(self):
        with closing(sqlite3.connect(":memory:")) as db:
            init_db(db, compare_portal=False)
            stats = ProbeStats(db)
            stats.observe(launch(), now_ms=1_791_000_001_000)
            stats.observe(launch(), now_ms=1_791_000_002_000)
            stats.observe(launch("mint-2"), now_ms=1_791_000_003_000)
            self.assertEqual(stats.unique_pump_launches, 2)
            self.assertEqual(stats.duplicate_pump_launches, 1)
            self.assertEqual(stats.counts[("create", "pump")], 3)
            self.assertEqual(stats.report()["event_age_ms_approx"]["p50"], 2000)

    def test_late_arrival_and_duplicate_use_first_receipt(self):
        with closing(sqlite3.connect(":memory:")) as db:
            init_db(db, compare_portal=True)
            stats = ProbeStats(db, compare_portal=True, duration_s=180, warmup_s=60, grace_s=90)
            start, end = stats.window_start_ms, stats.window_end_ms
            stats.portal_subscriptions = 1
            stats.set_connected("pump", True, now_ms=start - 30_000)
            stats.set_connected("portal", True, now_ms=start - 30_000)
            portal = json.dumps({"txType": "create", "pool": "pump", "mint": "late", "signature": "signature-1"})
            stats.observe_portal(portal, now_ms=end - 30_000)
            stats.observe(launch("late", timestamp=end - 30_000), now_ms=end + 45_000)
            stats.observe(launch("late", timestamp=end - 30_000), now_ms=end + 55_000)
            comparison = stats.comparison_report(end + 90_000)
            self.assertEqual(comparison["portal"]["matched"], 1)
            self.assertEqual(comparison["portal"]["late_in_grace"], 1)
            self.assertEqual(comparison["pump_minus_portal_arrival_ms"]["p50"], 75_000)
            self.assertEqual(stats.duplicate_pump_launches, 1)
            self.assertEqual(db.execute("SELECT signature, receipt_ms FROM launches WHERE provider='portal'").fetchone(),
                             ("signature-1", end - 30_000))

    def test_boundaries_outages_and_pool_labels_are_distinct(self):
        with closing(sqlite3.connect(":memory:")) as db:
            init_db(db, compare_portal=True)
            stats = ProbeStats(db, compare_portal=True, duration_s=300, warmup_s=60, grace_s=90)
            start, end = stats.window_start_ms, stats.window_end_ms
            stats.portal_subscriptions = 1
            stats.set_connected("pump", True, now_ms=start - 30_000)
            stats.set_connected("portal", True, now_ms=start - 30_000)
            def portal(mint: str, when: float, pool: str = "pump") -> None:
                stats.observe_portal(json.dumps({"txType": "create", "pool": pool, "mint": mint}), now_ms=when)
            portal("left", start + 10_000)
            portal("right", end - 10_000)
            portal("healthy-missing", start + 90_000)
            portal("wrong-pool", start + 150_000)
            stats.observe(launch("wrong-pool", pool="pump-amm", timestamp=start + 150_000),
                          now_ms=start + 151_000)
            stats.set_connected("pump", False, now_ms=start + 200_000)
            portal("during-outage", start + 220_000)
            stats.set_connected("pump", True, now_ms=start + 240_000)
            portal("not-a-pump-launch", start + 250_000, pool="pump-amm")
            result = stats.comparison_report(end + 90_000)["portal"]
            self.assertEqual(result["in_window"], 5)
            self.assertEqual(result["window_boundary"], 2)
            self.assertEqual(result["pool_label_mismatch"], 1)
            self.assertEqual(result["connection_outage"], 1)
            self.assertEqual(result["unexplained"], 1)
            self.assertEqual(stats.counts[("create", "pump-amm")], 1)

    def test_conflicting_launch_signatures_are_not_matched(self):
        with closing(sqlite3.connect(":memory:")) as db:
            init_db(db, compare_portal=True)
            stats = ProbeStats(db, compare_portal=True, duration_s=300, warmup_s=60, grace_s=90)
            start = stats.window_start_ms
            stats.set_connected("pump", True, now_ms=start - 30_000)
            stats.set_connected("portal", True, now_ms=start - 30_000)
            stats.observe_portal(json.dumps({"txType": "create", "pool": "pump", "mint": "same-mint",
                                             "signature": "other-signature"}), now_ms=start + 150_000)
            stats.observe(launch("same-mint", timestamp=start + 150_000), now_ms=start + 151_000)
            result = stats.comparison_report(start + 390_000)["portal"]
            self.assertEqual(result.get("matched", 0), 0)
            self.assertEqual(result["signature_conflict"], 1)

    def test_warmup_launch_can_match_window_arrival(self):
        with closing(sqlite3.connect(":memory:")) as db:
            init_db(db, compare_portal=True)
            stats = ProbeStats(db, compare_portal=True, duration_s=180, warmup_s=60, grace_s=90)
            start = stats.window_start_ms
            stats.set_connected("pump", True, now_ms=start - 30_000)
            stats.set_connected("portal", True, now_ms=start - 30_000)
            stats.observe(launch("boundary", timestamp=start - 10_000), now_ms=start - 10_000)
            stats.observe_portal(json.dumps({"txType": "create", "pool": "pump", "mint": "boundary",
                                             "signature": "signature-1"}), now_ms=start + 10_000)
            result = stats.comparison_report(start + 270_000)["portal"]
            self.assertEqual(result["matched"], 1)
            self.assertEqual(result.get("unmatched", 0), 0)


class ReconnectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_reconnects_when_pumpapi_stops_sending(self):
        active = 0
        max_active = 0

        class FakeSocket:
            def __init__(self, silent: bool):
                self.silent = silent

            async def __aenter__(self):
                nonlocal active, max_active
                active += 1
                max_active = max(max_active, active)
                return self

            async def __aexit__(self, *_):
                nonlocal active
                active -= 1

            async def recv(self):
                await asyncio.sleep(60 if self.silent else 0.005)
                return launch()

        attempts = 0

        def connector(*_, **__):
            nonlocal attempts
            attempts += 1
            return FakeSocket(silent=attempts == 1)

        with tempfile.TemporaryDirectory() as temp, closing(sqlite3.connect(":memory:")) as db:
            init_db(db, compare_portal=False)
            stats = ProbeStats(db)
            output = Path(temp) / "summary.json"
            with patch("sonar.feed_probe.PUMP_IDLE_TIMEOUT_S", 0.02):
                await collect(stats, 0.08, output, connector=connector, initial_backoff=0.001)
            self.assertEqual(stats.connections, 2)
            self.assertEqual(stats.idle_reconnects, 1)
            self.assertEqual(stats.disconnects, 1)
            self.assertEqual(stats.connection_error_types["TimeoutError"], 1)
            self.assertGreater(stats.messages, 0)
            self.assertEqual(max_active, 1)
            self.assertEqual(active, 0)
            self.assertEqual(json.loads(output.read_text())["idle_reconnects"], 1)

    async def test_reconnects_and_deduplicates_replayed_launch(self):
        class FakeSocket:
            def __init__(self, drop: bool):
                self.drop = drop
                self.sent = False

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                pass

            async def recv(self):
                if not self.sent:
                    self.sent = True
                    return launch()
                if self.drop:
                    raise OSError("connection dropped")
                await asyncio.sleep(60)

        attempts = 0

        def connector(*_, **__):
            nonlocal attempts
            attempts += 1
            return FakeSocket(drop=attempts == 1)

        with tempfile.TemporaryDirectory() as temp, closing(sqlite3.connect(":memory:")) as db:
            init_db(db, compare_portal=False)
            stats = ProbeStats(db)
            await collect(stats, 0.05, Path(temp) / "summary.json", connector=connector, initial_backoff=0.001)
            self.assertEqual(stats.connections, 2)
            self.assertEqual(stats.disconnects, 1)
            self.assertEqual(stats.connection_error_types["OSError"], 1)
            self.assertEqual(stats.unique_pump_launches, 1)
            self.assertEqual(stats.duplicate_pump_launches, 1)


if __name__ == "__main__":
    unittest.main()
