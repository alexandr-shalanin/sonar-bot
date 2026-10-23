# Sonar

Sonar has a FastAPI service, a Svelte/TypeScript portfolio page, and local SQLite storage. The service now saves PumpPortal token launches and migrations. Pool prices, Manual tracking, and trading are not implemented.

## Interface structure

`web/src/App.svelte` opens `web/src/screens/Portfolio.svelte`, the only implemented screen. Manual, Automatic, and Settings remain empty components pending their interface briefs. The portfolio fills the page with a centered pink CRT title, a bright pixel reef on the left, and the intro on the right. Local cat sprites react on hover; fourteen fish wander independently and swim away from a nearby pointer. The title has a cylindrical perspective, and the description reveals on scroll. Motion respects reduced-motion preferences. GitHub links to the supplied profile; Discord and “Let’s start” are disabled until destinations are supplied. Artwork prompts are recorded in [portfolio design notes](docs/portfolio-design.md).

For local interface work, run `npm run dev` from `web/` and open the printed local URL. `npm run build` checks Svelte/TypeScript and produces the static app served by FastAPI.

## Setup

Requires Python 3.11+ and Node.js 20.19+.

```sh
python3 -m venv .venv
.venv/bin/pip install -r service/requirements.txt
cd web && npm install && npm run build && cd ..
```

Set optional environment variables from `.env.example` in your shell. Sonar does not load `.env` files or require API keys in Step 1. Keep secrets in your environment or an ignored local file, never in `web/`.

## Run

```sh
cd service
../.venv/bin/python -m sonar
```

Open `http://127.0.0.1:8000/` for the portfolio, `/health` for `{"status":"ok"}`, and `/candidates` for the 100 most recent candidates. Each candidate includes its pool, last USD price, source/receipt times, price age, and `fresh`, `stale`, or `unavailable` price status. The provisional freshness cutoff is 30 seconds; a stale price is historical and should not be presented as current. Risk is `blocked` for observed dangerous permissions, a RugCheck rugged flag, or reported liquidity below the provisional $1,000 pool floor; `waiting` lists missing or stale evidence; `review` requires fresh price and reports, pool-matched liquidity, holder data, and a recent observed sell in that pool. `review` only means ready for human inspection, not safe or executable. The service can start before the web build; in that case only the API is available. SQLite is stored at `data/sonar.db` relative to the process working directory, or under `SONAR_DATA_DIR` if set. Logs are JSON lines on stderr. Bind to a trusted interface only; there is no app authentication yet.

Each candidate now includes `signals`: observed price changes over 1 and 5 minutes, plus observed buy/sell counts in roughly 1 and 5 minute windows. Price change is `null` unless a fresh current price and a sample within 15 seconds of the window baseline exist for the same pool. Trade counts are approximate because Shrine events are stored in one-minute buckets; zero means no trades were observed in those buckets, not that trading was absent. Shrine follows a pool for only 60 seconds, so 5-minute price change will usually be unavailable. These facts do not change the risk state or imply an entry signal.

On startup the service connects to PumpPortal's free launch stream and Shrine's free Pump.fun launch, pool-price and trade streams. Shrine follows up to 12 recent pools for 60 seconds and retries unavailable subscriptions briefly. The latest positive USD price includes source/receipt times; one price sample per 10 seconds is kept for one hour, trade counts for 24 hours, and candidates/lifecycle evidence for 48 hours. This retention applies before Track is built; tracked tokens will need an exemption. Prices become stale when updates stop; `/health` checks the database only, not feed freshness. The GoPlus/RugCheck gate checks only candidates with fresh prices, at most six candidates per hour. It stores selected facts from GoPlus and RugCheck's full report, not the full response. RugCheck may report no pool for a live Pump.fun bonding curve; that candidate stays `waiting`. Holder percentages do not establish independent ownership, and recent sells plus reported liquidity cannot guarantee an executable exit. Set `SONAR_PUMPPORTAL_ENABLED=0`, `SONAR_SHRINE_ENABLED=0`, or `SONAR_RISK_ENABLED=0` to disable a feed or the risk gate. If TLS certificate verification fails on this macOS installation, set `SSL_CERT_FILE=/etc/ssl/cert.pem`; keep verification enabled.

## Inspector backend

`POST /inspector` accepts `{"mint":"<Solana mint address>"}` and independently fetches DEX Screener pools/market data and GoPlus/RugCheck security reports. It works without candidate discovery. The response includes metadata, a selected pool and alternatives, market windows, holder concentration, named missing evidence and an explainable preliminary risk-screening score. Known hard blocks override points; missing critical data produces a null score. The score has not been validated as a growth probability. Source receipt times do not establish source freshness.

See [Inspector API and score rules](docs/inspector-api.md) for the contract, rubric, limits and error behavior. For local Inspector work, keep `SONAR_PUMPPORTAL_ENABLED=0 SONAR_SHRINE_ENABLED=0 SONAR_RISK_ENABLED=0`; the Inspector queries its sources on demand. The Inspector screen submits mint addresses to this API.

## Check

For the portfolio, run these from `web/` (the steering tests use Node 22.6 or newer):

```sh
npm run build
node --experimental-strip-types --test tests/fish.test.mjs
```

After building the web app, run:

```sh
cd service
../.venv/bin/python -m unittest discover -s tests -v
```

The smoke test starts the service twice and checks `/health`, the portfolio page, SQLite WAL mode and persistence, and that a test secret is absent from responses and logs.

## Step 2 feed probe

The read-only PumpAPI measurement tool remains separate from the app. See [feed probe instructions](docs/feed-probe.md) for a short run, optional PumpPortal launch comparison, and the 24–48 hour laptop trial.
