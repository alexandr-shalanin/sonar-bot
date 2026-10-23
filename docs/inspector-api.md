# Inspector API v1

Inspector is an on-demand Solana snapshot. It works for an address that has never appeared in `/candidates`; discovery streams can remain disabled. No keys, new packages, database writes or migrations are required.

## Request

`POST /inspector`, `Content-Type: application/json`

```json
{"mint":"JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"}
```

The address must decode from base58 to exactly 32 bytes. Whitespace is trimmed; URLs, pool searches and symbols are not accepted. A syntactically valid address is not proof that a mint exists.

## Report

- `token`: provider name, symbol and HTTPS image URL, when present. Metadata remains untrusted display data; no metadata URI is fetched.
- `selected_pool` and `pools`: Solana pools with the requested mint as **base token**, ordered by reported USD liquidity descending, then pool ID. Quote-side pairs are excluded because their `priceUsd` belongs to another token. This is a snapshot of the pools returned by the indexer, not exhaustive chain coverage.
- Pool data: address, DEX, base/quote mint, USD price, liquidity, FDV, market cap, pool creation time/age, changes, volume and observed buys/sells over `m5`, `h1`, `h6`, `h24`. Pool age is not token age. Missing fields remain `null`; unavailable one-minute data is not inferred from five-minute data.
- `goplus`: mint/freeze permissions, transfer restrictions, account closure/balance mutation and upgradable rules, reported transfer fee.
- `rugcheck`: permissions/addresses, token program, raw supply/decimals, creator, up to 20 holder token accounts, top-10 token-account concentration, matching-pool LP facts and provider findings. `creator_top_holders_pct` concerns only returned top accounts. `provider_score` is RugCheck's own raw score (higher means riskier), separate from Sonar's score.
- `sources`: status, safe error code/HTTP status and receipt time for each source. Provider failures retain the data obtained from the other sources.
- `generated_at_ms`, `cache`, `status`, `score`, `limitations` describe the snapshot and its limits.

Statuses: `complete` means the v1 rubric has the required data, `partial` means some evidence is missing, `no_data` means successful sources had no usable token data, and `unavailable` means all three requests failed. None establishes safety or absence of a token on chain. A report with a known hard block may still be partial.

DEX Screener does not provide the source price-tick time in this response. RugCheck reports can also be cached upstream; `detectedAt` is not a report-refresh time. All `source_updated_at_ms` fields therefore remain `null`. `fetched_at_ms` and cache age describe receipt by Sonar, not verified market freshness. No score measures data freshness or validates an executable exit.

## Sonar score (`inspector-v1`)

`kind=risk_screening`, `higher_is_better=true`, `calibration=heuristic_unvalidated`. These are provisional rules for screening observed facts; they have not been calibrated against future returns, scams or losses. The score is not a growth probability or trading recommendation. There are no safe/unsafe bands based solely on its value.

| Component | Maximum | Rule |
| --- | ---: | --- |
| Authorities | 25 | Both sources report no active mint/freeze authority and RugCheck does not report `rugged`. |
| Transfer rules | 20 | All eight GoPlus restriction/upgradability flags must be known and false. Fee 0 bps: 20; 1–100 bps: 10; higher fee: 0. Missing fee can be treated as 0 only for the classic SPL Token program, which has no transfer-fee extension. |
| Selected-pool liquidity | 25 | At least $100k: 25; $50k: 20; $10k: 12; $1k: 5; below $1k: hard block. If RugCheck has a matching pool, use the smaller reported liquidity. |
| Address concentration | 15 | Top-10 token accounts at most 20%: 15; at most 40%: 10; at most 60%: 5; otherwise 0. Pools and contracts are included; owners are not proven independent. Incomplete or malformed holder evidence cannot earn points. |
| Provider findings | 10 | No RugCheck `warn`/`danger` findings: 10; otherwise 0. Unknown severity makes the evidence incomplete. |
| Observed activity | 5 | Selected pool has positive five-minute volume and both observed buys and sells: 5; observed zero activity: 0. |

Hard blocks override points and missing data: any observed active mint/freeze authority, non-transferable/default-frozen token, transfer hook, upgradable transfer fee/hook/default account state, balance mutation/closure authority, 100% reported transfer fee, `rugged`, or selected-pool liquidity below the provisional $1,000 floor produces `status=blocked`, `value=0` and named `block_reasons`.

Without a block, any missing required evidence or conflicting permissions makes `value=null`, `status=insufficient_data`. Matching-pool liquidity estimates that differ by more than a factor of two also prevent a score. A RugCheck `danger` finding caps an otherwise computable score at 49. The response exposes every component, cap, missing field and conflict.

`coverage_pct` is the sum of rubric weights with known component results; it is not confidence or the percentage of all possible risks checked. Missing USD price or a cross-source conflict can prevent a score even when weighted coverage is 100%.

## Limits and errors

Three independent requests run concurrently using fixed HTTPS provider URLs with TLS verification. There are no automatic retries. Socket timeout: 8 seconds; body reads check a 12-second wall-clock budget between chunks (a blocked socket may add up to its timeout). RugCheck reports are bounded at 8 MiB because mature-token reports may exceed 2 MiB; other responses are bounded at 2 MiB. Errors never include raw provider bodies.

An in-memory 30-second cache holds at most 128 reports, including partial/failure reports. Concurrent requests for the same mint share work; at most four distinct reports run concurrently per service process. These local limits do not replace provider quotas. Rate-limited sources are explicitly reported and not silently retried. The cache is neither report history nor persistent Track storage.

- `200`: full, partial or no-data report.
- `422`: invalid request, before any provider call.
- `429`: local concurrency limit, `Retry-After: 5`.
- `503`: all providers failed; the response still contains the report and source errors.

Responses use `Cache-Control: no-store`. The Vite proxy forwards `/inspector` to the local FastAPI service. The Inspector search UI submits addresses to this API and displays a compact report. The service remains local-only with no authentication; do not expose it publicly without access controls and per-user rate limits.

Sources: [DEX Screener API](https://docs.dexscreener.com/api/reference), [GoPlus Solana security](https://docs.gopluslabs.io/reference/solanatokensecurityusingget), [RugCheck OpenAPI](https://api.rugcheck.xyz/swagger/doc.json).
