"""Fetch a few selected token-risk facts without treating provider scores as safety proof."""

import asyncio
import json
import logging
import math
import sqlite3
import time
from pathlib import Path
from urllib.request import Request, urlopen

from .pumpportal import ADDRESS


logger = logging.getLogger("sonar.risk")
PROVIDERS = ("goplus", "rugcheck")
RISK_FRESH_MS = 600_000
# shortcut: conservative pilot floor, revisit after measuring real pool depth and exit costs.
MIN_POOL_LIQUIDITY_USD = 1_000
# shortcut: sample at most six candidates an hour until a candidate-quality filter exists.
MAX_CHECKS_PER_HOUR = 6


def parse_goplus(mint: str, payload: object) -> tuple[str, dict]:
    if not isinstance(payload, dict) or payload.get("code") not in (1, "1"):
        return "partial", {}
    result = payload.get("result")
    data = result.get(mint) if isinstance(result, dict) else None
    if not isinstance(data, dict):
        return "partial", {}

    def flag(name: str) -> bool | None:
        value = data.get(name)
        if isinstance(value, dict):
            value = value.get("status")
        return bool(int(value)) if str(value) in ("0", "1") else None

    state = data.get("default_account_state")
    facts = {
        "mintable": flag("mintable"),
        "freezable": flag("freezable"),
        "non_transferable": flag("non_transferable"),
        "default_frozen": str(state) == "2" if str(state) in ("0", "1", "2") else None,
        "transfer_hook": bool(data["transfer_hook"]) if isinstance(data.get("transfer_hook"), list) else None,
        "transfer_fee_upgradable": flag("transfer_fee_upgradable"),
    }
    fee = data.get("transfer_fee")
    if isinstance(fee, dict) and isinstance(fee.get("current_fee_rate"), dict):
        rate = fee["current_fee_rate"].get("fee_rate")
        if isinstance(rate, (int, float, str)) and str(rate).isascii() and str(rate).isdigit() and len(str(rate)) <= 10:
            facts["transfer_fee_bps"] = int(rate)
    return ("ok" if all(value is not None for key, value in facts.items() if key != "transfer_fee_bps") else "partial", facts)


def parse_rugcheck(payload: object, pool_id: str | None = None) -> tuple[str, dict]:
    if not isinstance(payload, dict) or payload.get("error"):
        return "partial", {}
    risks = payload.get("risks")
    score = payload.get("score")
    token = payload.get("token")
    holders = payload.get("topHolders")
    markets = payload.get("markets")
    market = next((item for item in markets if isinstance(item, dict) and item.get("pubkey") == pool_id), None) if isinstance(markets, list) and pool_id else None
    lp = market.get("lp") if isinstance(market, dict) else None
    liquidity = sum(lp.get(key, 0) for key in ("baseUSD", "quoteUSD")) if isinstance(lp, dict) and all(isinstance(lp.get(key), (int, float)) and not isinstance(lp[key], bool) and math.isfinite(lp[key]) and lp[key] >= 0 for key in ("baseUSD", "quoteUSD")) else None
    valid_holders = [item for item in holders if isinstance(item, dict) and isinstance(item.get("pct"), (int, float)) and not isinstance(item["pct"], bool) and math.isfinite(item["pct"]) and 0 <= item["pct"] <= 100] if isinstance(holders, list) else []
    creator = payload.get("creator")
    facts = {
        "pool_id": pool_id,
        "score": score if isinstance(score, int) and not isinstance(score, bool) else None,
        "mintable": bool(token["mintAuthority"]) if isinstance(token, dict) and "mintAuthority" in token else None,
        "freezable": bool(token["freezeAuthority"]) if isinstance(token, dict) and "freezeAuthority" in token else None,
        "rugged": payload.get("rugged") if isinstance(payload.get("rugged"), bool) else None,
        "top10_pct": round(sum(item["pct"] for item in valid_holders[:10]), 2) if valid_holders else None,
        "creator_top_holders_pct": round(sum(item["pct"] for item in valid_holders if item.get("owner") == creator), 2) if isinstance(creator, str) and valid_holders else None,
        "pool_liquidity_usd": round(liquidity, 2) if liquidity is not None else None,
        "pool_lp_locked_pct": lp.get("lpLockedPct") if isinstance(lp, dict) and isinstance(lp.get("lpLockedPct"), (int, float)) and math.isfinite(lp["lpLockedPct"]) else None,
        "risks": [{"name": item.get("name", "")[:80], "level": item.get("level", "")[:40]}
                  for item in risks[:20] if isinstance(item, dict) and isinstance(item.get("name"), str)
                  and isinstance(item.get("level"), str)] if isinstance(risks, list) else None,
    }
    return ("ok" if all(facts[key] is not None for key in ("mintable", "freezable", "rugged", "risks")) else "partial", facts)


def fetch(provider: str, mint: str, pool_id: str | None = None) -> tuple[str, dict]:
    if not ADDRESS.fullmatch(mint) or provider not in PROVIDERS:
        raise ValueError("invalid risk request")
    url = (f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={mint}"
           if provider == "goplus" else f"https://api.rugcheck.xyz/v1/tokens/{mint}/report")
    with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=8) as response:
        content = response.read(262_145)
    if len(content) > 262_144:
        raise ValueError("risk response too large")
    payload = json.loads(content)
    return parse_goplus(mint, payload) if provider == "goplus" else parse_rugcheck(payload, pool_id)


