# Hardening

Current security and operational posture as implemented, followed by a staged ladder to
production. The system handles email — personal data by definition — and its tools send
mail and create calendar events, so the gated-tool design is itself a security control.

## Current posture

**Authentication and secrets**

- API keys load from `.env` via `python-dotenv`; Gmail OAuth material lives in the
  `GMAIL_TOKEN` / `GMAIL_SECRET` env vars or `src/email_assistant/tools/gmail/.secrets/`.
  Both `.env` and `.secrets/` are gitignored.
- Gmail access uses a desktop OAuth flow (`setup_gmail.py`); the token JSON grants
  read/send/modify on the mailbox and calendar scopes.
- The local `langgraph dev` server is unauthenticated on `127.0.0.1:2024`; hosted
  LangGraph Platform deployments authenticate with a LangSmith API key, and secrets are
  provided as deployment env vars.
- **Secrets audit**: a scan of the tree at HEAD (key patterns, tokens, private keys,
  committed env files) found no live credentials. Only placeholder values exist in
  `.env.example`.

**Human-in-the-loop as a control**

- In the HITL graphs, `write_email`, `schedule_meeting`, and `Question` cannot execute
  without an explicit human decision delivered through a persisted interrupt; edits and
  rejections are recorded in thread state, giving a de facto approval trail in the
  checkpointer and LangSmith traces.
- The basic `email_assistant` graph has no such gate — its tools are mocks, and it
  should not be pointed at real tools as-is.

**Error handling and resilience**

- Graph nodes fail loud (`ValueError` on invalid classifications, unknown interrupt
  responses, unknown gated tools); integration edges fail soft (try/except with
  continue in ingestion and run cleanup).
- There is no retry/backoff, no circuit breaking, and no explicit timeout configuration
  on Gmail API or LangGraph SDK calls; a transient failure skips an email until a later
  ingestion pass happens to pick it up.

**Observability**

- LangSmith tracing covers every model call, tool call, and eval run when
  `LANGSMITH_TRACING=true`.
- Application logging is `print()` throughout — adequate for notebooks and `langgraph
  dev`, unstructured for anything else. No metrics, no alerting.

## Ladder to production

### Stage 1 — Identity and keys

- Move `OPENAI_API_KEY`, `GMAIL_TOKEN`, `GMAIL_SECRET` from long-lived env vars into a
  secrets manager appropriate to the hosting platform, with rotation; keep `.env` for
  local development only.
- Narrow Gmail OAuth scopes to the minimum the tools use (send, modify for
  mark-as-read, calendar events); create the OAuth client in a dedicated project so
  revocation is one switch.
- Separate keys per environment (dev / staging / prod LangSmith projects and OpenAI
  keys) so trace data and spend are attributable.
- If the assistant serves more than one mailbox, key the store namespaces and
  credentials per user; today the namespace `("email_assistant", ...)` is global.

### Stage 2 — Monitoring and resilience

- Replace `print()` with structured logging (module, thread ID, Gmail message ID,
  decision) so ingestion issues can be traced per email.
- Add bounded retry with backoff around Gmail API calls and LangGraph SDK calls, plus
  explicit timeouts; surface a dead-letter list of emails that failed ingestion instead
  of silently skipping them.
- Finish the message-level dedup check in `run_ingest.py` (the thread metadata already
  stores the last `email_id`) so overlapping cron windows cannot double-process.
- Alert on: triage `ValueError` rate, interrupt queues growing without human response,
  cron runs returning `{"status": "error"}`, and LangSmith error traces.

### Stage 3 — Deployment

- Run the Gmail variant only on hosted LangGraph Platform (or an equivalently secured
  self-hosted server); never expose an unauthenticated `langgraph dev` port beyond
  localhost.
- Pin the deployment to a reviewed branch; make the eval suite in
  [EVALUATION.md](EVALUATION.md) a pre-deploy gate.
- Set the cron cadence and `--minutes-since` window together so windows overlap
  slightly (no missed mail) once dedup exists (no double-processing).
- Keep `multitask_strategy="rollback"` deliberate: it discards in-flight runs when a
  newer message lands on a thread — correct for drafting replies, but audit-log the
  rollback events.

### Stage 4 — Data governance and compliance

- Email bodies persist in three places: LangGraph checkpoints, the preference store,
  and LangSmith traces. Define retention for each; LangSmith trace retention in
  particular should match the mailbox owner's expectations, since full email text is
  captured.
- Memory profiles are free-text distillations of user behavior; expose them to the user
  (they are readable strings by design) and provide a wipe path
  (delete the three store namespaces).
- Document the OpenAI data-processing terms in force for the account, since full email
  content is sent to the model on every triage and response.
- Preserve the HITL approval trail (interrupt requests + human responses in
  checkpoints) as the audit record for anything the assistant sent; ensure checkpoint
  retention outlives the emails it justifies.
