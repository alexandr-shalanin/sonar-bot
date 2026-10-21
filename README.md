# Sonar

Step 1 foundation: a FastAPI service, a static Svelte/TypeScript placeholder, and local SQLite storage. Discovery and trading are not implemented.

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

Open `http://127.0.0.1:8000/` for the placeholder and `http://127.0.0.1:8000/health` for `{"status":"ok"}`. The service can start before the web build; in that case only the API is available. SQLite is stored at `data/sonar.db` relative to the process working directory, or under `SONAR_DATA_DIR` if set. Logs are JSON lines on stderr. Bind to a trusted interface only; there is no app authentication yet.

## Check

After building the web app, run:

```sh
cd service
../.venv/bin/python -m unittest discover -s tests -v
```

The smoke test starts the service twice and checks `/health`, the placeholder page, SQLite WAL mode and persistence, and that a test secret is absent from responses and logs.