def next_candidate(db_path: Path, now_ms: int) -> tuple[str, str | None, list[str]] | None:
    with sqlite3.connect(db_path) as db:
        if db.execute(
            "SELECT COUNT(*) FROM risk_reports WHERE provider = 'goplus' AND checked_ms >= ?",
            (now_ms - 3_600_000,),
        ).fetchone()[0] >= MAX_CHECKS_PER_HOUR:
            return None
        rows = db.execute(
            """SELECT mint, pool_id FROM candidates WHERE first_seen_ms >= ? AND price > 0
               AND price_unit = 'USD' AND price_source_ms >= ? AND price_seen_ms >= ?
               ORDER BY first_seen_ms DESC LIMIT 20""",
            (now_ms - 120_000, now_ms - 30_000, now_ms - 30_000),
        ).fetchall()
        for mint, pool_id in rows:
            if not ADDRESS.fullmatch(mint):
                continue
            reports = {provider: (status, attempts, checked_ms, json.loads(facts_json)) for provider, status, attempts, checked_ms, facts_json in db.execute(
                "SELECT provider, status, attempts, checked_ms, facts_json FROM risk_reports WHERE mint = ?", (mint,)
            )}
            due = [provider for provider in PROVIDERS if provider not in reports or
                   (provider == "rugcheck" and reports[provider][0] == "ok" and reports[provider][3].get("pool_id") != pool_id) or
                   (reports[provider][0] != "ok" and reports[provider][1] < 2 and reports[provider][2] <= now_ms - 60_000)]
            if due:
                return mint, pool_id, due
    return None


def save_report(db_path: Path, mint: str, provider: str, status: str, facts: dict, checked_ms: int) -> None:
    with sqlite3.connect(db_path) as db:
        db.execute(
            """INSERT INTO risk_reports (mint, provider, checked_ms, status, facts_json, attempts)
               VALUES (?, ?, ?, ?, ?, 1) ON CONFLICT(mint, provider) DO UPDATE SET
               checked_ms = excluded.checked_ms, status = excluded.status,
               facts_json = excluded.facts_json, attempts = attempts + 1""",
            (mint, provider, checked_ms, status, json.dumps(facts, separators=(",", ":"))),
        )


def risk_view(reports: dict[str, tuple[str, int, dict]], now_ms: int,
              pool_id: str | None = None, recent_sells: int = 0, fresh_price: bool = False) -> dict:
    flags = ("mintable", "freezable", "non_transferable", "default_frozen", "transfer_hook", "transfer_fee_upgradable")
    goplus = reports.get("goplus")
    rugcheck = reports.get("rugcheck")
    matching_pool = bool(pool_id and rugcheck and rugcheck[2].get("pool_id") == pool_id)
    reasons = [name for name in flags if goplus and goplus[1] >= now_ms - RISK_FRESH_MS
               and goplus[2].get(name) is True]
    if rugcheck and rugcheck[1] >= now_ms - RISK_FRESH_MS:
        reasons.extend(name for name in ("mintable", "freezable", "rugged") if rugcheck[2].get(name) is True and name not in reasons)
    if goplus and goplus[1] >= now_ms - RISK_FRESH_MS and goplus[2].get("transfer_fee_bps", 0) >= 10_000:
        reasons.append("full_transfer_fee")
    if matching_pool and rugcheck[1] >= now_ms - RISK_FRESH_MS:
        liquidity = rugcheck[2].get("pool_liquidity_usd")
        if isinstance(liquidity, (int, float)) and 0 <= liquidity < MIN_POOL_LIQUIDITY_USD:
            reasons.append("low_pool_liquidity")
    complete = all(provider in reports and reports[provider][0] == "ok" and
                   reports[provider][1] >= now_ms - RISK_FRESH_MS for provider in PROVIDERS)
    complete = bool(complete and goplus and rugcheck and
                    all(goplus[2].get(name) is not None for name in flags) and
                    all(rugcheck[2].get(name) is not None for name in ("mintable", "freezable", "rugged")))
    missing = []
    if not fresh_price:
        missing.append("fresh_price")
    if not complete:
        missing.append("risk_reports")
    if not matching_pool or rugcheck[2].get("pool_liquidity_usd") is None:
        missing.append("pool_liquidity")
    if not rugcheck or rugcheck[2].get("top10_pct") is None:
        missing.append("holders")
    if recent_sells <= 0:
        missing.append("recent_pool_sells")
    return {
        "status": "blocked" if reasons else "waiting" if missing else "review",
        "block_reasons": reasons,
        "missing_evidence": missing,
        "recent_pool_sells": recent_sells,
        "goplus": goplus[2] if goplus else None,
        "rugcheck": reports["rugcheck"][2] if "rugcheck" in reports else None,
    }


async def run(db_path: Path) -> None:
    while True:
        try:
            selection = next_candidate(db_path, int(time.time() * 1000))
            if selection is not None:
                mint, pool_id, providers = selection
                for provider in providers:
                    try:
                        status, facts = await asyncio.to_thread(fetch, provider, mint, pool_id)
                    except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                        logger.warning("risk_provider_failed provider=%s error=%s", provider, type(exc).__name__)
                        status, facts = "error", {}
                    save_report(db_path, mint, provider, status, facts, int(time.time() * 1000))
        except sqlite3.Error as exc:
            logger.warning("risk_database_error error=%s", type(exc).__name__)
        await asyncio.sleep(20)
