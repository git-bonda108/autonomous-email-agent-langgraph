# Evaluation and Testing

## What exists today

There is **no automated test harness** in this repository: no pytest/unittest suites, no
assertions, no CI configuration. The two `test_*.py` files are manual diagnostic scripts that
exercise the live LangSmith API and print results for a human to read:

| Script | Run with | What it does |
|---|---|---|
| `test_langsmith.py` | `python test_langsmith.py` | Probes LangSmith connectivity: `GET /projects`, `POST /runs/search`, then `GET` against `/runs`, `/traces`, `/datasets`, `/projects`, and finally checks whether the configured `GRAPH_ID` exists as a project. Prints status codes; asserts nothing. |
| `test_langsmith_integration.py` | `python test_langsmith_integration.py` | Creates four hardcoded sample email runs via `POST /runs` against the **live** LangSmith project, waits 5 seconds, then imports `get_langsmith_data()` from `app.py` and prints the statistics it returns. Side-effectful: it writes data into the real project. |

Both require a valid `LANGSMITH_API_KEY` in the environment. Neither returns a non-zero exit
code on failure, so they cannot gate a pipeline as written.

No metrics (accuracy, latency, coverage) are recorded anywhere in the code or docs, so none
are claimed here.

## Edge cases the code visibly handles

Enumerated from the source, not inferred:

- **Missing API key**: `app.py` renders the dashboard with an error banner
  (`test_langsmith_connection` returns an error status; `get_langsmith_data` raises and the
  route catches it); it does not crash.
- **Non-200 LangSmith responses**: checked at every call site in `app.py`,
  `ingest_to_langsmith.py`, and both diagnostic scripts; converted to error payloads or
  printed failures.
- **Connected but no matching dataset**: `get_langsmith_data()` returns a zeroed-statistics
  payload with `demo_mode: true` and explicit next-step guidance, which the template renders
  as an informational panel rather than an error.
- **Dataset exists but has zero examples**: handled as a distinct branch (zero stats, empty
  email list).
- **Empty inbox window**: `fetch_recent_emails` returns `[]` and `main()` exits with an
  informational message.
- **Missing Gmail credential files**: explicit `FileNotFoundError` with the expected path
  before any network call.
- **Multipart MIME bodies**: `extract_message_part` prefers `text/plain`, falls back to
  `text/html`, then to the direct body, then to an empty string.
- **Missing email headers**: `next(..., default)` fallbacks for Subject/From/To/Date.
- **Oversized bodies**: truncated to 500 characters before being sent to LangSmith.
- **Blanket exception catches**: every route and script `main()` wraps its work in
  `try/except Exception`, so failures degrade to messages instead of crashes.

## Edge cases the code does not handle

- **No timeouts**: every `requests` call omits `timeout=`; a hung upstream hangs the request.
- **No retries or backoff** on any HTTP call.
- **Statistics are heuristic**: with a non-empty dataset, `app.py` computes
  `processed = total - 2` and `hitl = min(2, total)` from `example_count` rather than reading
  real run statuses. The numbers indicate volume, not actual processing outcomes.
- **Response-shape assumptions**: `app.py` iterates the `/datasets` response directly as a
  list; a shape change upstream would surface only as a caught generic exception.

## Proposed evaluation harness

None of the following exists yet; it is a design proposal sized to what this system is.

1. **Unit layer (no network)** — pytest with `responses` or `requests-mock`:
   - `get_langsmith_data()` against canned `/datasets` payloads: matching dataset with N
     examples, matching dataset with 0, no match, non-200, malformed body.
   - `extract_message_part()` against fixture Gmail payloads: multipart plain, multipart
     HTML-only, single-part, empty.
   - Route tests via Flask's test client: `/`, `/api/refresh`, `/api/status` for both the
     healthy and the failing-upstream paths (assert the fail-soft contract: 200 + error
     payload, no stack trace in the body).
2. **Golden dataset shape** — a checked-in `tests/fixtures/` directory of JSON files:
   Gmail message payloads (one per MIME variant) and LangSmith dataset/run responses (one per
   branch above). Each fixture pairs with an expected statistics dict, making the
   volume-to-statistics mapping an explicit, reviewable contract.
3. **Gates** — CI (e.g. a GitHub Actions workflow) running the unit layer on every push;
   fail the build on any test failure. Add a secret-scanning step (e.g. gitleaks) as a second
   gate given this repo's history (see HARDENING.md).
4. **Live smoke (optional, manual trigger only)** — a single parametrized script replacing
   today's two diagnostics: probe connectivity, assert HTTP 200s, exit non-zero on failure,
   and never write runs to a production project by default.
5. **Metrics worth recording once real run data is read**: dashboard render latency,
   LangSmith call latency, ingestion success ratio (sent vs. fetched), and staleness (time
   since last successful refresh). None of these are measured today.
