import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sonar import main
from sonar.pumpportal import Launch, save_launch
from sonar.signals import signal_view


NOW = 1_800_000_000_000
POOL = "D" * 32


class CandidatesTest(unittest.IsolatedAsyncioTestCase):
    def test_signal_baseline_requires_coverage_and_fresh_price(self):
        self.assertIsNone(signal_view(NOW, 2, NOW, "fresh", [(NOW - 30_000, 1)], [])
                          ["price_change_1m_pct"])
        self.assertIsNone(signal_view(NOW, 2, NOW, "stale", [(NOW - 60_000, 1)], [])
                          ["price_change_1m_pct"])
        self.assertIsNone(signal_view(NOW, 1e300, NOW, "fresh", [(NOW - 60_000, 1e-300)], [])
                          ["price_change_1m_pct"])
        self.assertEqual(signal_view(NOW, 2, NOW + 1000, "fresh", [(NOW - 59_000, 1)],
                                     [(NOW + 60_000, 3, 0)])["observed_buys_1m_approx"], 0)

    async def test_price_states_and_pool_change(self):
        with tempfile.TemporaryDirectory() as root, patch.dict("os.environ", {"SONAR_PUMPPORTAL_ENABLED": "0", "SONAR_SHRINE_ENABLED": "0", "SONAR_RISK_ENABLED": "0"}), \
                patch.object(main, "DATA_DIR", Path(root)), patch.object(main, "DB_PATH", Path(root) / "sonar.db"), \
                patch.object(main.time, "time_ns", return_value=NOW * 1_000_000):
            async with main.lifespan(main.app):
                for index, mint in enumerate(("A" * 32, "B" * 32, "C" * 32)):
                    save_launch(main.DB_PATH, Launch(mint, "launch", "pump", POOL, None), NOW - 3000 + index)
                with sqlite3.connect(main.DB_PATH) as db:
                    db.execute("""UPDATE candidates SET price = 1, price_unit = 'USD', price_source = 'shrine',
                               price_source_ms = ?, price_seen_ms = ? WHERE mint = ?""",
                               (NOW - 1000, NOW - 500, "A" * 32))
                    db.execute("""UPDATE candidates SET price = 2, price_unit = 'USD', price_source = 'shrine',
                               price_source_ms = ?, price_seen_ms = ? WHERE mint = ?""",
                               (NOW - 31_000, NOW - 500, "B" * 32))
                    db.executemany(
                        "INSERT INTO price_samples VALUES (?, ?, ?, ?, ?, ?)",
                        [("A" * 32, POOL, timestamp // 10_000 * 10_000, sample_price, timestamp, timestamp)
                         for timestamp, sample_price in ((NOW - 61_000, 0.5), (NOW - 301_000, 0.25))],
                    )
                    db.executemany(
                        "INSERT INTO trade_minutes VALUES (?, ?, ?, ?, ?)",
                        [("A" * 32, POOL, NOW - 60_000, 2, 1),
                         ("A" * 32, POOL, NOW - 240_000, 3, 4)],
                    )
                rows = {row["mint"]: row for row in main.candidates()}
                self.assertEqual(rows["A" * 32]["price_status"], "fresh")
                self.assertEqual(rows["A" * 32]["price_age_ms"], 1000)
                self.assertEqual(rows["A" * 32]["signals"]["price_change_1m_pct"], 100)
                self.assertEqual(rows["A" * 32]["signals"]["price_change_5m_pct"], 300)
                self.assertEqual(rows["A" * 32]["signals"]["observed_buys_1m_approx"], 2)
                self.assertEqual(rows["A" * 32]["signals"]["observed_sells_5m_approx"], 5)
                self.assertEqual(rows["A" * 32]["risk"]["status"], "waiting")
                self.assertEqual(rows["B" * 32]["price_status"], "stale")
                self.assertIsNone(rows["B" * 32]["signals"]["price_change_1m_pct"])
                self.assertEqual(rows["C" * 32]["price_status"], "unavailable")
                self.assertIsNone(rows["C" * 32]["price_usd"])

                save_launch(main.DB_PATH, Launch("A" * 32, "migrate", "pump-amm", "E" * 32, None), NOW)
                self.assertEqual({row["mint"]: row for row in main.candidates()}["A" * 32]["price_status"], "unavailable")
                self.assertIsNone({row["mint"]: row for row in main.candidates()}["A" * 32]["signals"]["price_change_1m_pct"])
                with sqlite3.connect(main.DB_PATH) as db:
                    db.execute("""UPDATE candidates SET price = 3, price_unit = 'USD', price_source = 'shrine',
                               price_source_ms = ?, price_seen_ms = ? WHERE mint = ?""",
                               (NOW - 100, NOW - 100, "A" * 32))
                save_launch(main.DB_PATH, Launch("A" * 32, "migrate", "pump-amm", "E" * 32, None), NOW + 1)
                self.assertEqual({row["mint"]: row for row in main.candidates()}["A" * 32]["price_usd"], 3)
                save_launch(main.DB_PATH, Launch("A" * 32, "migrate", "unknown-amm", None, None), NOW + 2)
                row = {row["mint"]: row for row in main.candidates()}["A" * 32]
                self.assertEqual(row["price_status"], "unavailable")
                self.assertIsNone(row["pool_id"])


if __name__ == "__main__":
    unittest.main()
