# Hardening and Production Readiness

## Current posture (as the code stands)

- **Authentication on the dashboard: none.** `/`, `/api/refresh`, and `/api/status` are
  unauthenticated. Anyone with the deployment URL can view email subjects, statistics, and —
  via the error paths — upstream error strings. The Vercel setup adds no access control.
- **Secrets handling.** Configuration is read from environment variables via `python-dotenv`,
  which is the right mechanism — but a real LangSmith API key was previously committed in five
  files (now redacted at HEAD; see the bottom of this document). Gmail OAuth material is
  correctly kept out of the repo as local files under `gmail_credentials/`, and `.gitignore`
  now excludes that directory, `.env`, token/credential JSON, and key files.
- **Outbound calls.** All LangSmith and Gmail calls go over HTTPS. No `requests` call sets a
  timeout, and there are no retries; a slow or hung upstream stalls the serverless function
  until the platform kills it.
- **Error handling.** Fail-soft everywhere: exceptions are caught and rendered as banners or
  JSON error fields. The downside is information exposure — raw `str(e)` values (which can
  include endpoint URLs and upstream response fragments) are returned to the browser.
- **Debug mode.** `app.py` ends with `app.run(debug=True)`. That is the local entry point
  (Vercel invokes the app object, not `__main__`), but running it as-is on any reachable host
  exposes the Werkzeug debugger, which allows code execution.
- **Observability: none.** No logging module, no structured logs, no metrics, no health
  endpoint beyond `/api/status` (which itself calls the upstream).
- **Data exposure by design.** The ingestion script sends email subject, sender, recipient,
  and the first 500 characters of the body to LangSmith. That is the product's purpose, but it
  makes the LangSmith project itself sensitive: whoever holds the API key can read inbox
  content.

## Ladder to production

### Stage 1 — Identity and keys (do first)

1. Rotate the leaked LangSmith API key and purge it from git history (see below). Verify the
   old key is dead by calling the API with it.
2. Move all secrets to the platform secret store (Vercel environment variables); never rely on
   in-code defaults for credentials. Remove the `<REDACTED-ROTATE-ME>` fallback string in
   `ingest_to_langsmith.py` in favor of failing fast when the variable is unset.
3. Put authentication in front of the dashboard: at minimum Vercel deployment protection or
   basic auth; properly, an identity layer (e.g. OAuth via the hosting platform) since the
   page displays private email metadata.
4. Scope the Gmail OAuth token to `gmail.readonly` if it is not already, and document the
   token refresh procedure (the script currently assumes a valid `token.json`).

### Stage 2 — Robustness and monitoring

1. Add `timeout=` to every `requests` call and bounded retries with backoff for idempotent
   GETs.
2. Stop returning raw exception strings to clients; log them server-side (structured JSON
   logs) and return a generic message with a correlation ID.
3. Replace the heuristic statistics in `get_langsmith_data()` with real run statuses once the
   runs API integration is settled, so the dashboard reports truth (see ARCHITECTURE.md).
4. Add the automated test layer and CI gates proposed in EVALUATION.md, including a secret
   scanner on every push.
5. Add uptime monitoring against `/api/status` and alerting on sustained connection errors.

### Stage 3 — Deployment hygiene

1. Ensure `debug=True` can never reach a deployed environment (guard on an env var, default
   off).
2. Pin and complete dependencies: add the Google API client libraries to a separate
   `requirements-ingest.txt` (they are imported but unlisted today), and adopt a lockfile.
3. Run the ingestion script as a scheduled job (cron / scheduled function) rather than
   manually, with its own logging and failure alerting.
4. Add security headers (CSP, X-Content-Type-Options, frame denial) to Flask responses; the
   dashboard currently sets none.

### Stage 4 — Compliance and data governance

1. Treat the LangSmith project as a PII store: email bodies and addresses land there. Define
   retention for traces/runs and document who holds keys.
2. Document the Gmail account owner's consent and the data path (Gmail → LangSmith →
   dashboard viewers) for any org privacy review.
3. Restrict LangSmith key permissions to the single project, if the plan supports scoped keys.

## Secrets removed from HEAD — rotate these credentials and purge history

The following files at HEAD contained a live LangSmith API key (`lsv2_sk_…`), now replaced
with `<REDACTED-ROTATE-ME>`:

- `README.md` (rewritten)
- `DEPLOYMENT.md`
- `ingest_to_langsmith.py`
- `test_langsmith.py`
- `test_langsmith_integration.py`

The key remains in git history. **Rotate it in LangSmith immediately**, then purge history
(e.g. `git filter-repo --replace-text`) and force-push, or treat the repository history as
public knowledge of a dead key after rotation.
