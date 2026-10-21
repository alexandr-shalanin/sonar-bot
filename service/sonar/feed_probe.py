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
BOUNDARY_S = 60
PUMP_IDLE_TIMEOUT_S = 5


@dataclass(frozen=True)
class Event:
    kind: str
    pool: str
    pool_id: str | None
    mint: str | None
    timestamp_ms: float | None
    signature: str | None


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
    signature = next((item[key] for key in ("signature", "txSignature", "txSig")
                      if isinstance(item.get(key), str) and 0 < len(item[key]) <= 128), None)
    return Event(
        kind if kind in EVENT_TYPES else "other",
        pool if isinstance(pool, str) and 0 < len(pool) <= 64 else "other",
        pool_id if isinstance(pool_id, str) and 0 < len(pool_id) <= 128 else None,
        mint if isinstance(mint, str) else None,
        timestamp,
        signature,
    )


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    position = (len(values) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    return round(values[low] + (values[high] - values[low]) * (position - low), 1)


def init_db(db: sqlite3.Connection, *, compare_portal: bool) -> None:
    db.execute("CREATE TABLE seen_mints (mint TEXT PRIMARY KEY)")
    if compare_portal:
        db.execute("""CREATE TABLE launches (
            provider TEXT NOT NULL, mint TEXT NOT NULL, pool TEXT NOT NULL,
            signature TEXT, source_ms REAL, receipt_ms REAL NOT NULL,
            PRIMARY KEY (provider, mint, pool))""")


class ProbeStats:
    def __init__(self, launches_db: sqlite3.Connection, *, compare_portal: bool = False,
                 duration_s: float = 120, warmup_s: float = 0, grace_s: float = 0):
        self.db = launches_db
        self.compare_portal = compare_portal
        self.started_at = time.time()
        self.started_mono = time.monotonic()
        self.duration_s = duration_s
        self.warmup_s = warmup_s
        self.grace_s = grace_s
        self.window_start_ms = (self.started_at + warmup_s) * 1000
        self.window_end_ms = (self.started_at + warmup_s + duration_s) * 1000
        self.down_started_ms = {"pump": self.started_at * 1000, "portal": self.started_at * 1000}
        self.outages: dict[str, list[tuple[float, float]]] = {"pump": [], "portal": []}
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
        self.idle_reconnects = 0
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
        self.counts[(event.kind, event.pool if event.pool in POOLS else "other")] += 1
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
        if self.compare_portal and event.kind == "create" and event.mint and len(event.mint) <= 64:
            self.record_launch("pump", event, now_ms)
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

    def record_launch(self, provider: str, event: Event, receipt_ms: float) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO launches VALUES (?, ?, ?, ?, ?, ?)",
            (provider, event.mint, event.pool, event.signature, event.timestamp_ms, receipt_ms),
        )

    def set_connected(self, provider: str, connected: bool, *, now_ms: float | None = None,
                      now_mono: float | None = None) -> None:
        now_ms = time.time() * 1000 if now_ms is None else now_ms
        now_mono = time.monotonic() if now_mono is None else now_mono
        if (self.pump_connected if provider == "pump" else self.portal_connected) == connected:
            return
        if connected:
            self.outages[provider].append((self.down_started_ms[provider], now_ms))
        else:
            self.down_started_ms[provider] = now_ms
        was_comparing = self.pump_connected and self.portal_connected
        if provider == "pump":
            self.pump_connected = connected
        else:
            self.portal_connected = connected
        is_comparing = self.pump_connected and self.portal_connected
        if is_comparing and not was_comparing:
            self.comparison_since = now_mono
        elif was_comparing and not is_comparing and self.comparison_since is not None:
            self.comparison_seconds += now_mono - self.comparison_since
            self.comparison_since = None

    def observe_portal(self, message: str | bytes, *, now_ms: float | None = None) -> None:
        self.portal_messages += 1
        try:
            event = parse_event(message)
        except ValueError:
            return
        if event.kind == "create" and event.mint and 0 < len(event.mint) <= 64:
            self.record_launch("portal", event, time.time() * 1000 if now_ms is None else now_ms)

    def comparison_report(self, now_ms: float) -> dict:
        def affected_by_outage(provider: str, source_ms: float | None, receipt_ms: float) -> bool:
            earliest = min(source_ms, receipt_ms - 60_000) if source_ms and source_ms > 1_000_000_000_000 else receipt_ms - 60_000
            intervals = self.outages[provider]
            if not (self.pump_connected if provider == "pump" else self.portal_connected):
                intervals = [*intervals, (self.down_started_ms[provider], now_ms)]
            return any(start <= receipt_ms + 60_000 and end >= earliest for start, end in intervals)

        def side(provider: str, other: str) -> tuple[dict, list[float]]:
            result = Counter()
            result["unmatched_sample"] = []
            differences: list[float] = []
            rows = self.db.execute(
                """SELECT mint, pool, signature, source_ms, receipt_ms FROM launches
                   WHERE provider = ? AND pool = 'pump' AND receipt_ms >= ? AND receipt_ms < ?""",
                (provider, self.window_start_ms, self.window_end_ms),
            )
            for mint, pool, signature, source_ms, receipt_ms in rows:
                result["in_window"] += 1
                counterpart = self.db.execute(
                    "SELECT pool, signature, source_ms, receipt_ms FROM launches WHERE provider = ? AND mint = ? AND pool = ?",
                    (other, mint, pool),
                ).fetchone()
                other_pool = None
                if counterpart is None:
                    other_pool = self.db.execute(
                        "SELECT pool FROM launches WHERE provider = ? AND mint = ? LIMIT 1", (other, mint)
                    ).fetchone()
                boundary = (receipt_ms < self.window_start_ms + BOUNDARY_S * 1000
                            or receipt_ms >= self.window_end_ms - BOUNDARY_S * 1000
                            or (source_ms is not None and source_ms > 1_000_000_000_000
                                and not self.window_start_ms <= source_ms < self.window_end_ms))
                outage = affected_by_outage(other, source_ms, receipt_ms)
                signature_conflict = bool(counterpart and signature and counterpart[1] and signature != counterpart[1])
                if counterpart and not signature_conflict:
                    result["matched"] += 1
                    result["matched_without_both_signatures"] += not (signature and counterpart[1])
                    difference = counterpart[3] - receipt_ms
                    differences.append(difference)
                    result["late_in_grace"] += counterpart[3] >= self.window_end_ms
                    result["arrival_over_60s"] += difference > 60_000
                    if not boundary and not outage:
                        result["eligible_matched"] += 1
                else:
                    result["unmatched"] += 1
                    reason = ("signature_conflict" if signature_conflict else "pool_label_mismatch" if other_pool else "window_boundary" if boundary
                              else "connection_outage" if outage else "unexplained")
                    result[reason] += 1
                    if len(result["unmatched_sample"]) < 12:
                        result["unmatched_sample"].append({
                            "mint": mint, "pool": pool, "signature": signature,
                            "source_ms": source_ms, "receipt_ms": receipt_ms,
                            "reason": reason, "other_pool": other_pool[0] if other_pool else None,
                            "other_signature": counterpart[1] if signature_conflict else None,
                        })
                if not boundary and not outage and not other_pool and not signature_conflict:
                    result["eligible"] += 1
            return dict(result), differences

        portal, pump_minus_portal = side("portal", "pump")
        pump, _ = side("pump", "portal")
        eligible = portal.get("eligible", 0)
        return {
            "status": "observed" if self.portal_subscriptions else "unavailable",
            "window_start_utc": datetime.fromtimestamp(self.window_start_ms / 1000, UTC).isoformat(),
            "window_end_utc": datetime.fromtimestamp(self.window_end_ms / 1000, UTC).isoformat(),
            "warmup_s": self.warmup_s, "grace_s": self.grace_s,
            "overlapping_connection_s": round(
                self.comparison_seconds + (time.monotonic() - self.comparison_since if self.comparison_since else 0), 1
            ),
            "portal": portal,
            "pump": pump,
            "eligible_coverage_percent": round(100 * portal.get("eligible_matched", 0) / eligible, 1) if eligible else None,
            "pump_minus_portal_arrival_ms": {
                "count": len(pump_minus_portal), "p50": percentile(sorted(pump_minus_portal), 0.5),
                "p95": percentile(sorted(pump_minus_portal), 0.95),
                "p99": percentile(sorted(pump_minus_portal), 0.99),
            },
            "portal_messages": self.portal_messages,
            "portal_connections": self.portal_connections,
            "portal_subscriptions": self.portal_subscriptions,
            "portal_disconnects": self.portal_disconnects,
            "portal_connection_failures": self.portal_connection_failures,
            "portal_error_types": dict(self.portal_error_types),
        }

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
            "idle_reconnects": self.idle_reconnects,
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
            "local_clock_step_ms": round(((time.time() - self.started_at) - duration) * 1000, 1),
        }
        if self.compare_portal:
            report["pumpportal_comparison"] = self.comparison_report(time.time() * 1000)
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
                while (remaining := deadline - time.monotonic()) > 0:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=min(remaining, PUMP_IDLE_TIMEOUT_S))
                    except TimeoutError:
                        if time.monotonic() >= deadline:
                            break
                        stats.idle_reconnects += 1
                        raise TimeoutError("PumpAPI stream idle")
                    stats.observe(message)
                    backoff = initial_backoff
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
    parser.add_argument("--duration", type=float, default=120, help="measurement window in seconds (default: 120)")
    parser.add_argument("--output", type=Path, help="aggregate JSON path (default: data/probes/pumpapi-<time>.json)")
    parser.add_argument("--compare-pumpportal", action="store_true", help="compare free Pump.fun launch subscriptions with 60s warm-up and 90s grace")
    args = parser.parse_args()
    if not 1 <= args.duration <= 172800:
        parser.error("duration must be between 1 second and 48 hours")
    output = args.output or Path("data/probes") / f"pumpapi-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    warmup_s, grace_s = (60, 90) if args.compare_pumpportal else (0, 0)
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence_db = output.with_suffix(".launches.sqlite3") if args.compare_pumpportal else None
    if evidence_db and evidence_db.exists():
        parser.error(f"launch evidence already exists: {evidence_db}")
    with tempfile.TemporaryDirectory(prefix="sonar-probe-") as temp:
        with closing(sqlite3.connect(evidence_db or Path(temp) / "seen.db", isolation_level=None)) as db:
            init_db(db, compare_portal=args.compare_pumpportal)
            stats = ProbeStats(db, compare_portal=args.compare_pumpportal,
                               duration_s=args.duration, warmup_s=warmup_s, grace_s=grace_s)
            total_s = warmup_s + args.duration + grace_s
            status = "complete"
            try:
                if args.compare_pumpportal:
                    async def run_both() -> None:
                        await asyncio.gather(collect(stats, total_s, output), collect_portal(stats, total_s, output))
                    asyncio.run(run_both())
                else:
                    asyncio.run(collect(stats, total_s, output))
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
