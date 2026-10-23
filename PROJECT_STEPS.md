# Sonar: how the app works

Sonar is a personal Solana memecoin observation and research assistant. It runs on a lightweight server, discovers new tokens, checks basic risks, and helps the user observe candidates. The current product is **read-only Manual mode**: there is no buy button, no automatic trade, and no simulated/virtual purchase. The system is planned, not yet implemented or proven profitable.

**Current focus (2026-10-23): Inspector by mint address.** Automatic discovery is paused in the local run and Candidates uses UI demo cards. `POST /inspector` now requests DEX Screener, GoPlus and RugCheck independently of discovery, returns pool-specific market and security facts, and calculates an explicit provisional risk-screening score with hard blocks and missing-data states. Receipt time does not certify source freshness, and this score has no demonstrated predictive accuracy. See [API contract and rubric](docs/inspector-api.md). The Inspector search UI still needs connection to the API; the earlier discovery and Track sections below remain background plans.

## 1. Continuous discovery

1. Receive new token, pool, migration and trade events. Track live prices and liquidity for relevant pools. Record when each event was observed.
2. Remove duplicates and weak candidates early. Keep only a bounded number of active tokens to limit work on the planned 4 GB laptop.
3. Follow surviving tokens as they develop. Measure activity in short windows (for example 1–5 minutes) so future analysis can distinguish accelerating attention from a move that has already happened. Window sizes and thresholds are hypotheses, not trading rules.

**Current data:** PumpPortal's free Pump.fun launch/migration stream and Shrine's free pool-price/trade stream are connected to the backend. Their combined coverage and Shrine pool readiness still need a larger unbiased check. PumpAPI.io had repeated silent stalls and high bandwidth. REST providers are delayed cross-checks, not primary live feeds. See the measured results below.

## 2. Judge: risk and setup evidence

1. **Hard block:** separately flag conditions that make a token unsuitable for consideration, such as dangerous mint/freeze or Token-2022 permissions, missing critical evidence, inadequate liquidity, or no plausible exit. A block is not a score penalty; other signals cannot override it. No provider can certify a token as safe.
2. **Setup evidence:** measure pool-specific price and liquidity changes, buys and sells, distinct buyer growth, short-window acceleration, and pullbacks while activity continues. Check whether activity could be wash trading. Candles provide context; a named pattern alone is not a signal.
3. **Wallet clusters:** coordinated early buys may be a useful research signal, but wallet linkage is uncertain and the claimed predictive edge is unvalidated. Do not equate holder count with independent owners, label wallets as “smart money,” or copy trades based on this hypothesis. First establish whether suitable real-time wallet data is available and test signals without execution.
4. **Social evidence:** defer it. If added later, use it as contextual evidence or a possible artificial/dead-narrative filter, never as an entry trigger or a way around a hard block.
5. **Decision:** keep the hard-block result separate from setup quality. Any candidate ranking is an ordering of observed evidence, not a probability of profit or expected return. Expected value cannot be claimed until entry/exit prices, costs, and outcomes have been measured. DeepSeek is optional summarization and cannot override hard rules.

**Proposed data:** GoPlus for token details; RugCheck as a second risk check; limited Helius standard WebSocket use for selected live wallet activity after a trader list is validated. Avoid frequent Helius Wallet History polling because of its credit cost. Telegram's Bot API works for channels the bot can access. X access is a later option if its read costs fit the budget. Exact rules, sources and trusted wallets are not yet selected or validated.

## 3. Manual mode

Sonar discovers candidates and presents observed evidence, uncertainty, hard blocks, and setup quality. It may show token age, current pool price and its age, pool liquidity when available, short-window market activity, and the main risks. Avoid implying certainty or profit probability. No suggested spend is needed in the current product.

The user can press **Track** on a candidate. Sonar saves the current observed reference price and timestamp, then shows the token in a persistent **Tracked** view with its reference price, current comparable price, absolute price change, percentage change, and data age. Percentage change is `(current price / tracked reference price - 1) × 100`. Pressing Track again for an already tracked token must not silently reset its baseline. This is price observation only: it is not a purchase, simulated position, P&L, or executable quote. Use the same token pool and price basis for comparison; if the pool/source changes or the current quote is stale or unavailable, show that limitation instead of presenting a misleading change. Tracking must survive app/service restarts. The user can stop tracking a token.

