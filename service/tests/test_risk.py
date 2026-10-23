import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sonar import main
from sonar.pumpportal import Launch, save_launch
from sonar.risk import next_candidate, parse_goplus, parse_rugcheck, risk_view, save_report
from sonar.shrine import prune_history, save_price


MINT = "A" * 32
POOL = "B" * 32
NOW = 1_800_000_000_000


class RiskTest(unittest.IsolatedAsyncioTestCase):
    async def test_facts_wait_block_and_bounded_history(self):
        with tempfile.TemporaryDirectory() as root, patch.dict("os.environ", {
                "SONAR_PUMPPORTAL_ENABLED": "0", "SONAR_SHRINE_ENABLED": "0", "SONAR_RISK_ENABLED": "0"}), \
                patch.object(main, "DATA_DIR", Path(root)), patch.object(main, "DB_PATH", Path(root) / "sonar.db"):
            async with main.lifespan(main.app):
                save_launch(main.DB_PATH, Launch(MINT, "launch", "pump", POOL, None), NOW - 1000)
                self.assertTrue(save_price(main.DB_PATH, POOL, {"priceUSD": 1, "time": (NOW - 500) / 1000}, NOW))
                self.assertEqual(next_candidate(main.DB_PATH, NOW), (MINT, POOL, ["goplus", "rugcheck"]))

                status, facts = parse_goplus(MINT, {"code": 1, "result": {MINT: {
                    "mintable": {"status": "1"}, "freezable": {"status": "0"},
                    "non_transferable": 0, "default_account_state": "1", "transfer_hook": [],
                    "transfer_fee_upgradable": {"status": "0"},
                }}})
                self.assertEqual(status, "ok")
                self.assertEqual(risk_view({"goplus": (status, NOW, facts)}, NOW)["status"], "blocked")
                self.assertEqual(parse_goplus(MINT, {"code": 1, "result": {}})[0], "partial")
                save_report(main.DB_PATH, MINT, "goplus", status, facts, NOW)

                rug_status, rug_facts = parse_rugcheck({"score": 2, "risks": [], "rugged": False, "token": {
                    "mintAuthority": None, "freezeAuthority": None}, "topHolders": [{"pct": 40, "owner": MINT}],
                    "creator": MINT, "markets": [{"pubkey": POOL, "lp": {"baseUSD": 100,
                    "quoteUSD": 120, "lpLockedPct": 80}}]}, POOL)
                self.assertEqual(rug_status, "ok")
                self.assertEqual(rug_facts["pool_liquidity_usd"], 220)
                self.assertEqual(rug_facts["creator_top_holders_pct"], 40)
                save_report(main.DB_PATH, MINT, "rugcheck", rug_status, rug_facts, NOW)
                self.assertIsNone(next_candidate(main.DB_PATH, NOW))
                self.assertEqual(risk_view({"goplus": (status, NOW, facts),
                                            "rugcheck": (rug_status, NOW, rug_facts)}, NOW)["status"], "blocked")
                self.assertEqual(risk_view({"goplus": (status, NOW, facts),
                                            "rugcheck": (rug_status, NOW, rug_facts)}, NOW + 700_000)["status"], "waiting")
                second = "C" * 32
                save_launch(main.DB_PATH, Launch(second, "launch", "pump", "D" * 32, None), NOW - 500)
                self.assertTrue(save_price(main.DB_PATH, "D" * 32, {"priceUSD": 1, "time": (NOW - 100) / 1000}, NOW))
                self.assertEqual(next_candidate(main.DB_PATH, NOW)[0], second)
                for letter in "EFGHI":
                    save_report(main.DB_PATH, letter * 32, "goplus", "ok", {}, NOW)
                self.assertIsNone(next_candidate(main.DB_PATH, NOW))
                with sqlite3.connect(main.DB_PATH) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM price_samples").fetchone()[0], 2)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM risk_reports").fetchone()[0], 7)
                prune_history(main.DB_PATH, NOW + 172_800_001)
                with sqlite3.connect(main.DB_PATH) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0], 0)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM price_samples").fetchone()[0], 0)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM risk_reports").fetchone()[0], 0)


    async def test_gate_requires_pool_evidence_and_keeps_blocks(self):
        safe = {"mintable": False, "freezable": False, "non_transferable": False,
                "default_frozen": False, "transfer_hook": False, "transfer_fee_upgradable": False}
        payload = {"token": {"mintAuthority": None, "freezeAuthority": None}, "risks": [], "rugged": False,
                   "creator": MINT, "topHolders": [{"pct": 35, "owner": MINT}],
                   "markets": [{"pubkey": POOL, "lp": {"baseUSD": 1_000, "quoteUSD": 2_000}}]}
        status, facts = parse_rugcheck(payload, POOL)
        self.assertEqual(status, "ok")
        reports = {"goplus": ("ok", NOW, safe), "rugcheck": (status, NOW, facts)}
        self.assertEqual(risk_view(reports, NOW, POOL, 1, True)["status"], "review")
        self.assertEqual(risk_view(reports, NOW, "C" * 32, 1, True)["status"], "waiting")
        self.assertEqual(risk_view(reports, NOW, POOL, 0, True)["missing_evidence"], ["recent_pool_sells"])
        self.assertEqual(risk_view(reports, NOW, POOL, 1, False)["status"], "waiting")
        self.assertEqual(risk_view(reports, NOW + 700_000, POOL, 1, True)["status"], "waiting")
        self.assertIsNone(parse_rugcheck(payload, "C" * 32)[1]["pool_liquidity_usd"])
        self.assertEqual(risk_view({"goplus": ("error", NOW, {}), "rugcheck": ("ok", NOW, facts)},
                                   NOW, POOL, 1, True)["status"], "waiting")
        unsafe = dict(safe, non_transferable=True)
        self.assertEqual(risk_view({**reports, "goplus": ("ok", NOW, unsafe)}, NOW, POOL, 1, True)["status"], "blocked")
        self.assertIn("transfer_hook", risk_view({**reports, "goplus": ("ok", NOW,
            dict(safe, transfer_hook=True))}, NOW, POOL, 1, True)["block_reasons"])
        self.assertIn("full_transfer_fee", risk_view({**reports, "goplus": ("ok", NOW,
            dict(safe, transfer_fee_bps=10_000))}, NOW, POOL, 1, True)["block_reasons"])
        self.assertEqual(risk_view({**reports, "goplus": ("ok", NOW,
            dict(safe, transfer_hook=None))}, NOW, POOL, 1, True)["status"], "waiting")
        self.assertEqual(risk_view({**reports, "rugcheck": ("ok", NOW, dict(facts, rugged=True))},
                                   NOW, POOL, 1, True)["status"], "blocked")
        self.assertIn("low_pool_liquidity", risk_view({**reports, "rugcheck": ("ok", NOW,
            dict(facts, pool_liquidity_usd=999))}, NOW, POOL, 1, True)["block_reasons"])

    async def test_failed_rugcheck_is_not_retried_without_limit(self):
        with tempfile.TemporaryDirectory() as root, patch.dict("os.environ", {
                "SONAR_PUMPPORTAL_ENABLED": "0", "SONAR_SHRINE_ENABLED": "0", "SONAR_RISK_ENABLED": "0"}), \
                patch.object(main, "DATA_DIR", Path(root)), patch.object(main, "DB_PATH", Path(root) / "sonar.db"):
            async with main.lifespan(main.app):
                save_launch(main.DB_PATH, Launch(MINT, "launch", "pump", POOL, None), NOW)
                self.assertTrue(save_price(main.DB_PATH, POOL, {"priceUSD": 1, "time": NOW / 1000}, NOW))
                save_report(main.DB_PATH, MINT, "goplus", "ok", {}, NOW)
                save_report(main.DB_PATH, MINT, "rugcheck", "error", {}, NOW - 61_000)
                self.assertEqual(next_candidate(main.DB_PATH, NOW), (MINT, POOL, ["rugcheck"]))
                save_report(main.DB_PATH, MINT, "rugcheck", "error", {}, NOW)
                self.assertIsNone(next_candidate(main.DB_PATH, NOW))


if __name__ == "__main__":
    unittest.main()
