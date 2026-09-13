# Architecture

## Scope

This repository is the observability and data-ingestion layer around an email-assistant agent
graph (`email_assistant_hitl_memory_gmail`) that runs on LangSmith/LangGraph infrastructure
outside this codebase. Nothing here calls a model. The design questions this document answers
are therefore about the dashboard and the ingestion pipeline, and about the boundary between
this repo and the hosted agent.

## Component map

| Component | File(s) | Role |
|---|---|---|
| Dashboard app | `app.py` | Flask app with three routes: `/` (render dashboard), `/api/refresh` (JSON re-fetch), `/api/status` (JSON connectivity check). |
| Dashboard view | `templates/dashboard.html` | Single Jinja2 template: statistics cards, email-thread list, connection banner, and a JS `setInterval` that hits `/api/refresh` every 30 s and reloads the page. |
| Ingestion script | `ingest_to_langsmith.py` | CLI script: authenticates to Gmail via stored OAuth token, fetches messages from the last 60 minutes, extracts headers/body, POSTs each as a trace to LangSmith `/traces`. |
| Diagnostics | `test_langsmith.py`, `test_langsmith_integration.py` | Manual scripts that probe LangSmith endpoints and create sample runs. See [EVALUATION.md](EVALUATION.md). |
| Deployment config | `vercel.json`, `vercel-build.sh`, `requirements.txt` | Vercel `@vercel/python` build (Python 3.11), all routes rewritten to `app.py`. |

## Data flow, end to end

1. **Gmail → LangSmith** (`ingest_to_langsmith.py`): load OAuth client config and user token
   from `gmail_credentials/`; `users().messages().list` with an `after:` query for the recent
   window; per message, `messages().get`, header extraction (Subject/From/To/Date), MIME body
   extraction preferring `text/plain` over `text/html`, body truncated to 500 characters;
   each message POSTed individually to `{LANGSMITH_ENDPOINT}/traces` with inputs, outputs
   (`status: received`), tags, and metadata.
2. **Agent processing** (external): the hosted graph consumes inbox items and produces runs in
   LangSmith. This repo neither invokes nor configures it; the coupling is only the shared
   project/graph name.
3. **LangSmith → dashboard** (`app.py`): every page load calls `get_langsmith_data()`, which
   first runs a connectivity probe (`GET /datasets`), then fetches the dataset list and filters
   for names containing `GRAPH_ID`. If a matching dataset exists, statistics are derived from
   its `example_count`; otherwise a "connected, no data yet" payload with guidance text is
   returned. Errors at any stage render the template with an error banner and zeroed stats.
4. **Browser refresh loop**: the template auto-calls `/api/refresh` every 30 seconds and does a
   full `location.reload()` on success.

## Orchestration analysis: what runs parallel, sequential, async

- **Everything in this repo is sequential and synchronous.** The ingestion script processes
  emails in a plain `for` loop, one Gmail `get` and one LangSmith POST per message. The Flask
  handlers block on two serial `requests.get` calls (probe, then data fetch) before rendering.
- **No async, no workers, no queue.** Concurrency in production comes only from the hosting
  layer (Vercel spinning up function instances per request), not from the application.
- **Why this is acceptable at current scale:** the dashboard fetches a single small dataset
  listing, and the ingestion window is bounded (recent messages only). The trade-off is that
  each page load pays two round trips to LangSmith, and a slow upstream stalls the page —
  there are no timeouts on any `requests` call (see HARDENING.md).

## State and context engineering

- **Server state: none.** No database, no cache, no Flask session use. LangSmith is the
  single source of truth; the dashboard is a pure projection of it. This makes the Vercel
  serverless deployment safe (any instance can serve any request) at the cost of re-fetching
  on every load.
- **Context assembly for the agent: out of scope here.** The only "context shaping" this repo
  performs is on the ingestion side: body truncation to 500 characters, `text/plain` preferred
  over HTML, and a fixed inputs/outputs/tags/metadata trace schema. Memory and HITL state
  implied by the graph name live in the hosted graph, not in this code.

## Design decisions and trade-offs visible in the code

- **Poll, don't push.** The dashboard polls LangSmith and the browser polls the dashboard
  (30 s reload). Simple and stateless; the cost is staleness up to the polling interval and
  redundant upstream calls.
- **Datasets endpoint as the data source.** `app.py` reads `/datasets` rather than the runs
  API. The commit history and `STATUS_SUMMARY.md` indicate this was chosen because it was the
  endpoint that worked reliably. Consequence, visible in `get_langsmith_data()`: the
  "processed" and "HITL" numbers are heuristics derived from the dataset's `example_count`
  (`processed = total - 2`, `hitl = min(2, total)`), not real run statuses. The dashboard is
  currently a connectivity-plus-volume view, not a faithful per-run status board.
- **Fail-soft rendering.** Both `/` and the API routes catch all exceptions and return a
  degraded-but-rendered page or a `{"success": false}` JSON, never a 500 with a stack trace
  page. The error string is exposed to the client, which is a hardening concern.
- **Environment-variable configuration with in-code defaults.** Endpoint and graph ID default
  sensibly; note the differing `GRAPH_ID` defaults between `app.py`
  (`email_assistant_hitl_memory_gmail`) and `ingest_to_langsmith.py`
  (`autonomous-email-inbox`) — deployments should set the variable explicitly so ingestion
  and display target the same project.
- **Ingestion decoupled from serving.** The Gmail dependencies are only imported by the
  script, so the deployed dashboard does not need Google credentials, and `requirements.txt`
  deliberately covers only the Flask app.