There is no buy/order button, wallet connection, automatic trade, or virtual purchase in Manual mode. The user may decide independently what to do elsewhere. Alerts can be considered after the live candidate and tracking flow works.

## 4. Trading (explicitly out of current scope)

No Automatic mode, order controller, wallet integration, buy/sell controls, simulated purchase, paper trading, or execution interface is being built. Track is only a saved reference price and a view of subsequent market prices. Any future change to this boundary requires a separate decision. The position-sizing, stop-loss, take-profit, cluster-following, and execution figures in the shared research summary are unverified hypotheses, not product rules.

## 5. Records, testing and operation

Sonar records candidate evidence and timestamps, hard blocks, and tracked-token reference prices so observations can be reviewed after a restart. It also records rejected candidates so coverage and missed candidates can be examined. It does not keep orders, fills, positions, or simulated P&L in the current product.

The immediate validation goal is to compare observed candidate signals with subsequent market prices, including whether an observed move had already occurred and what data was available at the time. Tracking records a reference price; it does not simulate fills, fees, slippage, or a portfolio. Any future execution study would need separate rules for position sizing, exits, fees, slippage, and failed exits. Specific claims about trader win rates, wallet clusters, and strategy outcomes remain unverified hypotheses until their sources and methods are reviewed. The initial data API budget is ideally $5–10/month, with about $15–20/month as a starting maximum. DeepSeek access already exists. The planned host is an old laptop with 4 GB RAM.

## 6. Proposed technology stack

| Part | Choice | Purpose |
| --- | --- | --- |
| Bot and app API | Python + FastAPI | One lightweight service for feed ingestion, candidate evidence, tracking and app data. Use asynchronous I/O for live feeds and API calls. |
| App | Svelte + TypeScript, built as a static web app | Read-only candidate and tracked-token views accessible from phone or desktop. |
| Interface design | Project-owned design tokens and reusable Svelte components | Keep candidate evidence and tracked-price changes clear, readable, and explicit about data freshness. |
| Live app updates | Server-sent events (SSE) | Stream candidate, tracked-price and provider-status updates to the open app. |
| Storage | SQLite with write-ahead logging (WAL) | Persist candidates, tracking reference prices, settings, and enough event history to explain observations. Keep recent market data bounded; do not save every price tick. |
| Alerts | Telegram bot | Candidate alerts may be added after the read-only candidate and tracking flow works. |
| AI | Existing DeepSeek API | Optional concise evidence summaries; it cannot override hard blocks or turn a ranking into a profit claim. |
| Host | Linux + systemd on the 4 GB laptop | Run Sonar continuously and restart it after a crash or reboot. |

**Data-source status:** PumpPortal is connected as the provisional discovery trigger. Shrine is connected for up to 12 recent Pump.fun pools at a time; six Shrine-discovered pools subscribed immediately in a parallel probe, but availability across all new pools is unproven. Dexploit streamed reliably in one six-minute run, but its acknowledged free WebSocket venue filter did not restrict events, so it is unsuitable as the default lightweight feed until filtering is resolved. DEX Screener, GeckoTerminal and DexPaprika have been tested as REST cross-checks. Jupiter quote-only buy/sell checks have also been run. GoPlus and RugCheck returned token reports in a small read-only sample. Helius standard and parsed wallet streams both delivered events in a short, capped test; neither has a proven 24/7 free-tier cost envelope. Social sources remain untested. Details and limits are below.

**Current scope:** discovery, risk evidence, read-only candidate review, and user-started price tracking. Do not build execution quotes, wallet/key handling, buy/sell controls, virtual trades, or Automatic mode as part of this scope. Avoid adding a separate database server or message broker unless measured load requires one.

### Data providers: research and next tests (2026-10-21)

The provider claims below come from linked documentation; measured results are identified separately. A displayed last-trade price is **not** an executable buy/sell quote; launch bonding-curve reserves are **not** verified exit liquidity. Free tiers, coverage and freshness can change.

