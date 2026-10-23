import asyncio
import copy
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from pydantic import ValidationError

from sonar import inspector, main


MINT = "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
POOL = "So11111111111111111111111111111111111111112"
OTHER = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
NOW = 1_800_000_000_000


def fixture():
    gp = {"mintable": {"status": "0"}, "freezable": {"status": "0"},
          "default_account_state": "1", "non_transferable": "0", "transfer_hook": [],
          "transfer_fee_upgradable": {"status": "0"}, "transfer_fee": {}}
    gp.update({name: {"status": "0"} for name in inspector.TRANSFER_FLAGS[4:]})
    rug = {"mint": MINT, "tokenProgram": inspector.TOKEN_PROGRAM,
           "token": {"mintAuthority": None, "freezeAuthority": None, "supply": 1000, "decimals": 6},
           "rugged": False, "risks": [], "totalHolders": 10,
           "topHolders": [{"address": "1" * 31 + inspector.BASE58[index + 1], "pct": 1} for index in range(10)],
           "markets": [{"pubkey": POOL, "lp": {"baseUSD": 50_000, "quoteUSD": 50_000}}]}
    pair = {"chainId": "solana", "pairAddress": POOL, "dexId": "test", "priceUsd": "0.01",
            "baseToken": {"address": MINT, "name": "Example", "symbol": "EX"},
            "quoteToken": {"address": OTHER}, "liquidity": {"usd": 100_000},
            "txns": {"m5": {"buys": 10, "sells": 5}}, "volume": {"m5": 500},
            "priceChange": {"m5": -2}, "pairCreatedAt": NOW - 60_000}
    payloads = {"dexscreener": [pair], "goplus": {"code": 1, "result": {MINT: gp}}, "rugcheck": rug}
    return {source: ({"status": "ok", "error": None, "fetched_at_ms": NOW, "source_updated_at_ms": None}, payload)
            for source, payload in payloads.items()}


class InspectorTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        inspector._cache.clear()
        inspector._inflight.clear()

    def test_address_validation(self):
        self.assertEqual(inspector.InspectorRequest(mint=f" {MINT} ").mint, MINT)
        for value in ("https://example.com", "z" * 44, "1" * 31, "0" * 44, "../../health"):
            with self.assertRaises(ValidationError):
                inspector.InspectorRequest(mint=value)

    def test_complete_score_and_null_history(self):
        report = inspector.build_report(MINT, fixture(), NOW)
        self.assertEqual(report["score"]["value"], 100)
        self.assertEqual(report["score"]["status"], "scored")
        self.assertEqual(report["score"]["coverage_pct"], 100)
        self.assertEqual(report["selected_pool"]["price_usd"], 0.01)
        self.assertEqual(report["selected_pool"]["age_ms"], 60_000)
        self.assertIsNone(report["selected_pool"]["windows"]["h1"]["volume_usd"])
        self.assertIsNone(report["sources"]["rugcheck"]["source_updated_at_ms"])

    def test_pool_identity_and_liquidity_are_not_substituted(self):
        rows = fixture()
        pair = rows["dexscreener"][1][0]
        wrong = {**pair, "chainId": "ethereum", "liquidity": {"usd": 1e12}}
        quote = {**pair, "pairAddress": OTHER, "baseToken": {"address": OTHER}, "quoteToken": {"address": MINT}, "liquidity": {"usd": 1e12}}
        rows["dexscreener"][1].extend([wrong, quote])
        rows["rugcheck"][1]["markets"][0]["pubkey"] = OTHER
        report = inspector.build_report(MINT, rows, NOW)
        self.assertEqual(len(report["pools"]), 1)
        self.assertEqual(report["selected_pool"]["pool_id"], POOL)
        self.assertIsNone(report["rugcheck"]["pool_liquidity_usd"])
        rows["dexscreener"][1].pop(0)
        report = inspector.build_report(MINT, rows, NOW)
        self.assertIsNone(report["selected_pool"])
        self.assertIsNone(report["score"]["value"])

    def test_unknown_data_cannot_produce_high_score(self):
        for source in inspector.SOURCES:
            rows = fixture()
            rows[source] = ({"status": "error", "error": "rate_limited", "fetched_at_ms": NOW}, None)
            report = inspector.build_report(MINT, rows, NOW)
            self.assertIsNone(report["score"]["value"], source)
            self.assertEqual(report["score"]["status"], "insufficient_data")
        rows = fixture()
        rows["rugcheck"][1]["token"]["mintAuthority"] = False
        rows["rugcheck"][1]["topHolders"][0]["pct"] = float("nan")
        rows["dexscreener"][1][0]["liquidity"]["usd"] = True
        report = inspector.build_report(MINT, rows, NOW)
        self.assertIsNone(report["rugcheck"]["mintable"])
        self.assertIsNone(report["score"]["value"])
        json.dumps(report, allow_nan=False)

    def test_hard_blocks_override_missing_evidence_and_provider_disagreement(self):
        for field in ("mintable", "freezable", *inspector.TRANSFER_FLAGS[4:]):
            rows = fixture()
            rows["goplus"][1]["result"][MINT][field] = {"status": "1"}
            rows["dexscreener"][1].clear()
            score = inspector.build_report(MINT, rows, NOW)["score"]
            self.assertEqual(score["value"], 0)
            self.assertIn(field, score["block_reasons"])
        rows = fixture()
        rows["rugcheck"][1]["rugged"] = True
        self.assertEqual(inspector.build_report(MINT, rows, NOW)["score"]["status"], "blocked")
        rows = fixture()
        rows["goplus"][1]["result"][MINT]["transfer_fee"] = {"current_fee_rate": {"fee_rate": "10000"}}
        self.assertIn("full_transfer_fee", inspector.build_report(MINT, rows, NOW)["score"]["block_reasons"])
        rows = fixture()
        rows["dexscreener"][1][0]["liquidity"]["usd"] = 999
        self.assertIn("low_pool_liquidity", inspector.build_report(MINT, rows, NOW)["score"]["block_reasons"])
        rows = fixture()
        rows["rugcheck"][1]["markets"][0]["lp"] = {"baseUSD": 100, "quoteUSD": 100}
        self.assertIn("low_pool_liquidity", inspector.build_report(MINT, rows, NOW)["score"]["block_reasons"])

    def test_danger_caps_score_and_zero_activity_is_not_missing(self):
        rows = fixture()
        rows["rugcheck"][1]["risks"] = [{"name": "Example warning", "level": "danger"}]
        rows["dexscreener"][1][0]["txns"]["m5"] = {"buys": 0, "sells": 0}
        score = inspector.build_report(MINT, rows, NOW)["score"]
        self.assertEqual(score["value"], 49)
        self.assertNotIn("activity_5m", score["missing_evidence"])
        self.assertEqual(score["components"][-1]["points"], 0)

    def test_malformed_reports_preserve_known_blocks_and_do_not_earn_points(self):
        rows = fixture()
        gp = rows["goplus"][1]["result"][MINT]
        gp["mintable"] = {"status": "1"}
        gp["transfer_fee"] = {"current_fee_rate": {"fee_rate": "9" * 5000}}
        self.assertIn("mintable", inspector.build_report(MINT, rows, NOW)["score"]["block_reasons"])
        rows = fixture()
        rows["rugcheck"][1]["risks"] = [None]
        self.assertIsNone(inspector.build_report(MINT, rows, NOW)["score"]["value"])
        rows = fixture()
        rows["rugcheck"][1]["topHolders"][1] = rows["rugcheck"][1]["topHolders"][0]
        self.assertIsNone(inspector.build_report(MINT, rows, NOW)["score"]["value"])
        rows = fixture()
        rows["rugcheck"][1]["markets"][0]["lp"] = {"baseUSD": 10_000, "quoteUSD": 10_000}
        score = inspector.build_report(MINT, rows, NOW)["score"]
        self.assertIsNone(score["value"])
        self.assertIn("pool_liquidity_sources_disagree", score["conflicts"])

    def test_empty_and_failed_sources_have_distinct_status(self):
        failed = {source: ({"status": "error"}, None) for source in inspector.SOURCES}
        report = inspector.build_report(MINT, failed, NOW)
        self.assertEqual(report["status"], "unavailable")
        self.assertIsNone(report["score"]["value"])
        failed["dexscreener"] = ({"status": "empty"}, [])
        report = inspector.build_report(MINT, failed, NOW)
        self.assertEqual(report["status"], "no_data")
        self.assertIsNone(report["score"]["value"])

    async def test_cache_deduplicates_and_expires(self):
        rows = fixture()
        with patch.object(inspector, "fetch_source", side_effect=lambda source, mint: copy.deepcopy(rows[source])) as fetch:
            first, second = await asyncio.gather(inspector.inspect_mint(MINT), inspector.inspect_mint(MINT))
            self.assertEqual(fetch.call_count, 3)
            self.assertEqual(first["generated_at_ms"], second["generated_at_ms"])
            cached = await inspector.inspect_mint(MINT)
            self.assertTrue(cached["cache"]["hit"])
            self.assertEqual(fetch.call_count, 3)
            inspector._cache[MINT] = (0, first)
            await inspector.inspect_mint(MINT)
            self.assertEqual(fetch.call_count, 6)
        with patch.object(inspector, "MAX_INFLIGHT", 0):
            inspector._cache.clear()
            with self.assertRaises(inspector.InspectorBusy):
                await inspector.inspect_mint(MINT)

    def test_provider_limits_identity_and_errors(self):
        class Response(io.BytesIO):
            status = 200
        with patch.object(inspector, "urlopen", return_value=Response(b"[]")) as fetch:
            meta, payload = inspector.fetch_source("dexscreener", MINT)
            self.assertEqual(meta["status"], "empty")
            self.assertEqual(payload, [])
            self.assertEqual(fetch.call_args.args[0].get_header("User-agent"), "Sonar/0.1")
        with patch.object(inspector, "urlopen", return_value=Response(b'{"mint":"wrong","token":{}}')):
            self.assertEqual(inspector.fetch_source("rugcheck", MINT)[0]["error"], "invalid_response")
        with patch.object(inspector, "urlopen", return_value=Response(b" " * 2_097_153)):
            self.assertEqual(inspector.fetch_source("dexscreener", MINT)[0]["error"], "response_too_large")
        for failure, error in ((HTTPError("", 429, "", {}, None), "rate_limited"),
                               (TimeoutError(), "timeout"), (OSError(), "network_error")):
            with patch.object(inspector, "urlopen", side_effect=failure):
                meta, payload = inspector.fetch_source("goplus", MINT)
                self.assertEqual(meta["error"], error)
                self.assertIsNone(payload)

    async def test_http_validation_partial_and_total_failure(self):
        async def request(body):
            sent = []
            encoded = json.dumps(body).encode()
            async def receive():
                return {"type": "http.request", "body": encoded, "more_body": False}
            async def send(message):
                sent.append(message)
            await main.app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                            "method": "POST", "path": "/inspector", "raw_path": b"/inspector", "query_string": b"",
                            "headers": [(b"content-type", b"application/json")], "server": ("127.0.0.1", 8000),
                            "client": ("127.0.0.1", 1234), "scheme": "http", "root_path": ""}, receive, send)
            return sent[0]["status"], json.loads(sent[1]["body"])
        with patch.object(main, "inspect_mint") as inspect:
            self.assertEqual((await request({"mint": "invalid"}))[0], 422)
            inspect.assert_not_called()
            inspect.return_value = {"status": "partial", "score": {"value": None}}
            self.assertEqual((await request({"mint": MINT}))[0], 200)
            inspect.return_value = {"status": "unavailable", "score": {"value": None}}
            self.assertEqual((await request({"mint": MINT}))[0], 503)
            inspect.side_effect = inspector.InspectorBusy
            self.assertEqual((await request({"mint": MINT}))[0], 429)


if __name__ == "__main__":
    unittest.main()
