import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sonar import main
from sonar.pumpportal import parse_launch, save_launch


MINT = "A" * 32
PUMP_POOL = "B" * 32
MIGRATED_POOL = "C" * 32


class PumpPortalTest(unittest.IsolatedAsyncioTestCase):
    async def test_launch_migration_and_duplicate_messages(self):
        with tempfile.TemporaryDirectory() as root, patch.dict("os.environ", {"SONAR_PUMPPORTAL_ENABLED": "0", "SONAR_SHRINE_ENABLED": "0", "SONAR_RISK_ENABLED": "0"}), \
                patch.object(main, "DATA_DIR", Path(root)), patch.object(main, "DB_PATH", Path(root) / "sonar.db"):
            async with main.lifespan(main.app):
                launch = parse_launch(json.dumps({
                    "txType": "create", "mint": MINT, "pool": "pump", "poolId": PUMP_POOL,
                    "timestamp": 1_791_000_000,
                }))
                migrated = parse_launch(json.dumps({
                    "txType": "migrate", "mint": MINT, "pool": "pump-amm", "poolId": MIGRATED_POOL,
                }))
                self.assertIsNotNone(launch)
                self.assertIsNotNone(migrated)
                self.assertEqual(launch.source_ms, 1_791_000_000_000)
                self.assertIsNone(parse_launch('{"txType":"create","mint":"bad"}'))
                self.assertIsNone(parse_launch('{"txType":"buy","mint":"' + MINT + '"}'))

                save_launch(main.DB_PATH, launch, 1000)
                save_launch(main.DB_PATH, launch, 2000)
                save_launch(main.DB_PATH, migrated, 3000)
                save_launch(main.DB_PATH, migrated, 4000)
                with sqlite3.connect(main.DB_PATH) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0], 1)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM candidate_events").fetchone()[0], 2)
                    self.assertEqual(
                        db.execute("SELECT pool, pool_id, first_seen_ms FROM candidates").fetchone(),
                        ("pump-amm", MIGRATED_POOL, 1000),
                    )