| Need | Current use / best free candidate | Status and limit |
| --- | --- | --- |
| Broad launch/trade stream tried first | [PumpAPI.io](https://pumpapi.io/stream) | **Tested, not selected for the 4 GB host.** The first 121-second run received 6,988 events in 10.84 MB, with two disconnects. Two later runs of about 32.5 minutes received 569 MB and 1.18 GB respectively; the latter recorded 29 disconnects and 22 event gaps over five seconds. Network conditions varied, so these are not proof of a provider-side fault. A broad feed is expensive in bandwidth and still does not prove complete new-token coverage. |
| Pump.fun launches and migrations | [PumpPortal](https://pumpportal.fun/data-api/real-time/) free stream | **Connected, provisional.** A 360-second probe received 125 creations and 2 migrations in 75 KB, with one connection and no errors. A separate 15-second backend check stored five launches. This does not establish long-run reliability or coverage. The free subscription did not provide ongoing trades, price or liquidity. Other launchpads and complete coverage remain unproven. |
| Live pool-specific trades and last price | [Shrine Data API](https://shrine.trade/pump/data-api/overview/) per-pool price/trade subscriptions | **Promising, unresolved availability.** Free keyless Socket.IO streams delivered price and trade events with all checked core fields present and low resource use. In two retry probes only 151/261 and 172/267 price subscriptions were ready immediately; 5 and 2 more became ready after retries. The 12-pool tracking cap left many launches unmeasured, so test a fixed cohort before relying on this source. Documented maximum: 50 subscriptions per connection. |
| Independent live trade stream | [Dexploit Starter](https://www.dexploit.dev/pricing) | **Measured, filtering unresolved.** A six-minute run held one connection and received 16,165 swaps with no errors. Two acknowledged `dexes` filters still delivered unrelated venues, so the free stream is too broad for the planned lightweight ingest until this is resolved. An earlier attempt had 17 HTTP 503 responses before connecting. |
| Price, pool liquidity, volume and pair age cross-check | [DEX Screener API](https://docs.dexscreener.com/api/reference) | **Briefly tested.** In a same-mint six-token run, prices appeared for 6/6 at observed p50 81.52 s, liquidity for 0/6. Earlier runs found prices for 2/6 and 4/6. Keep as a delayed cross-check, not the seconds-scale trade feed. |
| Independent price/liquidity cross-check | [GeckoTerminal public API](https://apiguide.geckoterminal.com/) | **Rate-limited in the same-mint run.** Price/liquidity appeared for 1/6, with 54 HTTP 429 responses in 86 requests at this test cadence. Earlier slower runs found 2/6 and 4/6 with three 429s each. Use only with a measured lower polling rate. |
| Another independent price/liquidity cross-check | [DexPaprika REST](https://dexpaprika.com/api/pricing) | **Mixed short runs.** A first six-token run found price/liquidity for 2/6 without 429s; a same-mint run found token records for 6/6 but price/liquidity for 0/6, with four 429s in 86 requests. Free REST may lag up to 60 seconds; SSE updates spend monthly credits. |
| Indicative buy/sell amounts | [Jupiter Swap API](https://developers.jup.ag/docs/api-reference/swap/order) quote-only route | **Briefly tested, without orders.** Both runs returned buy quotes for 12/12 tokens, but sell quotes only for 9/12 and 11/12 tokens. Roundtrip quote loss varied widely. A quote does not prove a transaction will execute or what its final proceeds will be. Requote selected candidates and open positions. |
| Token security | [GoPlus Solana Token Security](https://docs.gopluslabs.io/reference/solanatokensecurityusingget), [RugCheck API](https://api.rugcheck.xyz/swagger/doc.json) | **Basic access measured.** Both returned HTTP 200 and nonempty reports for 6/6 fresh tokens without keys, about 20 s after launch. Validate the specific fields and verdicts against on-chain facts and known examples; neither certifies safety. |
| Selected wallet activity and occasional history | [Helius Free](https://www.helius.dev/pricing) standard WSS; Wallet History only when justified | **Access measured, economics unresolved.** Three recently active public trader wallets produced 3,136 standard events in 10.00 MB and 1,366 parsed events in 10.00 MB, with one connection per stream, no connection errors and 29 MB peak RSS. Both streams hit a deliberate 10 MB cap after about four minutes, so this was not a full ten-minute run. These wallets were selected for activity, not trading quality. At the documented rates, this sample cost roughly 201 standard-stream credits versus 1,367 parsed-stream credits, subject to billing confirmation. Free plan lists 1M credits/month; a continuous stream at this sample's rate would exceed it. Standard logs need parsing and wallet-specific filtering; use a small validated list, count actual credits and events, and pause on budget thresholds. Wallet History is documented at 100 credits/request, unsuitable for frequent polling. |
| Social signals | [Telegram Bot API](https://core.telegram.org/bots/api); [X API](https://docs.x.com/x-api/getting-started/pricing) later | **Unselected.** Telegram access depends on channels the bot can reach; X read access and cost still need review. Social evidence cannot override risk checks. |

**Other options reviewed, not first-choice free feeds:** [PumpPortal token/account trades](https://pumpportal.fun/fees) (metered, requires a key); [Birdeye](https://docs.birdeye.so/docs/pricing) (free REST, streaming on paid tiers); [Vybe](https://docs.vybenetwork.com/docs/plans-rate-limits) (free REST, paid WebSocket); [Solana Tracker](https://www.solanatracker.io/pumpfun-api) (small free REST allowance; ongoing Datastream pricing needs checking); [Shinobi](https://shinobi.trade/) (free REST only, paid WebSocket); [SolanaStreaming](https://solanastreaming.com/docs/websocket-api/pricing) (5,000 free WebSocket messages); [AFK Data](https://data.afk.fun/docs?s=rest) (free launch/migration, metered filtered price/trade streams); [Bitquery](https://docs.bitquery.io/docs/blockchain/Solana/) (trial access rather than confirmed permanent free streaming). [Moralis](https://developers.moralis.com/chains/solana/) and direct Solana/Raydium/Meteora RPC parsing are further fallbacks; their coverage/cost or engineering burden has not been evaluated for this laptop.

**Measured short runs:** A 360-second Shrine vs PumpPortal probe saw 302 vs 241 Pump.fun launches, 232 shared; Shrine arrived 206 ms earlier at the median for shared mints. Shrine delivered 3,317 price updates and 3,223 trades in 2.31 MB, with one connection, ~0.54% of one CPU core and 41.5 MB peak process RAM. Source-timestamp ages were approximately p50/p95 0.58/1.07 s for prices and 0.77/1.29 s for trades; these are not precise network latency. There were 278 `not_found` errors across 604 immediate price/trade subscription attempts (about 46% of attempts), with no retry. Launch-only differences include start/end boundary effects and do not prove coverage. A 300-second REST probe sampled 30 new tokens with 27 requests to each provider; DEX Screener first price was observed at p50 66 s in 10-second batch polls. GeckoTerminal produced two 429s. Its one-token-per-10-second sampling cannot establish true first-price delay. The probe did not retain per-provider unique hit counts, so neither REST source's token coverage is established. Full local reports are in ignored `service/data/probes/` files named `shrine-free-6m-20261021.json` and `rest-freshness-5m-20261021.json`.

**Follow-up short runs:** Two seven-minute Shrine retry probes had 151/261 and 172/267 immediately ready price subscriptions; only 5 and 2 additional subscriptions became ready after 1/2/5/10-second retries. Their `not_found` counts (359 and 303 per subscription type) include **all** attempts, not only first attempts; dividing those by total attempts does not give an initial failure rate. Twenty-five and 27 price subscriptions exhausted the retry budget while still tracked. Because only 12 pools were tracked and older pools were evicted, these counts do not establish what fraction of all launched tokens eventually become available. In two six-token REST comparisons, DEX Screener found prices for 2 and 4 tokens, GeckoTerminal for 2 and 4 tokens, and DEX Screener returned liquidity for none; GeckoTerminal returned 429 three times in each run. A separate six-token DexPaprika run found price/liquidity for 2 tokens with no errors. These runs used different tokens and times, and each provider polled one token per 10 seconds. In two 0.05-SOL Jupiter quote-only runs, buys succeeded 36/36 each; sells succeeded 33/36 and 25/36. Two-way quotes existed for 11/12 and 9/12 tokens. Indicative roundtrip loss was p50 2.98% and 8.09%, p95 8.09% and 13.01%, respectively. This is variable quote cost, not measured fill or guaranteed exit. Full local reports are ignored under `service/data/probes/`.

**Parallel read-only run (2026-10-21, six minutes):** On six Shrine-discovered Pump.fun pools, all six price and trade subscriptions succeeded on the first attempt, with first acknowledgements in 0–0.89 s. They produced 1,002 price updates and 1,000 trades, heavily concentrated in one pool. Shrine reported 182 launches and PumpPortal 139, with 117 shared; different event definitions and boundary effects prevent a coverage conclusion. The same six mints were polled across REST providers: DEX Screener found prices for 6/6 after observed p50 81.52 s but liquidity for 0/6; GeckoTerminal found price/liquidity for 1/6 with 54 HTTP 429 responses in 86 requests; DexPaprika found token records for 6/6 but price/liquidity for 0/6, with four 429s in 86 requests. Polling cadence limits first-price timing precision. GoPlus and RugCheck returned HTTP 200 and nonempty token reports for all six about 20 s after launch; report accuracy and safety verdicts were not validated. The combined probe peaked at 42 MB RSS. In parallel, Dexploit held one connection for six minutes with no errors and received 16,165 swaps and 245 pool events (15.8 MB, 38.8 MB peak RSS). Two 12-second follow-ups found non-Pump.fun swaps despite acknowledged `dexes` filters using both `pumpfun` and `pump_fun`; the alternate documented `/ws/json` endpoint returned HTTP 404. These results do not prove venue-filter support on the free stream. Local reports are ignored under `service/data/probes/`.

**Helius wallet-stream run (2026-10-21):** A local read-only probe sampled three recently active public trader wallets from Dexploit and subscribed to Helius standard `logsSubscribe` and Parsed Streams. All three standard subscriptions and the one parsed subscription were accepted. Both streams connected once without reported errors; first events arrived roughly 34 seconds after the test started, including wallet sampling time. Standard delivered 3,136 events in 10,000,825 bytes; parsed delivered 1,366 events in 10,003,950 bytes. Both hit a deliberate 10 MB cap, ending the test after 241.5 seconds rather than the planned ten minutes. Peak process RSS was 29 MB. Using the published rates of two credits per 0.1 MB for standard WSS traffic, one credit per parsed event and one credit per connection gives approximate costs of 201 and 1,367 credits respectively; the actual billed usage was not checked. At this unusually active sample's constant rate, either stream would exceed 1M credits/month. The test confirms access and event delivery, but does not measure complete wallet-transaction coverage, event latency, a vetted trader list, quiet-period usage or long-run cost. Report: ignored local `service/data/probes/helius-wallet-10m.json`.

**Combined backend run (2026-10-22, 20 minutes):** PumpPortal and Shrine together recorded 333 distinct candidates: 211 seen by both, 25 only by PumpPortal and 97 only by Shrine. Shrine prices reached 136 candidates, and 4,552 trades were counted; five prices were still fresh at the end under the current 60-second pool-tracking window. PumpPortal had three logged timeouts and reconnected each time; Shrine had no logged disconnect. Peak process RSS was 54.6 MB. Provider event definitions and short observation boundaries still limit coverage conclusions. The ignored local report is `service/data/probes/sonar-feed-20m-20261022.json`.

**Next test order:** (1) verify GoPlus/RugCheck fields against on-chain facts and known unsafe/ambiguous examples; (2) only if real-time cluster analysis remains a priority, validate wallet coverage and measure Helius usage before integrating it; (3) run the selected feeds on the intended 4 GB laptop during quiet and busy periods. There are no planned fill or execution tests in the current read-only scope. Revisit Dexploit only if server-side filtering can be made to work on the free plan.

**Still missing:** a reliable Shrine subscription strategy or alternative continuous feed, independent new-token coverage across launchpads, pool-specific liquidity for live Pump.fun bonding curves, any evidence for wallet-cluster hypotheses, and a proven 24/7 free-tier cost envelope. Real executable quotes, wallets, and social feeds are outside current scope.

Step 1, the Step 2 feed probe, and the backend implementation of Step 4 are complete: PumpPortal/Shrine ingestion, bounded candidate data, price freshness states, short-window samples and retention. The Step 5 conservative backend gate is implemented and checked against live provider responses and on-chain authority examples; it leaves unsupported pool liquidity and exit evidence in `waiting`. The candidate Judge and tracking are not integrated. Final feed validation, the 4 GB laptop trial and observation-based strategy validation are pending.

## 7. Step-by-step build and test guide

Build in this order. Finish each step's check before relying on the next one. The targets for feed freshness, resource use, API spending, and tracking data quality must be written down before judging results; they are not yet known.

**Current milestone:** Step 1 foundation, Step 2 exploratory probes, Step 4 backend ingestion and the conservative Step 5 gate are done. Step 3 interface design and screen work is in progress; current screens are not a live product. **Next backend work is Step 6 measurable signals**; no UI work is needed yet. Use the following seven-stage roadmap as the current agreed plan:

1. Finish the minimal Manual/Track behavior and data contract.
2. Connect PumpPortal and Shrine to the backend with deduplication, bounded retries/subscriptions, and stale states.
3. Build a normalized, persistent candidate stream tied to actual pools and event timestamps.
4. Add GoPlus/RugCheck hard risk checks, with missing or stale critical data kept distinct from safe results.
5. Calculate observable short-window market signals; treat wallet-cluster claims as unvalidated and defer Helius.
6. Build read-only Manual and persistent Track views; Track stores a reference price and displays later market-price changes, never a simulated position.
7. Validate failure handling, saved tracking, feed coverage, and operation on the target laptop.

Trading, wallet integration, buy controls, virtual purchases, and Automatic mode are outside this plan. Evaluate candidate evidence against later observed prices without claiming fills or profit. API test success alone does not advance implementation steps.

The interface is a major product track. Design the read-only candidate and Tracked views, then check them with realistic data and failure states. Keep data age, uncertainty, and risk visible. Interface work can progress while the longer feed trial is pending.

### Step 1 — Set up the small foundation

**Add/build:** Create the Python/FastAPI service, Svelte/TypeScript app, SQLite database, configuration, structured logs and health status. Keep API keys out of code, the browser and Git. Start with one service and bounded memory use.

**Test:** Start and restart it on the 4 GB laptop. Check memory, CPU, database persistence, missing configuration, and that no secret appears in logs or app responses.

### Step 2 — Measure discovery and price feeds

**Add/build:** Exploratory probes for PumpAPI.io, PumpPortal, Shrine, Dexploit, DEX Screener, GeckoTerminal, DexPaprika, Jupiter quotes, GoPlus, RugCheck and Helius wallet streams are complete. Their reports live in ignored local `service/data/probes/`. PumpPortal launches/migrations, bounded Shrine prices/trades, and a capped GoPlus/RugCheck pilot are integrated; the other providers remain probes. Capture pool changes, trades, source timestamps, disconnects and API usage in continuing feed validation.

**Test:** The short runs identify PumpPortal + Shrine as provisional starters, with the limitations above. Before treating them as reliable, observe quiet and busy periods, compare an unbiased token cohort, and measure freshness, reconnect behavior, price differences, RAM/CPU and monthly cost. Keep a fallback path if coverage or stability fails.

### Step 3 — Design the interface and interaction model

**Add/build:** Design the read-only candidate and Tracked views for phone and desktop. Define the Track interaction, captured reference price/time/source/pool, current price comparison, percent change, stale/unavailable states, and stop-tracking behavior. Specify candidate loading, empty, provider-error, stale, and insufficient-evidence states. Make clear that Track observes market price and is not a purchase or simulated position. Do not design a buy action or Automatic trading flow for this milestone.

**Test:** Walk through candidate review and tracking on phone and desktop. Check that reference/current prices, percentage change, freshness, major risks, and uncertainty are understandable without reading logs. Review touch targets, keyboard use, contrast, readable text, and reduced-motion behavior. Record design decisions before implementation.

### Step 4 — Build continuous discovery

**Backend progress:**

- [x] Define the normalized event fields and timestamp units.
- [x] Create SQLite tables for candidates and selected events; confirm records survive restart.
- [x] Connect PumpPortal launch/migration events to the backend, with validation, deduplication, and reconnects.
- [x] Connect Shrine prices/trades for selected pools.
- [x] Expose a bounded read-only candidate list with explicit price freshness states.
- [x] Add deduplication, bounded subscriptions/retries, stale states, and retention rules.

**Normalized event contract:** One backend event has `mint` (token address), `pool` (venue label), optional `pool_id` (actual pool address), `source` (provider), `kind` (`launch`, `migrate`, `price`, or `trade`), optional `source_ms` (provider's event time), and required `received_ms` (Sonar receipt time). Times are Unix milliseconds. Price events additionally carry a positive `price` and explicit `price_unit`; a price without a known unit is unusable. A launch may precede identification of its pool. Price and trade events must identify the pool they describe. Provider adapters validate and normalize these fields before storage. Candidate identity is the mint; its selected pool is stored separately. The database keeps candidate state and selected lifecycle events, not every price tick or trade.

**Add/build:** Connect provisional PumpPortal launches/migrations and Shrine pool-price/trade subscriptions to Sonar through small replaceable provider adapters. Deduplicate events, track each candidate's actual pool and age, retry unavailable Shrine pools within a bounded window, reject malformed input, cap active candidates/subscriptions, and mark stale data. Preserve event/source/receipt timestamps and enough trade/price history to calculate short-window activity and investigate coverage without saving every tick. Keep provider credentials server-side and optional; do not require Helius or social sources for this step.

**Test:** Replay duplicates, out-of-order events, disconnects, failed subscriptions and provider outages. Verify new tokens are found once, prices show their age, and stale data cannot produce a fresh recommendation. Compare a bounded cohort of PumpPortal-only and Shrine-discovered tokens to expose missed pools without claiming complete coverage.

### Step 5 — Add the safety gate

**Backend complete as a conservative gate (2026-10-22):** At most six recently launched candidates with fresh prices are checked per hour. GoPlus permissions and RugCheck's full report provide mint/freeze, transfer restrictions, holder/creator concentration, LP details for an exact matching pool, and provider risk flags. The API exposes `blocked`, `waiting` with named missing evidence, or `review` for human inspection. Hard blocks are active mint/freeze authority, non-transferable/default-frozen/transfer-hook/upgradeable transfer-fee rules, a 100% transfer fee, RugCheck's `rugged` flag, and a reported matching pool below a **provisional $1,000 liquidity floor**. An unknown pool, missing holders or recent sells, stale price or reports, or provider error stays `waiting`; no score or other signal can override a block. A recent sell is only evidence that a sell was observed, not a quote or guarantee of an exit. Concentration is shown for review, not used as a hard block because pool holdings and wallet linkage are unresolved.

**Validation:** Public Solana RPC `getAccountInfo` agreed with GoPlus and RugCheck on mint/freeze authorities for USDC (both present) and a newly launched Pump token (both absent). A live full RugCheck report for the new token contained holder data but no market entry; the gate correctly remained `waiting` for pool liquidity and sells. A mature Pump token's full report exposed per-market `pubkey` and `lp.baseUSD`/`quoteUSD`; the implementation matches the candidate pool ID and does not substitute token-wide liquidity. Synthetic tests cover dangerous permissions, `rugged`, low liquidity, stale/missing data, provider failure and pool mismatch. The earlier 65-second run saved three `ok` reports from each provider alongside 26 candidates and six prices. This validates field mapping and conservative behavior, not detection accuracy, market coverage, or an executable exit.

**Add/build:** Call GoPlus and RugCheck only for surviving candidates. Check token permissions and transfer rules, holder/creator concentration, liquidity and basic exit feasibility. Define hard rejects and a wait state when critical evidence is missing.

**Test:** Use known unsafe and ambiguous token examples, missing fields and provider failures. Confirm that wallet activity, social hype and AI cannot override a hard rejection.

### Step 6 — Build the Judge's measurable signals

**Minimal backend slice (2026-10-22):** `/candidates` now reports pool-specific 1-minute and 5-minute observed price changes when a fresh price and a baseline sample near the window boundary exist. It also reports observed buys and sells from existing one-minute buckets; these counts are approximate and may include part of an adjacent minute. Missing baseline or stale price yields `null`, and changing pools cannot reuse the old pool's history. The risk gate remains independent. Shrine currently follows a pool for 60 seconds, so a 5-minute price baseline will normally be missing. Distinct buyers, acceleration, pullbacks, likely costs and any ranking remain for later validation; this minimal slice is enough to start wiring the read-only UI.

**Add/build:** Separate binary hard blocks from setup evidence. Compute pool-specific price movement, buys/sells, distinct buyers and acceleration in short windows, pullbacks, and likely trading costs when measurable. Treat wallet clusters as an unvalidated research hypothesis; add wallet feeds only after a real-time coverage and cost study. Social signals stay deferred. Do not label a score as expected return or probability of profit.

**Test:** Replay recorded candidates, including blocked and low-evidence cases. Check hard-block consistency, delayed signals, short-window metric behavior, and possible wash trading. Compare later observed prices using only information available at each decision time; do not treat tracked price changes as fills, P&L, or proof of a profitable strategy.

### Step 7 — Add DeepSeek carefully

**Add/build:** Send compact evidence for selected promising or ambiguous candidates. Require a short explanation and use code to validate the response. Keep all hard safety and budget limits in code.

**Test:** Simulate slow calls, API errors, invalid responses and contradictory advice. Sonar must continue with a clear non-AI result; AI cannot override a hard block or initiate a purchase. Track AI call cost and latency.

### Step 8 — Build Manual mode and its interface

**Add/build:** Implement responsive read-only candidate and Tracked views. Candidates show available market evidence, data age, risks, hard-block status, and concise explanation without implying certainty. Track saves a baseline price and time; Tracked shows that baseline, current comparable price, absolute and percentage changes, and freshness, and persists across restarts. Allow stopping tracking. No buy/order action, wallet connection, suggested spend, or virtual purchase. Add live updates; consider alerts only after this flow works.

**Test:** Check phone and desktop use, empty/loading/error/stale states, filters, Track baseline capture, percentage calculation, persistence after restart, stop-tracking, and duplicate Track behavior. Verify stale or changed-pool data is clearly marked and cannot silently produce a misleading comparison. Confirm there is no purchase or order path.

### Step 9 — Refine and verify the Manual interface

**Add/build:** Use realistic recorded candidates and live updates to refine information hierarchy, wording, visual consistency, motion, and Track behavior. Make stale or missing evidence visibly different from fresh evidence. Keep updates readable when token activity is high and avoid unnecessary browser work on the 4 GB host.

**Test:** Review actual renders on small and large screens, with slow connections and long token names. Test loading, empty, error, stale, and fast-changing states; keyboard navigation, screen reader labels, contrast, reduced motion, and clarity of risk and price-change wording. Fix usability problems before treating Manual mode as complete.

### Step 10 — Evaluate Manual recommendations live

**Add/build:** Run Sonar in observation mode and log candidates, hard blocks, evidence, tracking start prices/times, and later observed prices. Track provider and AI spending, data gaps, and resource use. This is market observation, not paper trading: no hypothetical fills, portfolio, or P&L.

**Test:** Compare candidate evidence with subsequent observed market prices over new, unseen periods. Inspect delayed signals, bad calls, missed candidates, and whether apparent moves were already underway. This does not establish executable returns because there are no simulated or real fills. Adjust rules only from recorded evidence, then repeat the forward check.

### Step 11 — Deferred: any execution research (not current scope)

No execution, wallet, buy/sell quote, or trading safety implementation is planned. Revisit only after a separate product decision; the shared summary's sizing and exit figures are not adopted parameters.

### Step 12 — Deferred: simulated or paper trading (not current scope)

Track is deliberately simpler: it records market-price movement from a user-selected starting point and does not simulate an entry, exit, or portfolio result.

### Step 13 — Deferred: any trading interface (not current scope)

Do not add a trading interface, buy/order control, or wallet connection to the current read-only app.

### Step 14 — Operational reliability for the read-only service

**Add/build:** Run the read-only Sonar service under systemd on the laptop, restrict remote access, back up the database and configuration safely, and monitor feed freshness, process health, disk space, and API costs. Document how to stop the service and recover after an outage.

**Test:** Reboot the laptop; interrupt the network and each provider; simulate low disk space; restore a backup. Verify Sonar resumes with tracked baselines intact and makes stale/uncertain data visible.

### Step 15 — Deferred: live trading (not current scope)

No live trading is planned or enabled by this roadmap.

Sources: [PumpAPI](https://pumpapi.io/stream), [PumpPortal](https://pumpportal.fun/data-api/real-time/), [GoPlus](https://docs.gopluslabs.io/reference/solanatokensecurityusingget), [RugCheck](https://api.rugcheck.xyz/swagger/doc.json), [Helius](https://www.helius.dev/docs/api-reference/wallet-api/history), [Telegram](https://core.telegram.org/bots/api), [X pricing](https://docs.x.com/x-api/getting-started/pricing).
