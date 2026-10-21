# Sonar: how the app works

Sonar is a personal Solana memecoin assistant. It runs on a lightweight server, continuously discovers new tokens, checks risk, and identifies possible trades. The user switches between **Manual** and **Automatic** modes. Both modes use the same market data and Judge; only Automatic places new trades. The system is planned, not yet implemented or proven profitable.

## 1. Continuous discovery

1. Receive new token, pool, migration and trade events. Track live prices and liquidity for relevant pools. Record when each event was observed.
2. Remove duplicates and weak candidates early. Keep only a bounded number of active tokens to limit work on the planned 4 GB laptop.
3. Follow surviving tokens as they develop. A minimum age of about one minute is a working idea, not a final trading rule.

**Proposed data:** trial the free PumpAPI.io stream first; try PumpPortal's selective stream if the full feed is too heavy. GeckoTerminal and DEX Screener may provide extra context, but are not the primary live price feed. Freshness, coverage, resource use and cost still need live measurement.

## 2. Judge: risk and opportunity

1. **Safety gate:** inspect mint/freeze permissions, Token-2022 transfer rules, creator and holder concentration, liquidity, suspicious activity, and whether a realistic exit is possible. Missing or stale critical data means wait or reject. No check can certify a token as safe.
2. **Market check:** measure price and liquidity changes, buys versus sells, distinct traders, and possible wash trading in the pool Sonar could actually use. Candles provide context; named candle patterns alone never trigger a buy.
3. **Extra evidence:** consider purchases by tracked traders only after measuring their history and achievable follow prices; related wallets count as one signal. Consider X/Telegram posts only with source and timing; copied or late posts count less. These signals cannot override a safety rejection.
4. **Decision:** fixed rules check freshness, risk, liquidity and likely trading costs. DeepSeek reviews a compact summary for promising or ambiguous tokens. The Judge returns **avoid, watch, or recommended**, its reasons, and a **1–100 ranking score**. The score ranks candidates; it is not a chance of profit or a guarantee of safety.

**Proposed data:** GoPlus for token details; RugCheck as a second risk check; limited Helius use for wallet history and selected live wallet activity. Telegram's Bot API works for channels the bot can access. X access is a later option if its read costs fit the budget. Exact rules, sources and trusted wallets are not yet selected or validated.

## 3. Manual mode

Sonar discovers, checks and ranks tokens. It **never opens trades on the user's behalf in Manual mode**. The user sees a ranked candidate screen with filters. Each candidate shows its score and decision, token age, current pool price and data age, liquidity, main risks, a short AI explanation, and a suggested spend with a **maximum based on the user's set budget and the pool's depth**. If there is too little evidence or no usable exit, Sonar gives no spend suggestion.

Sonar notifies the user when a high-ranking candidate becomes newly active or materially changes. The user decides whether to trade elsewhere. There is no order button or trade execution for new positions in this mode.

## 4. Automatic mode

The Judge's recommendations go to the Action Controller, which can buy and sell without routine approval. The main screen is a mini game: its agents represent actual discovery, checking, trading and risk events. A mode switch and emergency pause remain accessible. Sonar alerts the user about trades, failures and urgent risks.

Before buying, the controller rechecks the Judge's evidence, wallet balance, pool liquidity and a fresh executable quote. It estimates the sell outcome for the intended size, including fees, slippage and price impact. It skips entries that moved outside the acceptable range or cannot reasonably be exited.

Position size is capped by the proposed amount, available capital, per-trade risk, total exposure, daily loss limit and pool depth. The AI may suggest entry, size and exits; code enforces the limits and places orders. It records an order intent, sends at most one pending order per token, confirms the transaction and checks the actual balance before marking a position open. An uncertain outcome is reconciled before any retry.

