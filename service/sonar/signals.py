"""Small observed market windows; no ranking or trading recommendation."""

import math


def signal_view(now_ms: int, price: float | None, price_source_ms: int | None,
                price_status: str, samples: list[tuple[int, float]],
                trade_minutes: list[tuple[int, int, int]]) -> dict:
    result = {}
    for label, window_ms in (("1m", 60_000), ("5m", 300_000)):
        baseline = None
        if price_status == "fresh" and price is not None and price_source_ms is not None and price_source_ms <= now_ms:
            target = price_source_ms - window_ms
            baseline = min((sample for sample in samples if sample[1] > 0 and
                            sample[0] <= price_source_ms and abs(sample[0] - target) <= 15_000),
                           key=lambda sample: abs(sample[0] - target), default=None)
        change = (price / baseline[1] - 1) * 100 if baseline else None
        result[f"price_change_{label}_pct"] = round(change, 2) if change is not None and math.isfinite(change) else None
        first_bucket = (now_ms - window_ms) // 60_000 * 60_000
        last_bucket = now_ms // 60_000 * 60_000
        result[f"observed_buys_{label}_approx"] = sum(buys for minute, buys, _ in trade_minutes if first_bucket <= minute <= last_bucket)
        result[f"observed_sells_{label}_approx"] = sum(sells for minute, _, sells in trade_minutes if first_bucket <= minute <= last_bucket)
    return result
