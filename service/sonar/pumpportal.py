"""Read PumpPortal's free launch stream into the local candidate database."""

import asyncio
import json
import logging
import math
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException


URL = "wss://pumpportal.fun/api/data"
ADDRESS = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}\Z")
logger = logging.getLogger("sonar.pumpportal")


@dataclass(frozen=True)
class Launch:
    mint: str
    kind: str
    pool: str | None
    pool_id: str | None
    source_ms: int | None


def parse_launch(message: str | bytes) -> Launch | None:
    try:
        item = json.loads(message)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(item, dict) or item.get("txType") not in ("create", "migrate"):
        return None
    mint = item.get("mint")
    if not isinstance(mint, str) or not ADDRESS.fullmatch(mint):
        return None
    pool = item.get("pool")
    pool = pool if isinstance(pool, str) and 0 < len(pool) <= 64 else None
    pool_id = item.get("poolId")
    pool_id = pool_id if isinstance(pool_id, str) and ADDRESS.fullmatch(pool_id) else None
    timestamp = item.get("timestamp")
    source_ms = None
    if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool) and math.isfinite(timestamp):
        if 1_000_000_000 <= timestamp < 100_000_000_000:
            source_ms = int(timestamp * 1000)
        elif 1_000_000_000_000 <= timestamp < 10_000_000_000_000:
            source_ms = int(timestamp)
    return Launch(mint, "launch" if item["txType"] == "create" else "migrate", pool, pool_id, source_ms)


def save_launch(db_path: Path, event: Launch, received_ms: int, source: str = "pumpportal") -> None:
    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT OR IGNORE INTO candidates (mint, pool, pool_id, first_seen_ms, last_seen_ms) VALUES (?, ?, ?, ?, ?)",
            (event.mint, event.pool, event.pool_id, received_ms, received_ms),
        )
        if event.kind == "migrate":
            if event.pool_id is not None:
                db.execute(
                    """UPDATE candidates SET price = NULL, price_unit = NULL, price_source = NULL,
                       price_source_ms = NULL, price_seen_ms = NULL
                       WHERE mint = ? AND pool_id IS NOT NULL AND pool_id != ?""",
                    (event.mint, event.pool_id),
                )
            elif event.pool is not None:
                db.execute(
                    """UPDATE candidates SET pool_id = NULL, price = NULL, price_unit = NULL,
                       price_source = NULL, price_source_ms = NULL, price_seen_ms = NULL
                       WHERE mint = ? AND pool IS NOT ?""",
                    (event.mint, event.pool),
                )
            db.execute(
                "UPDATE candidates SET last_seen_ms = MAX(last_seen_ms, ?), pool = COALESCE(?, pool), pool_id = COALESCE(?, pool_id) WHERE mint = ?",
                (received_ms, event.pool, event.pool_id, event.mint),
            )
        else:
            db.execute(
                "UPDATE candidates SET last_seen_ms = MAX(last_seen_ms, ?), pool = COALESCE(pool, ?), pool_id = COALESCE(pool_id, ?) WHERE mint = ?",
                (received_ms, event.pool, event.pool_id, event.mint),
            )
        db.execute(
            "INSERT OR IGNORE INTO candidate_events (mint, kind, source, pool, pool_id, source_ms, received_ms) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event.mint, event.kind, source, event.pool, event.pool_id, event.source_ms, received_ms),
        )


async def run(db_path: Path) -> None:
    backoff = 1
    while True:
        try:
            async with connect(URL, max_size=64 * 1024, max_queue=4, compression=None,
                               open_timeout=10, close_timeout=1) as websocket:
                await websocket.send('{"method":"subscribeNewToken"}')
                acknowledgement = json.loads(await asyncio.wait_for(websocket.recv(), timeout=10))
                if not isinstance(acknowledgement, dict) or "successfully subscribed" not in str(acknowledgement.get("message", "")).lower():
                    raise ValueError("subscription rejected")
                logger.info("pumpportal_connected")
                backoff = 1
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    event = parse_launch(message)
                    if event is not None:
                        save_launch(db_path, event, int(time.time() * 1000))
        except (OSError, TimeoutError, ValueError, WebSocketException, sqlite3.Error) as exc:
            logger.warning("pumpportal_disconnected error=%s", type(exc).__name__)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30)