After entry, the controller watches the **executable sell value**, not just the displayed token price. It attempts an exit on the stop, profit target, maximum holding time, invalidated trade reason, critical new risk, or liquidity withdrawal. It verifies the actual sale and any remaining balance. If an exit fails, it keeps the position marked at risk, retries safely and alerts the user. A stop loss cannot guarantee its target price or a successful sale.

The controller stops **new entries** if data is stale, providers fail, balances disagree, limits are reached, or the user pauses it. It continues managing existing positions. On switching from Automatic to Manual, new automatic buys stop immediately; positions already opened in Automatic follow their existing exit plans until closed. Manual analysis then continues without opening trades.

## 5. Records, testing and operation

Sonar records each candidate, evidence timestamp, Judge decision, quote, order, fill, fee and position outcome. It also records rejected candidates so results can be checked for missed opportunities and false signals. Durable records let it recover open positions and uncertain orders after a restart or network outage.

Before live automation, run the same logic in paper trading with realistic fees, slippage, delays and failed exits; then compare small live fills with the simulation. Exact thresholds, quote and execution providers, wallet setup and emergency procedures are still to be chosen. The initial data API budget is ideally $5–10/month, with about $15–20/month as a starting maximum. DeepSeek access already exists. The planned host is an old laptop with 4 GB RAM.

## 6. Proposed technology stack

| Part | Choice | Purpose |
| --- | --- | --- |
| Bot and app API | Python + FastAPI | One lightweight service for feed ingestion, Judge, Action Controller and app data. Use asynchronous I/O for live feeds and API calls. |
| App | Svelte + TypeScript, built as a static web app | One app accessible from phone or desktop. The Automatic mode's mini game runs in the browser and reflects real backend events. |
| Interface design | Project-owned design tokens and reusable Svelte components | Keep Manual and Automatic modes visually coherent while allowing each to have its own layout and interaction model. |
| Live app updates | Server-sent events (SSE) | Stream candidate, status and agent activity to the open app. |
| Storage | SQLite with write-ahead logging (WAL) | Persist decisions, settings, orders and positions on the single laptop. Keep only a bounded set of recent market data in memory; do not save every price tick. |
| Alerts | Telegram bot | Send candidate alerts, trade updates and urgent failures when the app is closed. |
| AI | Existing DeepSeek API | Summarize evidence for selected candidates; fixed code rules enforce safety and spending limits. |
| Host | Linux + systemd on the 4 GB laptop | Run Sonar continuously and restart it after a crash or reboot. |

**Market-data candidates:** PumpAPI.io first for discovery and live events; PumpPortal if a selective stream works better; GeckoTerminal/DEX Screener for extra context; GoPlus and RugCheck for risk checks; limited Helius for tracked wallets; Telegram channels with bot access for social signals. X is a later option if access costs fit. These providers are proposed, not yet benchmarked or committed.

**Still to select before live trading:** a provider for fresh executable quotes and order submission, the wallet/key setup, and concrete operational limits. Start by building Manual discovery and ranking, then paper trading, then Automatic trading. Avoid adding a separate database server or message broker unless measured load requires one.

Provider information was researched on 2026-10-20. Step 1 and the Step 2 feed probe are implemented; final feed selection, the 4 GB laptop trial, and strategy validation are still pending.

## 7. Step-by-step build and test guide

Build in this order. Finish each step's check before relying on the next one. The targets for feed freshness, resource use, API spending and trading risk must be written down before judging results; they are not yet known.

The interface is a major product track. Design it before filling the app with features, then test it with realistic data and failure states. Keep the Manual and Automatic experiences distinct without hiding data age, uncertainty, risk, mode state, or emergency controls. Interface work can progress while the long feed trial is pending.

### Step 1 — Set up the small foundation

**Add/build:** Create the Python/FastAPI service, Svelte/TypeScript app, SQLite database, configuration, structured logs and health status. Keep API keys and future wallet keys out of code, the browser and Git. Start with one service and bounded memory use.

**Test:** Start and restart it on the 4 GB laptop. Check memory, CPU, database persistence, missing configuration, and that no secret appears in logs or app responses.

