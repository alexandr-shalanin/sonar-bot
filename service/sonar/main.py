import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles


DATA_DIR = Path(os.environ.get("SONAR_DATA_DIR", "data"))
DB_PATH = DATA_DIR / "sonar.db"
WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
logger = logging.getLogger("sonar")


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
    logger.info("database_ready")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True) as db:
            db.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
