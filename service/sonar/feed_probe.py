"""Temporary, read-only measurements of the free PumpAPI stream."""

import argparse
import asyncio
import json
import math
import random
import resource
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException


STREAM_URL = "wss://stream.pumpapi.io/"
PORTAL_URL = "wss://pumpportal.fun/api/data"
EVENT_TYPES = {"transfer", "create", "buy", "sell", "migrate", "createPool", "add", "remove"}
POOLS = {"pump", "pump-amm", "raydium-launchpad", "raydium-cpmm", "meteora-damm-v1", "meteora-damm-v2", "meteora-dlmm"}
AGE_SAMPLE_SIZE = 8192


@dataclass(frozen=True)
class Event:
    kind: str
    pool: str
    pool_id: str | None
    mint: str | None
    timestamp_ms: float | None


def parse_event(message: str | bytes) -> Event:
    try:
        item = json.loads(message)
    except (ValueError, UnicodeDecodeError, TypeError) as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(item, dict):
        raise ValueError("expected object")
    kind = item.get("txType") or item.get("action")
    if not isinstance(kind, str) or not kind:
        raise ValueError("missing transaction type")
    pool = item.get("pool")
    mint = item.get("mint")
    if kind == "create" and pool == "pump" and (
        not isinstance(mint, str) or not 0 < len(mint) <= 64
    ):
        raise ValueError("Pump.fun launch without mint")
    timestamp = item.get("timestamp")
    if timestamp is not None and (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, (int, float))
        or not math.isfinite(timestamp)
    ):
        raise ValueError("invalid timestamp")
    pool_id = item.get("poolId")
    return Event(
        kind if kind in EVENT_TYPES else "other",
        pool if isinstance(pool, str) and pool in POOLS else "other",
        pool_id if isinstance(pool_id, str) and 0 < len(pool_id) <= 128 else None,
        mint if isinstance(mint, str) else None,
        timestamp,
    )


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    position = (len(values) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    return round(values[low] + (values[high] - values[low]) * (position - low), 1)


class ProbeStats:
    def __init__(self, launches_db: sqlite3.Connection, *, compare_portal: bool = False):
        self.db = launches_db
        self.compare_portal = compare_portal
        self.started_at = time.time()
        self.started_mono = time.monotonic()
        self.started_cpu = time.process_time()
        self.last_message_mono = self.started_mono
        self.last_save_mono = self.started_mono
        self.counts = Counter()
        self.minute_counts = Counter()
        self.pool_ids: dict[str, tuple[int, int]] = {}
        self.ages: list[float] = []
        self.age_count = 0
        self.first_source_timestamp_ms: float | None = None
        self.last_source_timestamp_ms: float | None = None
        self.missing_timestamps = 0
        self.negative_ages = 0
        self.messages = 0
        self.malformed = 0
        self.bytes_received = 0
        self.unique_pump_launches = 0
        self.duplicate_pump_launches = 0
        self.connections = 0
        self.disconnects = 0
        self.connection_failures = 0
        self.connection_error_types = Counter()
        self.pump_connected = False
        self.portal_connected = False
        self.comparison_since: float | None = None
        self.comparison_seconds = 0.0
        self.portal_messages = 0
        self.portal_connections = 0
        self.portal_subscriptions = 0
        self.portal_disconnects = 0
        self.portal_connection_failures = 0
        self.portal_error_types = Counter()
        self.down_since: float | None = None
        self.down_seconds = 0.0
        self.max_down_seconds = 0.0
        self.gaps_over_5s = 0
        self.max_gap_s = 0.0

    def observe(self, message: str | bytes, *, now_ms: float | None = None, now_mono: float | None = None) -> None:
        now_ms = time.time() * 1000 if now_ms is None else now_ms
        now_mono = time.monotonic() if now_mono is None else now_mono
        gap = now_mono - self.last_message_mono
        self.max_gap_s = max(self.max_gap_s, gap)
        self.gaps_over_5s += gap > 5
        self.last_message_mono = now_mono
        self.messages += 1
        self.bytes_received += len(message.encode() if isinstance(message, str) else message)
        self.minute_counts[int((now_mono - self.started_mono) // 60)] += 1

        try:
            event = parse_event(message)
        except ValueError:
            self.malformed += 1
            return
        self.counts[(event.kind, event.pool)] += 1
        if event.pool_id:
            if event.pool_id in self.pool_ids:
                count, error = self.pool_ids[event.pool_id]
                self.pool_ids[event.pool_id] = (count + 1, error)
            elif len(self.pool_ids) < 32:
                self.pool_ids[event.pool_id] = (1, 0)
            else:
                smallest = min(self.pool_ids, key=lambda key: self.pool_ids[key][0])
                count, _ = self.pool_ids.pop(smallest)
                self.pool_ids[event.pool_id] = (count + 1, count)
        if event.kind == "create" and event.pool == "pump":
            if self.db.execute("INSERT OR IGNORE INTO seen_mints VALUES (?)", (event.mint,)).rowcount:
                self.unique_pump_launches += 1
            else:
                self.duplicate_pump_launches += 1
            if self.compare_portal and self.portal_connected:
                self.db.execute("INSERT OR IGNORE INTO compare_pump VALUES (?)", (event.mint,))
        if event.timestamp_ms is None or event.timestamp_ms < 1_000_000_000_000:
            self.missing_timestamps += 1
            return
        if self.first_source_timestamp_ms is None:
            self.first_source_timestamp_ms = event.timestamp_ms
        self.last_source_timestamp_ms = event.timestamp_ms
        age = now_ms - event.timestamp_ms
        self.negative_ages += age < 0
        self.age_count += 1
        if len(self.ages) < AGE_SAMPLE_SIZE:
            self.ages.append(age)
        else:
            slot = random.randrange(self.age_count)
            if slot < AGE_SAMPLE_SIZE:
                self.ages[slot] = age

    def set_connected(self, provider: str, connected: bool) -> None:
        was_comparing = self.pump_connected and self.portal_connected
        if provider == "pump":
            self.pump_connected = connected
        else:
            self.portal_connected = connected
        is_comparing = self.pump_connected and self.portal_connected
        if is_comparing and not was_comparing:
            self.comparison_since = time.monotonic()
        elif was_comparing and not is_comparing and self.comparison_since is not None:
            self.comparison_seconds += time.monotonic() - self.comparison_since
            self.comparison_since = None

    def observe_portal(self, message: str | bytes) -> None:
        self.portal_messages += 1
        try:
            item = json.loads(message)
        except (ValueError, UnicodeDecodeError, TypeError):
            return
        if (
            isinstance(item, dict)
            and item.get("txType") == "create"
            and item.get("pool") == "pump"
            and isinstance(item.get("mint"), str)
            and 0 < len(item["mint"]) <= 64
            and self.pump_connected
        ):
            self.db.execute("INSERT OR IGNORE INTO compare_portal VALUES (?)", (item["mint"],))

    def report(self, *, status: str = "running") -> dict:
        now_mono = time.monotonic()
        duration = max(now_mono - self.started_mono, 0.001)
        ages = sorted(self.ages)
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024
        counts = {f"{kind}/{pool}": count for (kind, pool), count in sorted(self.counts.items())}
        report = {
            "status": status,
            "started_at_utc": datetime.fromtimestamp(self.started_at, UTC).isoformat(),
            "duration_s": round(duration, 1),
            "messages": self.messages,
            "malformed_messages": self.malformed,
            "event_counts_by_type_and_pool": counts,
            "top_pool_ids_approx": [
                {"pool_id": pool_id, "count_upper_bound": count, "error": error}
                for pool_id, (count, error) in sorted(self.pool_ids.items(), key=lambda pair: -pair[1][0])[:20]
            ],
            "unique_pump_launches": self.unique_pump_launches,
            "duplicate_pump_launches": self.duplicate_pump_launches,
            "connections": self.connections,
            "disconnects": self.disconnects,
            "connection_failures": self.connection_failures,
            "connection_error_types": dict(self.connection_error_types),
            "connection_down_s": round(self.down_seconds + (now_mono - self.down_since if self.down_since else 0), 1),
            "max_connection_down_s": round(max(self.max_down_seconds, now_mono - self.down_since if self.down_since else 0), 1),
            "gaps_over_5s": self.gaps_over_5s + (now_mono - self.last_message_mono > 5),
            "max_message_gap_s": round(max(self.max_gap_s, now_mono - self.last_message_mono), 1),
            "message_rate_per_s": round(self.messages / duration, 2),
            "messages_per_minute": [self.minute_counts[index] for index in range(math.ceil(duration / 60))],
            "bytes_received": self.bytes_received,
            "projected_gb_per_30_days": round(self.bytes_received / duration * 30 * 86400 / 1e9, 2),
            "event_age_ms_approx": {
                "count": self.age_count,
                "sample_size": len(ages),
                "first_source_timestamp_ms": self.first_source_timestamp_ms,
                "last_source_timestamp_ms": self.last_source_timestamp_ms,
                "missing_or_unusable_timestamp": self.missing_timestamps,
                "negative_age_count": self.negative_ages,
                "p50": percentile(ages, 0.5),
                "p95": percentile(ages, 0.95),
                "p99": percentile(ages, 0.99),
            },
            "cpu_percent_of_one_core": round((time.process_time() - self.started_cpu) / duration * 100, 1),
            "peak_rss_mb": round(rss_mb, 1),
        }
        if self.compare_portal:
            pump = self.db.execute("SELECT COUNT(*) FROM compare_pump").fetchone()[0]
            portal = self.db.execute("SELECT COUNT(*) FROM compare_portal").fetchone()[0]
            shared = self.db.execute(
                "SELECT COUNT(*) FROM compare_pump JOIN compare_portal USING (mint)"
            ).fetchone()[0]
            report["pumpportal_comparison"] = {
                "status": "observed" if self.portal_subscriptions else "unavailable",
                "overlapping_connection_s": round(
                    self.comparison_seconds + (now_mono - self.comparison_since if self.comparison_since else 0), 1
                ),
                "pump_launches": pump,
                "portal_launches": portal,
                "shared_launches": shared,
                "pump_only": pump - shared,
                "portal_only": portal - shared,
                "portal_messages": self.portal_messages,
                "portal_connections": self.portal_connections,
                "portal_subscriptions": self.portal_subscriptions,
                "portal_disconnects": self.portal_disconnects,
                "portal_connection_failures": self.portal_connection_failures,
                "portal_error_types": dict(self.portal_error_types),
            }
        return report

    def save(self, output: Path, *, status: str = "running") -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text(json.dumps(self.report(status=status), separators=(",", ":")) + "\n")
        temporary.replace(output)
        self.last_save_mono = time.monotonic()


async def collect(stats: ProbeStats, duration_s: float, output: Path, *, connector=None, initial_backoff: float = 1) -> None:
    connector = connect if connector is None else connector
    deadline = stats.started_mono + duration_s
    backoff = initial_backoff
    while time.monotonic() < deadline:
        connected = False
        try:
            async with connector(STREAM_URL, max_size=256 * 1024, max_queue=4, compression=None, open_timeout=10, close_timeout=1) as websocket:
                connected = True
                stats.connections += 1
                stats.set_connected("pump", True)
                if stats.down_since is not None:
                    downtime = time.monotonic() - stats.down_since
                    stats.down_seconds += downtime
                    stats.max_down_seconds = max(stats.max_down_seconds, downtime)
                    stats.down_since = None
                backoff = initial_backoff
                while (remaining := deadline - time.monotonic()) > 0:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=min(remaining, 5))
                    except TimeoutError:
                        if time.monotonic() - stats.last_save_mono >= 60:
                            stats.save(output)
                        continue
                    stats.observe(message)
                    if time.monotonic() - stats.last_save_mono >= 60:
                        stats.save(output)
        except (OSError, TimeoutError, WebSocketException) as exc:
            stats.connection_error_types[type(exc).__name__] += 1
            if connected:
                stats.disconnects += 1
            else:
                stats.connection_failures += 1
            if stats.down_since is None:
                stats.down_since = time.monotonic()
            stats.save(output)
        finally:
            if connected:
                stats.set_connected("pump", False)
        if time.monotonic() < deadline:
            await asyncio.sleep(min(backoff, deadline - time.monotonic()))
            backoff = min(backoff * 2, 30)


async def collect_portal(stats: ProbeStats, duration_s: float, output: Path) -> None:
    deadline = stats.started_mono + duration_s
    backoff = 1
    while time.monotonic() < deadline:
        subscribed = False
        try:
            async with connect(PORTAL_URL, max_size=64 * 1024, max_queue=4, compression=None, open_timeout=10, close_timeout=1) as websocket:
                stats.portal_connections += 1
                await websocket.send('{"method":"subscribeNewToken"}')
                acknowledgement = json.loads(await asyncio.wait_for(websocket.recv(), timeout=10))
                stats.portal_messages += 1
                if not isinstance(acknowledgement, dict) or "successfully subscribed" not in str(acknowledgement.get("message", "")).lower():
                    raise ValueError("PumpPortal launch subscription unavailable")
                subscribed = True
                stats.portal_subscriptions += 1
                stats.set_connected("portal", True)
                backoff = 1
                while (remaining := deadline - time.monotonic()) > 0:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=min(remaining, 5))
                    except TimeoutError:
                        continue
                    stats.observe_portal(message)
        except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
            stats.portal_error_types[type(exc).__name__] += 1
            if subscribed:
                stats.portal_disconnects += 1
            else:
                stats.portal_connection_failures += 1
            stats.save(output)
        finally:
            if subscribed:
                stats.set_connected("portal", False)
        if time.monotonic() < deadline:
            await asyncio.sleep(min(backoff, deadline - time.monotonic()))
            backoff = min(backoff * 2, 30)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=120, help="sample duration in seconds (default: 120)")
    parser.add_argument("--output", type=Path, help="aggregate JSON path (default: data/probes/pumpapi-<time>.json)")
    parser.add_argument("--compare-pumpportal", action="store_true", help="compare free Pump.fun launch subscriptions during overlapping connections")
    args = parser.parse_args()
    if not 1 <= args.duration <= 172800:
        parser.error("duration must be between 1 second and 48 hours")
    output = args.output or Path("data/probes") / f"pumpapi-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    with tempfile.TemporaryDirectory(prefix="sonar-probe-") as temp:
        with closing(sqlite3.connect(Path(temp) / "seen.db", isolation_level=None)) as db:
            db.execute("CREATE TABLE seen_mints (mint TEXT PRIMARY KEY)")
            if args.compare_pumpportal:
                db.execute("CREATE TABLE compare_pump (mint TEXT PRIMARY KEY)")
                db.execute("CREATE TABLE compare_portal (mint TEXT PRIMARY KEY)")
            stats = ProbeStats(db, compare_portal=args.compare_pumpportal)
            status = "complete"
            try:
                if args.compare_pumpportal:
                    async def run_both() -> None:
                        await asyncio.gather(collect(stats, args.duration, output), collect_portal(stats, args.duration, output))
                    asyncio.run(run_both())
                else:
                    asyncio.run(collect(stats, args.duration, output))
            except KeyboardInterrupt:
                status = "interrupted"
            except Exception:
                status = "failed"
                raise
            finally:
                stats.save(output, status=status)
    print(output)


if __name__ == "__main__":
    main()