### Step 2 — Measure discovery and price feeds

**Add/build:** Make a temporary feed probe for PumpAPI.io, then PumpPortal if needed. Capture token launches, pool changes, trades, source timestamps, disconnects and API usage. Compare a sample of pool prices and liquidity with independent sources.

**Test:** Observe quiet and busy periods. Measure event coverage, delay, reconnect behavior, price differences, RAM/CPU and projected monthly cost. Choose the primary feed only after it meets the written targets; keep a fallback plan if it fails.

### Step 3 — Design the interface and interaction model

**Add/build:** Define the main screens and complete user flows for switching modes, reviewing Manual candidates, changing filters and limits, receiving alerts, checking Automatic activity, and pausing new trades. Make phone and desktop wireframes, then an interactive prototype using realistic token examples. Define visual direction, typography, colors, spacing, reusable components, motion rules, and concise wording for scores, risks, data age, and uncertainty. Specify loading, empty, stale, provider-error, AI-error, paused, and open-position states. Manual mode must have no order controls; Automatic's mini game must correspond to real system states and keep critical status accessible.

**Test:** Walk through the prototype on phone and desktop. Check that the next action, current mode, freshness, major risks, and reason for each recommendation are understandable without reading logs. Review touch targets, keyboard use, contrast, readable text, and reduced-motion behavior. Record design decisions before implementation.

### Step 4 — Build continuous discovery

**Add/build:** Connect the chosen feed to Sonar. Deduplicate events, track each candidate's actual pool and age, reject malformed input, cap active candidates, and mark stale data. Store enough event history to explain decisions without saving every tick.

**Test:** Replay duplicates, out-of-order events, disconnects and provider outages. Verify new tokens are found once, prices show their age, and stale data cannot produce a fresh recommendation.

### Step 5 — Add the safety gate

**Add/build:** Call GoPlus and RugCheck only for surviving candidates. Check token permissions and transfer rules, holder/creator concentration, liquidity and basic exit feasibility. Define hard rejects and a wait state when critical evidence is missing.

**Test:** Use known unsafe and ambiguous token examples, missing fields and provider failures. Confirm that wallet activity, social hype and AI cannot override a hard rejection.

### Step 6 — Build the Judge's measurable signals

**Add/build:** Compute pool-specific liquidity, price movement, buys/sells, distinct traders and trading costs. Add a small, verified Helius wallet list and accessible Telegram channels only after the core market checks work. Deduplicate related wallets and repeated posts. Produce avoid/watch/recommended, reasons and a 1–100 ranking score.

**Test:** Replay recorded candidates, including rejected ones. Check score consistency, delayed signals and possible wash trading. Compare later outcomes using only information available at each decision time; the score must never be presented as a profit probability.

### Step 7 — Add DeepSeek carefully

**Add/build:** Send compact evidence for selected promising or ambiguous candidates. Require a short explanation and use code to validate the response. Keep all hard safety and budget limits in code.

**Test:** Simulate slow calls, API errors, invalid responses and contradictory advice. Sonar must continue with a clear non-AI result and never recommend or buy because the AI ignored a hard rule. Track AI call cost and latency.

### Step 8 — Build Manual mode and its interface

**Add/build:** Implement the designed Manual screen with reusable components and responsive phone/desktop layouts. Show ranked candidates without a table: filters, main facts, data age, risks, score, recommendation, AI summary, and bounded spend suggestion. Connect live updates to the backend and send selected Telegram alerts. Add user budget/risk settings and private access to the app. Manual mode has no new-order action.

**Test:** Check phone and desktop use, empty/loading/error/stale states, filters, alert duplicates and alert delay. Verify suggested spend never exceeds the configured or liquidity-based cap, and that Manual mode cannot open a trade.

### Step 9 — Refine and verify the Manual interface

