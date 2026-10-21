import asyncio
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from sonar.feed_probe import ProbeStats, collect, parse_event


def launch(mint: str = "mint-1") -> str:
    return json.dumps({
        "txType": "create", "pool": "pump", "poolId": "pool-1", "mint": mint,
        "timestamp": 1_791_000_000_000,
    })


class ProbeTest(unittest.TestCase):
    def test_parsing_and_malformed_messages(self):
        event = parse_event(launch())
        self.assertEqual((event.kind, event.pool, event.pool_id, event.mint), ("create", "pump", "pool-1", "mint-1"))
        self.assertEqual(parse_event(launch().replace('"txType"', '"action"').encode()).kind, "create")
        with closing(sqlite3.connect(":memory:")) as db:
            db.execute("CREATE TABLE seen_mints (mint TEXT PRIMARY KEY)")
            stats = ProbeStats(db)
            for message in ('not JSON', '[]', '{}', '{"txType":"create","pool":"pump"}', '{"txType":"buy","timestamp":true}'):
                stats.observe(message)
            self.assertEqual(stats.malformed, 5)
            self.assertEqual(stats.messages, 5)
            self.assertFalse(stats.counts)

    def test_launch_deduplication_and_age(self):
        with closing(sqlite3.connect(":memory:")) as db:
            db.execute("CREATE TABLE seen_mints (mint TEXT PRIMARY KEY)")
            stats = ProbeStats(db)
            stats.observe(launch(), now_ms=1_791_000_001_000)
            stats.observe(launch(), now_ms=1_791_000_002_000)
            stats.observe(launch("mint-2"), now_ms=1_791_000_003_000)
            self.assertEqual(stats.unique_pump_launches, 2)
            self.assertEqual(stats.duplicate_pump_launches, 1)
            self.assertEqual(stats.counts[("create", "pump")], 3)
            self.assertEqual(stats.report()["event_age_ms_approx"]["p50"], 2000)

    def test_portal_launch_overlap_counts(self):
        with closing(sqlite3.connect(":memory:")) as db:
            db.execute("CREATE TABLE seen_mints (mint TEXT PRIMARY KEY)")
            db.execute("CREATE TABLE compare_pump (mint TEXT PRIMARY KEY)")
            db.execute("CREATE TABLE compare_portal (mint TEXT PRIMARY KEY)")
            stats = ProbeStats(db, compare_portal=True)
            stats.portal_connections = 1
            stats.set_connected("pump", True)
            stats.set_connected("portal", True)
            stats.observe(launch("shared"))
            stats.observe(launch("pump-only"))
            stats.observe_portal(json.dumps({"txType": "create", "pool": "pump", "mint": "shared"}))
            stats.observe_portal(json.dumps({"txType": "create", "pool": "pump", "mint": "portal-only"}))
            comparison = stats.report()["pumpportal_comparison"]
            self.assertEqual((comparison["shared_launches"], comparison["pump_only"], comparison["portal_only"]), (1, 1, 1))


class ReconnectionTest(unittest.IsolatedAsyncioTestCase):
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
            db.execute("CREATE TABLE seen_mints (mint TEXT PRIMARY KEY)")
            stats = ProbeStats(db)
            await collect(stats, 0.05, Path(temp) / "summary.json", connector=connector, initial_backoff=0.001)
            self.assertEqual(stats.connections, 2)
            self.assertEqual(stats.disconnects, 1)
            self.assertEqual(stats.connection_error_types["OSError"], 1)
            self.assertEqual(stats.unique_pump_launches, 1)
            self.assertEqual(stats.duplicate_pump_launches, 1)


if __name__ == "__main__":
    unittest.main()
