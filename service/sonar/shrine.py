"""Read bounded Shrine pool streams into the local candidate database."""

import asyncio
import json
import logging
import math
import sqlite3
import time
from collections import deque
from pathlib import Path

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from .pumpportal import ADDRESS, Launch, save_launch


URL = "wss://sol.shrine.trade/socket.io/?EIO=4&transport=websocket"
MAX_POOLS = 12
TRACK_MS = 60_000
RETRY_SECONDS = (1, 2, 5, 10)
logger = logging.getLogger("sonar.shrine")


def frame_event(frame: str) -> tuple[str, dict] | None:
    if not frame.startswith("42"):
        return None
    try:
        value = json.loads(frame[2:])
    except ValueError:
        return None
    if not isinstance(value, list) or len(value) < 2 or not isinstance(value[0], str) or not isinstance(value[1], dict):
        return None
    return value[0], value[1]


def source_ms(value: object, received_ms: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    milliseconds = int(value * 1000)
    return milliseconds if 1_000_000_000_000 <= milliseconds <= received_ms + 30_000 else None


def save_price(db_path: Path, pool: str, event: dict, received_ms: int) -> bool:
    price = event.get("priceUSD")
    timestamp = source_ms(event.get("time"), received_ms)
    if not isinstance(pool, str) or not ADDRESS.fullmatch(pool) or isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0 or timestamp is None:
        return False
    with sqlite3.connect(db_path) as db:
        changed = db.execute(
            """UPDATE candidates SET price = ?, price_unit = 'USD', price_source = 'shrine',
               price_source_ms = ?, price_seen_ms = ? WHERE pool_id = ?
               AND (price_source_ms IS NULL OR price_source_ms <= ?)""",
            (price, timestamp, received_ms, pool, timestamp),
        ).rowcount
        if changed:
            db.execute(
                """INSERT OR IGNORE INTO price_samples
                   (mint, pool_id, bucket_ms, price_usd, source_ms, received_ms)
                   SELECT mint, pool_id, ?, ?, ?, ? FROM candidates WHERE pool_id = ?""",
                (timestamp // 10_000 * 10_000, price, timestamp, received_ms, pool),
            )
    return changed > 0


def save_trade(db_path: Path, pool: str, event: dict, received_ms: int) -> bool:
    mint = event.get("mint")
    timestamp = source_ms(event.get("timestamp"), received_ms)
    side = event.get("is_buy")
    if not isinstance(pool, str) or not ADDRESS.fullmatch(pool) or not isinstance(mint, str) or not ADDRESS.fullmatch(mint) or timestamp is None or not isinstance(side, bool):
        return False
    with sqlite3.connect(db_path) as db:
        if db.execute("SELECT 1 FROM candidates WHERE mint = ? AND pool_id = ?", (mint, pool)).fetchone() is None:
            return False
        db.execute(
            """INSERT INTO trade_minutes (mint, pool_id, minute_ms, buys, sells)
               VALUES (?, ?, ?, ?, ?) ON CONFLICT(mint, pool_id, minute_ms) DO UPDATE SET
               buys = buys + excluded.buys, sells = sells + excluded.sells""",
            (mint, pool, timestamp // 60_000 * 60_000, int(side), int(not side)),
        )
    return True


def recent_candidates(db_path: Path, now_ms: int) -> list[tuple[str, str | None]]:
    with sqlite3.connect(db_path) as db:
        return db.execute(
            """SELECT mint, pool_id FROM candidates WHERE first_seen_ms >= ?
               ORDER BY first_seen_ms DESC LIMIT ?""",
            (now_ms - TRACK_MS, MAX_POOLS),
        ).fetchall()


def prune_history(db_path: Path, now_ms: int) -> None:
    with sqlite3.connect(db_path) as db:
        db.execute("DELETE FROM price_samples WHERE bucket_ms < ?", (now_ms - 3_600_000,))
        db.execute("DELETE FROM trade_minutes WHERE minute_ms < ?", (now_ms - 86_400_000,))
        db.execute("DELETE FROM candidate_events WHERE received_ms < ?", (now_ms - 172_800_000,))
        db.execute("DELETE FROM risk_reports WHERE checked_ms < ?", (now_ms - 172_800_000,))
        # shortcut: keep candidates for 48 hours; preserve tracked mints when Track is implemented.
        db.execute("DELETE FROM candidates WHERE first_seen_ms < ?", (now_ms - 172_800_000,))


async def run(db_path: Path) -> None:
    backoff = 1
    last_cleanup = 0.0
    while True:
        try:
            if time.monotonic() - last_cleanup >= 300:
                prune_history(db_path, int(time.time() * 1000))
                last_cleanup = time.monotonic()
            async with connect(URL, max_size=128 * 1024, max_queue=4, compression=None,
                               open_timeout=10, close_timeout=1) as ws:
                if not str(await asyncio.wait_for(ws.recv(), 10)).startswith("0{"):
                    raise ValueError("missing Engine.IO open")
                await ws.send("40")
                if not str(await asyncio.wait_for(ws.recv(), 10)).startswith("40"):
                    raise ValueError("missing Socket.IO connect")
                await ws.send('42["subscribe_new_tokens",{"protocols":["PUMPFUN"]}]')
                logger.info("shrine_connected")
                backoff = 1
                active: dict[str, dict] = {}
                acks: dict[int, tuple[str, str, int]] = {}
                retries: list[tuple[float, str, str, int]] = []
                next_ack = 0
                # shortcut: dedupe recent signatures in memory; persist IDs if reconnect replays prove common.
                seen = set()
                seen_order = deque()

                async def subscribe(mint: str, method: str, attempt: int) -> None:
                    nonlocal next_ack
                    candidate = active.get(mint)
                    if candidate is None or candidate[method]:
                        return
                    next_ack += 1
                    acks[next_ack] = (mint, method, attempt)
                    target = {"pool": candidate["pool"]} if candidate["pool"] else {"mint": mint}
                    await ws.send(f"42{next_ack}" + json.dumps([method, target], separators=(",", ":")))

                while True:
                    now_ms = int(time.time() * 1000)
                    if time.monotonic() - last_cleanup >= 300:
                        prune_history(db_path, now_ms)
                        last_cleanup = time.monotonic()
                    for mint, candidate in list(active.items()):
                        if now_ms - candidate["started"] >= TRACK_MS:
                            if candidate["pool"]:
                                for method in ("unsubscribe", "unsubscribe_trades"):
                                    await ws.send("42" + json.dumps([method, {"pool": candidate["pool"]}]))
                            del active[mint]
                    acks = {number: request for number, request in acks.items() if request[0] in active}
                    for mint, pool in recent_candidates(db_path, now_ms):
                        if len(active) >= MAX_POOLS:
                            break
                        if mint not in active and ADDRESS.fullmatch(mint):
                            active[mint] = {"pool": pool if isinstance(pool, str) and ADDRESS.fullmatch(pool) else None,
                                            "started": now_ms, "subscribe": False, "subscribe_trades": False}
                            for method in ("subscribe", "subscribe_trades"):
                                await subscribe(mint, method, 0)
                    due, retries = [r for r in retries if r[0] <= time.monotonic()], [r for r in retries if r[0] > time.monotonic()]
                    for _, mint, method, attempt in due:
                        await subscribe(mint, method, attempt)
                    try:
                        frame = await asyncio.wait_for(ws.recv(), 1)
                    except TimeoutError:
                        continue
                    if frame == "2":
                        await ws.send("3")
                        continue
                    if not isinstance(frame, str):
                        continue
                    if frame.startswith("43"):
                        marker = frame.find("[")
                        if marker < 0 or not frame[2:marker].isdigit():
                            continue
                        request = acks.pop(int(frame[2:marker]), None)
                        if request is None:
                            continue
                        mint, method, attempt = request
                        if mint not in active:
                            continue
                        try:
                            result = json.loads(frame[marker:])[0]
                        except (ValueError, TypeError, IndexError):
                            continue
                        if isinstance(result, dict) and result.get("ok") is True:
                            pool = result.get("pool")
                            if isinstance(pool, str) and ADDRESS.fullmatch(pool):
                                active[mint]["pool"] = pool
                                with sqlite3.connect(db_path) as db:
                                    db.execute("UPDATE candidates SET pool_id = COALESCE(pool_id, ?) WHERE mint = ?", (pool, mint))
                            active[mint][method] = True
                        elif isinstance(result, dict) and result.get("error") in ("not_found", "unavailable") and attempt < len(RETRY_SECONDS):
                            retries.append((time.monotonic() + RETRY_SECONDS[attempt], mint, method, attempt + 1))
                        continue
                    parsed = frame_event(frame)
                    if parsed is None:
                        continue
                    kind, event = parsed
                    if kind == "new_token" and event.get("protocol") == "PUMPFUN":
                        mint, pool = event.get("mint"), event.get("pool")
                        if isinstance(mint, str) and ADDRESS.fullmatch(mint) and isinstance(pool, str) and ADDRESS.fullmatch(pool):
                            save_launch(db_path, Launch(mint, "launch", "PUMPFUN", pool,
                                                        source_ms(event.get("timestamp"), now_ms)), now_ms, "shrine")
                    elif kind == "token_update":
                        save_price(db_path, event.get("pool"), event, now_ms)
                    elif kind == "trade":
                        signature = event.get("signature")
                        if not isinstance(signature, str) or not 64 <= len(signature) <= 128 or signature in seen:
                            continue
                        if save_trade(db_path, event.get("pool"), event, now_ms):
                            seen.add(signature)
                            seen_order.append(signature)
                            if len(seen_order) > 1024:
                                seen.remove(seen_order.popleft())
        except (OSError, TimeoutError, ValueError, WebSocketException, sqlite3.Error) as exc:
            logger.warning("shrine_disconnected error=%s", type(exc).__name__)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30)
