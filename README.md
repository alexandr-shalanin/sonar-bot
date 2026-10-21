# Sonar

Sonar has a FastAPI service, a Svelte/TypeScript portfolio page, and local SQLite storage. Discovery and trading are not implemented.

## Interface structure

`web/src/App.svelte` opens `web/src/screens/Portfolio.svelte`, the only implemented screen. Manual, Automatic, and Settings remain empty components pending their interface briefs. The portfolio fills the page with a centered pink CRT title, a bright pixel reef on the left, and the intro on the right. Local cat sprites react on hover; the fish swim and scatter on ocean hover. Motion respects reduced-motion preferences. GitHub links to the supplied profile; Discord and “Let’s start” are disabled until destinations are supplied. Artwork prompts are recorded in [portfolio design notes](docs/portfolio-design.md).

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

Open `http://127.0.0.1:8000/` for the portfolio and `http://127.0.0.1:8000/health` for `{"status":"ok"}`. The service can start before the web build; in that case only the API is available. SQLite is stored at `data/sonar.db` relative to the process working directory, or under `SONAR_DATA_DIR` if set. Logs are JSON lines on stderr. Bind to a trusted interface only; there is no app authentication yet.

## Check

After building the web app, run:

```sh
cd service
../.venv/bin/python -m unittest discover -s tests -v
```

The smoke test starts the service twice and checks `/health`, the placeholder page, SQLite WAL mode and persistence, and that a test secret is absent from responses and logs.

## Step 2 feed probe

The read-only PumpAPI measurement tool is separate from the app. See [feed probe instructions](docs/feed-probe.md) for a short run, optional PumpPortal launch comparison, and the 24–48 hour laptop trial.
