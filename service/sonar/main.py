import asyncio
import json
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles

from .pumpportal import run as run_pumpportal
from .risk import risk_view, run as run_risk
from .shrine import run as run_shrine
from .signals import signal_view
from .inspector import InspectorBusy, InspectorRequest, inspect_mint


DATA_DIR = Path(os.environ.get("SONAR_DATA_DIR", "data"))
DB_PATH = DATA_DIR / "sonar.db"
WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
logger = logging.getLogger("sonar")
# shortcut: 30 seconds is a provisional freshness cutoff; calibrate it from longer feed runs.
PRICE_FRESH_MS = 30_000


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        if db.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
            raise RuntimeError("SQLite WAL mode is required")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS candidates (
                mint TEXT PRIMARY KEY,
                pool TEXT,
                pool_id TEXT,
                first_seen_ms INTEGER NOT NULL,
                last_seen_ms INTEGER NOT NULL,
                price REAL,
                price_unit TEXT,
                price_source TEXT,
                price_source_ms INTEGER,
                price_seen_ms INTEGER
            );
            CREATE TABLE IF NOT EXISTS candidate_events (
                id INTEGER PRIMARY KEY,
                mint TEXT NOT NULL,
                kind TEXT NOT NULL,
                source TEXT NOT NULL,
                pool TEXT,
                pool_id TEXT,
                source_ms INTEGER,
                received_ms INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS candidate_events_mint_received
                ON candidate_events (mint, received_ms);
            CREATE INDEX IF NOT EXISTS candidate_events_received
                ON candidate_events (received_ms);
            CREATE UNIQUE INDEX IF NOT EXISTS candidate_events_unique_launch
                ON candidate_events (mint, source, kind)
                WHERE kind IN ('launch', 'migrate');
            CREATE INDEX IF NOT EXISTS candidates_first_seen ON candidates (first_seen_ms);
            CREATE INDEX IF NOT EXISTS candidates_pool_id ON candidates (pool_id);
            CREATE TABLE IF NOT EXISTS price_samples (
                mint TEXT NOT NULL,
                pool_id TEXT NOT NULL,
                bucket_ms INTEGER NOT NULL,
                price_usd REAL NOT NULL,
                source_ms INTEGER NOT NULL,
                received_ms INTEGER NOT NULL,
                PRIMARY KEY (mint, pool_id, bucket_ms)
            );
            CREATE INDEX IF NOT EXISTS price_samples_bucket ON price_samples (bucket_ms);
            CREATE TABLE IF NOT EXISTS trade_minutes (
                mint TEXT NOT NULL,
                pool_id TEXT NOT NULL,
                minute_ms INTEGER NOT NULL,
                buys INTEGER NOT NULL DEFAULT 0,
                sells INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (mint, pool_id, minute_ms)
            );
            CREATE INDEX IF NOT EXISTS trade_minutes_minute ON trade_minutes (minute_ms);
            CREATE TABLE IF NOT EXISTS risk_reports (
                mint TEXT NOT NULL,
                provider TEXT NOT NULL,
                checked_ms INTEGER NOT NULL,
                status TEXT NOT NULL,
                facts_json TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                PRIMARY KEY (mint, provider)
            );
        """)
    logger.info("database_ready")
    feed = asyncio.create_task(run_pumpportal(DB_PATH)) if os.environ.get("SONAR_PUMPPORTAL_ENABLED", "1") != "0" else None
    shrine = asyncio.create_task(run_shrine(DB_PATH)) if os.environ.get("SONAR_SHRINE_ENABLED", "1") != "0" else None
    risk = asyncio.create_task(run_risk(DB_PATH)) if os.environ.get("SONAR_RISK_ENABLED", "1") != "0" else None
    try:
        yield
    finally:
        if feed is not None:
            feed.cancel()
            with suppress(asyncio.CancelledError):
                await feed
        if shrine is not None:
            shrine.cancel()
            with suppress(asyncio.CancelledError):
                await shrine
        if risk is not None:
            risk.cancel()
            with suppress(asyncio.CancelledError):
                await risk


app = FastAPI(lifespan=lifespan)


@app.post("/inspector")
async def inspector(request: InspectorRequest, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    try:
        report = await inspect_mint(request.mint)
    except InspectorBusy as exc:
        raise HTTPException(status_code=429, detail="Inspector busy; retry shortly", headers={"Retry-After": "5"}) from exc
    if report["status"] == "unavailable":
        response.status_code = 503
    return report


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True) as db:
            db.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


@app.get("/candidates")
def candidates() -> list[dict]:
    now_ms = time.time_ns() // 1_000_000
    try:
        with sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True) as db:
            rows = db.execute(
                """SELECT mint, pool, pool_id, first_seen_ms, last_seen_ms,
                          price, price_unit, price_source, price_source_ms, price_seen_ms
                   FROM candidates ORDER BY first_seen_ms DESC LIMIT 100"""
            ).fetchall()
            report_rows = db.execute(
                """SELECT mint, provider, status, checked_ms, facts_json FROM risk_reports
                   WHERE mint IN (SELECT mint FROM candidates ORDER BY first_seen_ms DESC LIMIT 100)"""
            ).fetchall()
            price_rows = db.execute(
                """SELECT mint, pool_id, source_ms, price_usd FROM price_samples
                   WHERE bucket_ms >= ? AND mint IN
                   (SELECT mint FROM candidates ORDER BY first_seen_ms DESC LIMIT 100)""",
                (now_ms - 360_000,),
            ).fetchall()
            trade_rows = db.execute(
                """SELECT mint, pool_id, minute_ms, buys, sells FROM trade_minutes
                   WHERE minute_ms >= ? AND mint IN
                   (SELECT mint FROM candidates ORDER BY first_seen_ms DESC LIMIT 100)""",
                (now_ms - 360_000,),
            ).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    result = []
    reports: dict[str, dict] = {}
    samples: dict[tuple[str, str], list[tuple[int, float]]] = {}
    trades: dict[tuple[str, str], list[tuple[int, int, int]]] = {}
    for mint, pool_id, sample_ms, sample_price in price_rows:
        samples.setdefault((mint, pool_id), []).append((sample_ms, sample_price))
    for mint, pool_id, minute_ms, buys, sells in trade_rows:
        trades.setdefault((mint, pool_id), []).append((minute_ms, buys, sells))
    for mint, provider, report_status, checked_ms, facts_json in report_rows:
        reports.setdefault(mint, {})[provider] = (report_status, checked_ms, json.loads(facts_json))
    for mint, pool, pool_id, first_seen_ms, last_seen_ms, price, unit, source, source_ms, seen_ms in rows:
        has_price = price is not None and price > 0 and unit == "USD" and source_ms is not None and seen_ms is not None
        age_ms = max(0, now_ms - source_ms) if has_price else None
        if not has_price:
            status = "unavailable"
        elif age_ms > PRICE_FRESH_MS or now_ms - seen_ms > PRICE_FRESH_MS:
            status = "stale"
        else:
            status = "fresh"
        pool_trades = trades.get((mint, pool_id), [])
        recent_sells = sum(sells for minute, _, sells in pool_trades
                           if now_ms - 120_000 <= minute <= now_ms // 60_000 * 60_000)
        result.append({
            "mint": mint, "pool": pool, "pool_id": pool_id,
            "first_seen_ms": first_seen_ms, "last_seen_ms": last_seen_ms,
            "price_usd": price if has_price else None,
            "price_source": source if has_price else None,
            "price_source_ms": source_ms if has_price else None,
            "price_seen_ms": seen_ms if has_price else None,
            "price_age_ms": age_ms,
            "price_status": status,
            "signals": signal_view(now_ms, price if has_price else None, source_ms, status,
                                   samples.get((mint, pool_id), []), pool_trades),
            "risk": risk_view(reports.get(mint, {}), now_ms, pool_id,
                              recent_sells, status == "fresh"),
        })
    return result


if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
