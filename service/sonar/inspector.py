"""On-demand Solana snapshots and an explicit, uncalibrated risk-screening rubric."""

import asyncio
import json
import math
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .pumpportal import ADDRESS
from .risk import parse_goplus, parse_rugcheck


BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SOURCES = ("dexscreener", "goplus", "rugcheck")
TRANSFER_FLAGS = ("non_transferable", "default_frozen", "transfer_hook", "transfer_fee_upgradable",
                  "balance_mutable_authority", "closable", "default_account_state_upgradable",
                  "transfer_hook_upgradable")
CACHE_SECONDS = 30
MAX_REPORTS = 128
MAX_INFLIGHT = 4
_cache: dict[str, tuple[float, dict]] = {}
_inflight: dict[str, asyncio.Task] = {}


def valid_address(value: object) -> bool:
    if not isinstance(value, str) or not ADDRESS.fullmatch(value):
        return False
    number = 0
    for char in value:
        number = number * 58 + BASE58.index(char)
    return (number.bit_length() + 7) // 8 + len(value) - len(value.lstrip("1")) == 32


class InspectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mint: str = Field(min_length=32, max_length=128)

    @field_validator("mint")
    @classmethod
    def validate_mint(cls, value: str) -> str:
        value = value.strip()
        if not valid_address(value):
            raise ValueError("Expected a base58 Solana mint address encoding 32 bytes")
        return value


