# Step 2: feed probe

The probe opens one PumpAPI WebSocket and reads the free, unfiltered stream. It sends no orders or wallet data. `--compare-pumpportal` opens one separate PumpPortal connection and subscribes only to free `subscribeNewToken` launch events. It does not subscribe to metered trade data. No API key is required for the observed launch-only connection, though provider access rules may change.

From the repository root, install the Python requirements, then run from `service/`:

```sh
.venv/bin/pip install -r service/requirements.txt
cd service
../.venv/bin/python -m sonar.feed_probe --duration 120 --compare-pumpportal
```

The command prints the path of a compact JSON result under `service/data/probes/`. These local results are ignored by Git. Set `--output` to choose another path. The file is refreshed at least once a minute and after connection errors. With `--compare-pumpportal`, a sibling `.launches.sqlite3` file retains **only** each launch's provider, mint, pool label, optional transaction signature, optional source timestamp, and local receipt time. Repeated launches retain their first receipt time. No trade messages or full transactions are saved. Without comparison, launch deduplication uses a temporary SQLite file. In memory, the probe keeps counters, at most 8,192 event ages, and 32 approximate top pool IDs. WebSocket queues and frame sizes are capped.

If PumpAPI sends no messages for five seconds, the probe closes that connection and reconnects with backoff. The JSON report counts these events in `idle_reconnects`; reconnecting cannot recover messages missed during the gap.

Comparison mode adds **60 seconds of warm-up** before the requested measurement window and **90 seconds of grace** afterward. For example, `--duration 1800` runs about 32.5 minutes total. It compares Pump.fun launch mints with the same pool label and, when both feeds provide signatures, the same transaction signature. It counts arrivals after the window but within grace as late matches. Unmatched launches near either window boundary, around a connection outage, or with a conflicting pool label or signature are separate from unexplained omissions. The coverage percentage excludes uncertain boundary and outage cases; it is meaningful only with at least 100 eligible PumpPortal launches and substantial simultaneous connectivity. Arrival-time difference is **PumpAPI local receipt minus PumpPortal local receipt** for matched launches; negative means PumpAPI arrived first. This is separate from PumpAPI source-timestamp event age. Check the local clock before and after a run; the JSON also records wall-clock versus monotonic-clock drift.

On this macOS Python installation, the default CA path is missing. Use `SSL_CERT_FILE=/etc/ssl/cert.pem` before the command if certificate verification fails. Keep TLS verification enabled.

## 24–48 hour laptop trial

Run once on the 4 GB laptop during both quiet and busy periods, with its clock synchronized. The requested duration excludes warm-up and grace:

```sh
cd service
../.venv/bin/python -m sonar.feed_probe --duration 86400 --compare-pumpportal --output data/probes/pumpapi-24h.json
```

Use `--duration 172800` for 48 hours. Keep the laptop awake, record its network connection and any other workloads, and inspect the JSON at the end and during the run. Repeat without PumpPortal if its free launch subscription stops working. Do not put provider keys in the command line, app, output path, or Git.

Before selecting a feed, use these provisional gates and investigate failures:

- **Freshness:** clock-synchronized event age p95 below 5 seconds and p99 below 15 seconds; verify what the provider's `timestamp` actually marks. Event age is local receipt time minus source timestamp, **not a precise network latency measurement**.
- **Continuity:** no unexplained message gap above 30 seconds; connection downtime below 60 seconds per outage; inspect minute counts, disconnects, and failed reconnects. A quiet interval can also create a gap.
- **Relative launch coverage:** compare at least 100 eligible Pump.fun launch mints while both feeds are connected, after warm-up and grace. Investigate mismatches, then aim for at least 95% of PumpPortal-observed eligible launches in PumpAPI. PumpPortal is not ground truth, and neither feed establishes coverage of every Solana token.
- **Resources:** while the app service and normal laptop workload are running, keep average probe CPU below 20% of one core and peak probe RSS below 300 MB, without swapping or sustained backlog. Confirm the process does not grow over 48 hours.
- **Volume and cost:** inspect bytes received and the projected 30-day volume in quiet and busy windows against the laptop's network plan. This is payload volume only; TLS and WebSocket overhead are additional. The PumpAPI stream is documented as free at this time, but verify provider terms before a continuous run. The 30-day projection assumes the sampled rate stays constant.
- **Price and liquidity cross-check:** compare later pool prices and real liquidity with an independent source before choosing a trading feed. The launch messages observed here did not provide compatible price and reserve fields for a reliable comparison. Virtual bonding-curve reserves are **not actual sellable liquidity**.

The current computer's short test cannot establish busy-period coverage, long-run cost, or suitability on the intended 4 GB laptop. Do not select a primary feed from a short sample alone.