**Add/build:** Use realistic recorded candidates and live updates to refine information hierarchy, wording, visual consistency, motion, and alert behavior. Make stale or missing evidence visibly different from fresh evidence. Keep updates readable when token activity is high and avoid unnecessary browser work on the 4 GB host.

**Test:** Review actual renders on small and large screens, with slow connections and long token names. Test loading, empty, error, stale, and fast-changing states; keyboard navigation, screen reader labels, contrast, reduced motion, and clarity of risk/spend wording. Fix usability problems before treating Manual mode as complete.

### Step 10 — Evaluate Manual recommendations live

**Add/build:** Run Sonar in observation mode and log every candidate, rejection, recommendation, timestamp and later outcome. Track provider and AI spending, false alerts and resource use.

**Test:** Compare ranked candidates with a simple baseline over new, unseen periods. Include realistic fees, slippage and missed entries; inspect bad calls and missed candidates. Adjust rules only from recorded evidence, then repeat the forward check.

### Step 11 — Prepare execution and wallet safety

**Add/build:** Choose and test a fresh executable quote/swap route and Solana transaction/RPC provider. Use a dedicated low-balance trading wallet; keep signing on the server. Implement durable order intents, one pending order per token, confirmation, balance reconciliation and hard trade/exposure/loss limits.

**Test:** Validate buy and sell quotes at intended sizes, including fees and price impact. Exercise rejected transactions, timeouts, duplicate events, unknown outcomes and restarts without double-ordering. Do not rely on a displayed price as proof that a token can be sold.

### Step 12 — Paper trade the full Action Controller

**Add/build:** Run the same entry, sizing, stop, profit, time-exit and emergency rules against live incoming data, but simulate orders with delays, fees, slippage and failed exits. Keep a durable position ledger.

**Test:** Review net results, drawdown, actual quote availability and exit failures over unseen periods. Force stale data, lost connectivity, liquidity withdrawal and a restart with an open position. Do not enable live Automatic mode until these cases recover safely and the results meet prewritten limits.

### Step 13 — Build and test the Automatic interface

**Add/build:** Implement the Automatic mini game with agents driven by real backend discovery, Judge, order, position, and risk events. Show clear mode state, active positions, recent decisions, failed actions, and emergency pause without making animation the only source of information. Add the mode switch and trade/failure alerts. Use the paper-trading controller as the event source until live trading is enabled.

**Test:** Check that animations match recorded events and recover after reconnect or page reload. Verify pause and mode-switch feedback, visible failures, accessible status, reduced motion, and phone/desktop performance. In paper trading, switching to Manual must stop new buys while existing positions continue their exit management.

### Step 14 — Make 24/7 operation reliable

**Add/build:** Run Sonar under systemd on the laptop, restrict remote access, back up the database and configuration safely, and monitor feed freshness, process health, disk space, API costs and open positions. Document how to stop new entries and recover after an outage.

**Test:** Reboot the laptop; interrupt the network and each provider; simulate low disk space; restore a backup. Verify Sonar resumes without duplicate orders, knows its real balances, and blocks new entries whenever critical state is uncertain.

### Step 15 — Enable small live Automatic trading

**Add/build:** Turn on real orders only after the earlier checks pass. Start with the dedicated wallet and very small limits. Connect the tested Automatic interface to real execution events.

**Test:** Compare real fills and sale proceeds with paper estimates. Verify that pause and switching to Manual stop new buys immediately while existing Automatic positions keep their exit management. Confirm every trade, fee, remaining balance and failed exit is recorded and alerted.

Sources: [PumpAPI](https://pumpapi.io/stream), [PumpPortal](https://pumpportal.fun/data-api/real-time/), [GoPlus](https://docs.gopluslabs.io/reference/solanatokensecurityusingget), [RugCheck](https://api.rugcheck.xyz/swagger/doc.json), [Helius](https://www.helius.dev/docs/api-reference/wallet-api/history), [Telegram](https://core.telegram.org/bots/api), [X pricing](https://docs.x.com/x-api/getting-started/pricing).