def number(value: object, minimum: float | None = 0, maximum: float | None = None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        parsed = float(value)
    except (ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) and (minimum is None or parsed >= minimum) and (maximum is None or parsed <= maximum) else None


def text(value: object, limit: int = 160) -> str | None:
    return value[:limit] if isinstance(value, str) and value.strip() else None


def mapping(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def image_url(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        url = urlsplit(value)
        return value if url.scheme == "https" and url.hostname and not url.username and not url.password else None
    except ValueError:
        return None


def fetch_source(source: str, mint: str) -> tuple[dict, object]:
    urls = {
        "dexscreener": f"https://api.dexscreener.com/token-pairs/v1/solana/{mint}",
        "goplus": f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={mint}",
        "rugcheck": f"https://api.rugcheck.xyz/v1/tokens/{mint}/report",
    }
    limit = 8_388_608 if source == "rugcheck" else 2_097_152
    http_status = None
    try:
        started = time.monotonic()
        with urlopen(Request(urls[source], headers={"Accept": "application/json", "User-Agent": "Sonar/0.1"}), timeout=8) as response:
            http_status = response.status
            content = bytearray()
            while True:
                if time.monotonic() - started > 12:
                    raise TimeoutError("response deadline")
                chunk = response.read1(min(65_536, limit + 1 - len(content)))
                content.extend(chunk)
                if len(content) > limit:
                    raise ResponseTooLarge
                if not chunk:
                    break
        payload = json.loads(content, parse_constant=lambda _: None)
        if source == "dexscreener":
            valid = isinstance(payload, list)
            empty = not payload
        elif source == "goplus":
            valid = isinstance(payload, dict) and payload.get("code") in (1, "1") and isinstance(payload.get("result"), dict)
            empty = not isinstance(mapping(mapping(payload).get("result")).get(mint), dict)
        else:
            valid = isinstance(payload, dict) and payload.get("mint") == mint and isinstance(payload.get("token"), dict) and not payload.get("error")
            empty = False
        if not valid:
            raise ValueError("invalid response")
        status, error = ("empty" if empty else "ok"), None
    except HTTPError as exc:
        http_status = exc.code
        status, error, payload = "error", "rate_limited" if exc.code == 429 else "not_found" if exc.code == 404 else "http_error", None
        exc.close()
    except ResponseTooLarge:
        status, error, payload = "error", "response_too_large", None
    except TimeoutError:
        status, error, payload = "error", "timeout", None
    except OSError:
        status, error, payload = "error", "network_error", None
    except (ValueError, UnicodeError):
        status, error, payload = "error", "invalid_response", None
    return {"status": status, "error": error, "http_status": http_status, "fetched_at_ms": time.time_ns() // 1_000_000,
            "source_updated_at_ms": None}, payload


def parse_pairs(mint: str, payload: object, now_ms: int) -> list[dict]:
    pairs = {}
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict) or item.get("chainId") != "solana" or mapping(item.get("baseToken")).get("address") != mint or not valid_address(item.get("pairAddress")):
            continue
        price = number(item.get("priceUsd"))
        created = number(item.get("pairCreatedAt"), 1_000_000_000_000, now_ms)
        windows = {}
        for key in ("m5", "h1", "h6", "h24"):
            txns = mapping(mapping(item.get("txns")).get(key))
            counts = {name: number(txns.get(name), 0, 1e12) for name in ("buys", "sells")}
            windows[key] = {
                "price_change_pct": number(mapping(item.get("priceChange")).get(key), -100),
                "volume_usd": number(mapping(item.get("volume")).get(key)),
                **{f"observed_{name}": int(value) if value is not None and value.is_integer() else None for name, value in counts.items()},
            }
        info = mapping(item.get("info"))
        pairs[item["pairAddress"]] = {
            "pool_id": item["pairAddress"], "dex": text(item.get("dexId")),
            "base_mint": mint, "quote_mint": text(mapping(item.get("quoteToken")).get("address")),
            "name": text(mapping(item.get("baseToken")).get("name")),
            "symbol": text(mapping(item.get("baseToken")).get("symbol"), 32),
            "image_url": image_url(info.get("imageUrl")),
            "source": "dexscreener", "source_updated_at_ms": None,
            "price_usd": price if price and price > 0 else None,
            "liquidity_usd": number(mapping(item.get("liquidity")).get("usd")),
            "fdv_usd": number(item.get("fdv")), "market_cap_usd": number(item.get("marketCap")),
            "created_at_ms": int(created) if created is not None else None,
            "age_ms": now_ms - int(created) if created is not None else None,
            "windows": windows,
        }
    return sorted(pairs.values(), key=lambda row: (-(row["liquidity_usd"] or 0), row["pool_id"]))


def rug_facts(payload: object, pool_id: str | None) -> dict:
    data = mapping(payload)
    token = dict(mapping(data.get("token")))
    for key in ("mintAuthority", "freezeAuthority"):
        if key in token and token[key] is not None and not valid_address(token[key]):
            token.pop(key)
    _, facts = parse_rugcheck({**data, "token": token}, pool_id)
    facts["provider_score"] = facts.pop("score")
    facts["provider_score_higher_is_riskier"] = True
    holders = data.get("topHolders")
    valid_holders = []
    seen = set()
    malformed_holders = False
    if isinstance(holders, list):
        for holder in holders[:20]:
            holder = mapping(holder)
            pct = number(holder.get("pct"), 0, 100)
            if pct is not None and valid_address(holder.get("address")) and holder["address"] not in seen:
                valid_holders.append({"token_account": holder["address"], "owner": text(holder.get("owner")), "pct": pct})
                seen.add(holder["address"])
            else:
                malformed_holders = True
    valid_holders.sort(key=lambda holder: -holder["pct"])
    count = number(data.get("totalHolders"), 1, 1e12)
    expected = min(10, int(count)) if count is not None and count.is_integer() else 10
    concentration = sum(holder["pct"] for holder in valid_holders[:10]) if not malformed_holders and len(valid_holders) >= expected else None
    facts["top10_pct"] = round(concentration, 2) if concentration is not None and concentration <= 100 else None
    facts["holders"] = valid_holders
    facts["total_holders"] = int(count) if count is not None and count.is_integer() else None
    facts["pool_lp_locked_pct"] = number(facts.get("pool_lp_locked_pct"), 0, 100)
    facts["token_program"] = text(data.get("tokenProgram"))
    facts["mint_authority"] = text(token.get("mintAuthority"))
    facts["freeze_authority"] = text(token.get("freezeAuthority"))
    facts["creator"] = data.get("creator") if valid_address(data.get("creator")) else None
    decimals = token.get("decimals")
    facts["decimals"] = decimals if isinstance(decimals, int) and not isinstance(decimals, bool) and 0 <= decimals <= 255 else None
    supply = str(token.get("supply", ""))
    facts["supply_raw"] = supply if supply.isascii() and supply.isdigit() and len(supply) <= 20 else None
    facts["metadata_mutable"] = mapping(data.get("tokenMeta")).get("mutable") if isinstance(mapping(data.get("tokenMeta")).get("mutable"), bool) else None
    risks = data.get("risks")
    valid_risks = isinstance(risks, list) and all(isinstance(row, dict) and text(row.get("name")) for row in risks)
    facts["risks"] = [{"name": text(row.get("name")), "level": text(row.get("level"), 40),
                       "description": text(row.get("description"), 500)}
                      for row in risks] if valid_risks else None
    return facts


def score_report(pool: dict | None, goplus: dict, rugcheck: dict) -> dict:
    blocks = []
    missing = []
    conflicts = []
    for key in ("mintable", "freezable"):
        values = [provider.get(key) for provider in (goplus, rugcheck)]
        if True in values:
            blocks.append(key)
        if any(value is None for value in values):
            missing.append(key)
        if all(isinstance(value, bool) for value in values) and values[0] != values[1]:
            conflicts.append(key)
    for key in TRANSFER_FLAGS:
        if goplus.get(key) is True:
            blocks.append(key)
        elif goplus.get(key) is None:
            missing.append(key)
    if rugcheck.get("rugged") is True:
        blocks.append("rugged")
    elif rugcheck.get("rugged") is None:
        missing.append("rugged")
    fee = number(goplus.get("transfer_fee_bps"), 0, 10_000)
    if fee is None and rugcheck.get("token_program") == TOKEN_PROGRAM:
        fee = 0
    if fee is None:
        missing.append("transfer_fee_bps")
    elif fee >= 10_000:
        blocks.append("full_transfer_fee")
    liquidity = pool.get("liquidity_usd") if pool else None
    rug_liquidity = number(rugcheck.get("pool_liquidity_usd"))
    if liquidity is not None and rug_liquidity is not None:
        if max(liquidity, rug_liquidity) > 0 and min(liquidity, rug_liquidity) / max(liquidity, rug_liquidity) < 0.5:
            conflicts.append("pool_liquidity_sources_disagree")
        liquidity = min(liquidity, rug_liquidity)
    if liquidity is None:
        missing.append("pool_liquidity")
    elif liquidity < 1_000:
        blocks.append("low_pool_liquidity")
    if not pool or pool.get("price_usd") is None:
        missing.append("usd_price")
    concentration = rugcheck.get("top10_pct")
    if concentration is None:
        missing.append("holder_concentration")
    risks = rugcheck.get("risks")
    findings_known = risks is not None and all(row["level"] in ("info", "warn", "danger") for row in risks)
    if not findings_known:
        missing.append("rugcheck_findings")
    activity = pool["windows"]["m5"] if pool else {}
    activity_known = all(activity.get(key) is not None for key in ("volume_usd", "observed_buys", "observed_sells"))
    if not activity_known:
        missing.append("activity_5m")

    authority_points = None
    if not any(key in missing for key in ("mintable", "freezable", "rugged")):
        authority_points = 0 if any(key in blocks for key in ("mintable", "freezable", "rugged")) else 25
    transfer_points = None
    if not any(key in missing for key in (*TRANSFER_FLAGS, "transfer_fee_bps")):
        transfer_points = 20 if fee == 0 else 10 if fee <= 100 else 0
        if any(key in blocks for key in (*TRANSFER_FLAGS, "full_transfer_fee")):
            transfer_points = 0
    liquidity_points = None
    if liquidity is not None:
        liquidity_points = next(points for floor, points in ((100_000, 25), (50_000, 20), (10_000, 12), (1_000, 5), (0, 0)) if liquidity >= floor)
    concentration_points = None
    if concentration is not None:
        concentration_points = next(points for ceiling, points in ((20, 15), (40, 10), (60, 5), (100, 0)) if concentration <= ceiling)
    finding_points = None if not findings_known else 10 if all(row["level"] == "info" for row in risks) else 0
    activity_points = None
    if activity_known:
        activity_points = 5 if activity["volume_usd"] > 0 and activity["observed_buys"] > 0 and activity["observed_sells"] > 0 else 0
    components = [
        {"key": "authorities", "max_points": 25, "points": authority_points},
        {"key": "transfer_rules", "max_points": 20, "points": transfer_points},
        {"key": "liquidity", "max_points": 25, "points": liquidity_points},
        {"key": "address_concentration", "max_points": 15, "points": concentration_points},
        {"key": "provider_findings", "max_points": 10, "points": finding_points},
        {"key": "observed_activity", "max_points": 5, "points": activity_points},
    ]
    caps = [{"reason": "rugcheck_danger", "maximum": 49}] if risks and any(row["level"] == "danger" for row in risks) else []
    value = None if missing or conflicts else sum(row["points"] for row in components)
    if value is not None and caps:
        value = min(value, 49)
    return {"version": "inspector-v1", "kind": "risk_screening", "higher_is_better": True,
            "status": "blocked" if blocks else "insufficient_data" if missing or conflicts else "scored",
            "value": 0 if blocks else value, "max_value": 100,
            "coverage_pct": sum(row["max_points"] for row in components if row["points"] is not None),
            "components": components, "caps": caps, "block_reasons": blocks,
            "missing_evidence": missing, "conflicts": conflicts,
            "evidence": {"effective_transfer_fee_bps": fee, "pool_liquidity_usd": liquidity,
                         "top10_token_accounts_pct": concentration},
            "calibration": "heuristic_unvalidated"}


def build_report(mint: str, results: dict[str, tuple[dict, object]], now_ms: int) -> dict:
    sources = {source: row[0] for source, row in results.items()}
    pairs = parse_pairs(mint, results["dexscreener"][1], now_ms)
    pool = pairs[0] if pairs else None
    gp_payload = results["goplus"][1]
    try:
        gp_status, goplus = parse_goplus(mint, gp_payload)
    except (ValueError, TypeError, OverflowError):
        gp_status, goplus = "partial", {}
    if sources["goplus"]["status"] == "ok" and gp_status != "ok":
        sources["goplus"] = {**sources["goplus"], "status": "partial"}
    gp_data = mapping(mapping(mapping(gp_payload).get("result")).get(mint))
    for key in TRANSFER_FLAGS[4:]:
        value = mapping(gp_data.get(key)).get("status")
        goplus[key] = bool(int(value)) if str(value) in ("0", "1") else None
    rug_payload = mapping(results["rugcheck"][1])
    rugcheck = rug_facts(rug_payload, pool["pool_id"] if pool else None)
    meta = mapping(rug_payload.get("tokenMeta")) or mapping(gp_data.get("metadata"))
    score = score_report(pool, goplus, rugcheck)
    any_data = bool(pairs or gp_data or rug_payload)
    status = "unavailable" if all(row["status"] == "error" for row in sources.values()) else "no_data" if not any_data else "partial" if score["missing_evidence"] or any(row["status"] != "ok" for row in sources.values()) else "complete"
    return {
        "mint": mint, "chain": "solana", "generated_at_ms": now_ms, "status": status,
        "token": {"name": pool["name"] if pool and pool["name"] else text(meta.get("name")),
                  "symbol": pool["symbol"] if pool and pool["symbol"] else text(meta.get("symbol"), 32),
                  "image_url": pool["image_url"] if pool else None},
        "sources": sources, "pool_selection": "highest_reported_liquidity_base_token_match",
        "selected_pool": pool, "pools": pairs, "goplus": goplus, "rugcheck": rugcheck,
        "score": score,
        "limitations": [
            "Баллы основаны на предварительных правилах; вероятность роста и результат сделки не оценивались.",
            "Время исходного обновления источники не подтверждают. fetched_at_ms — время получения ответа, не время цены или проверки блокчейна.",
            "Концентрация относится к токен-счетам, включая пулы и контракты; независимость владельцев не установлена.",
            "Покупки и продажи — счётчики выбранного пула от индексатора. Исполнимость выхода, проскальзывание и wash trading не проверены.",
            "Минутная история, связи кошельков и социальные сигналы пока отсутствуют. LP-поля зависят от типа пула и не гарантируют блокировку ликвидности.",
        ],
    }


async def _generate(mint: str) -> dict:
    try:
        rows = await asyncio.gather(*(asyncio.to_thread(fetch_source, source, mint) for source in SOURCES))
        report = build_report(mint, dict(zip(SOURCES, rows)), time.time_ns() // 1_000_000)
        if len(_cache) >= MAX_REPORTS:
            _cache.pop(next(iter(_cache)))
        _cache[mint] = (time.monotonic(), report)
        return report
    finally:
        _inflight.pop(mint, None)


async def inspect_mint(mint: str) -> dict:
    if not valid_address(mint):
        raise ValueError("invalid mint")
    entry = _cache.get(mint)
    if entry and time.monotonic() - entry[0] < CACHE_SECONDS:
        return {**entry[1], "cache": {"hit": True, "age_ms": max(0, time.time_ns() // 1_000_000 - entry[1]["generated_at_ms"]), "ttl_seconds": CACHE_SECONDS}}
    if mint not in _inflight:
        if len(_inflight) >= MAX_INFLIGHT:
            raise InspectorBusy
        _inflight[mint] = asyncio.create_task(_generate(mint))
    report = await asyncio.shield(_inflight[mint])
    return {**report, "cache": {"hit": False, "age_ms": max(0, time.time_ns() // 1_000_000 - report["generated_at_ms"]), "ttl_seconds": CACHE_SECONDS}}


class InspectorBusy(Exception):
    pass


class ResponseTooLarge(ValueError):
    pass
