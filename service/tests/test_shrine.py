import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sonar import main
from sonar.pumpportal import Launch, save_launch
from sonar.shrine import frame_event, save_price, save_trade


MINT = "A" * 32
POOL = "B" * 32
OTHER = "C" * 32


class ShrineTest(unittest.IsolatedAsyncioTestCase):
    async def test_price_trade_validation_and_pool_identity(self):
        with tempfile.TemporaryDirectory() as root, patch.dict("os.environ", {"SONAR_PUMPPORTAL_ENABLED": "0", "SONAR_SHRINE_ENABLED": "0", "SONAR_RISK_ENABLED": "0"}), \
                patch.object(main, "DATA_DIR", Path(root)), patch.object(main, "DB_PATH", Path(root) / "sonar.db"):
            async with main.lifespan(main.app):
                save_launch(main.DB_PATH, Launch(MINT, "launch", "PUMPFUN", POOL, 1_800_000_000_000), 1_800_000_000_000, "shrine")
                self.assertEqual(frame_event('42["token_update",{"pool":"x"}]'), ("token_update", {"pool": "x"}))
                self.assertIsNone(frame_event('42["token_update"]'))
                price = {"priceUSD": 0.0001, "time": 1_800_000_000}
                self.assertTrue(save_price(main.DB_PATH, POOL, price, 1_800_000_001_000))
                self.assertFalse(save_price(main.DB_PATH, OTHER, price, 1_800_000_001_000))
                self.assertFalse(save_price(main.DB_PATH, POOL, {"priceUSD": 0, "time": 1_800_000_001}, 1_800_000_002_000))
                self.assertTrue(save_price(main.DB_PATH, POOL, {"priceUSD": 0.0002, "time": 1_800_000_001}, 1_800_000_002_000))
                self.assertFalse(save_price(main.DB_PATH, POOL, price, 1_800_000_003_000))
                trade = {"mint": MINT, "timestamp": 1_800_000_001, "is_buy": True}
                self.assertTrue(save_trade(main.DB_PATH, POOL, trade, 1_800_000_002_000))
                self.assertFalse(save_trade(main.DB_PATH, OTHER, trade, 1_800_000_002_000))
                with sqlite3.connect(main.DB_PATH) as db:
                    self.assertEqual(db.execute("SELECT price, price_unit, price_source, price_source_ms FROM candidates").fetchone(),
                                     (0.0002, "USD", "shrine", 1_800_000_001_000))
                    self.assertEqual(db.execute("SELECT buys, sells FROM trade_minutes").fetchone(), (1, 0))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM price_samples").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
