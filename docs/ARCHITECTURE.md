# Architecture

This document describes the system as it exists in the code: the components, the end-to-end
data flow, the orchestration model, and the design decisions visible in the implementation.

## Component map

| Component | File(s) | Role |
|---|---|---|
| Graph registry | `langgraph.json` | Registers six graphs for `langgraph dev` / LangGraph Platform |
| Basic pipeline | `src/email_assistant/email_assistant.py` | `triage_router` → `response_agent` (tool loop), mock tools |
| HITL pipeline | `src/email_assistant/email_assistant_hitl.py` | Adds `triage_interrupt_handler` and `interrupt_handler` gates |
| HITL + memory | `src/email_assistant/email_assistant_hitl_memory.py` | Adds `BaseStore` preference memory read/written around every human decision |
| Gmail variant | `src/email_assistant/email_assistant_hitl_memory_gmail.py` | Same graph shape with Gmail/Calendar tools and a `mark_as_read_node` terminal step |
| Ingestion graph | `src/email_assistant/cron.py` | Wraps `fetch_and_process_emails` in a one-node graph so LangGraph Platform crons can run it |
| State schemas | `src/email_assistant/schemas.py` | `StateInput`, `State` (extends `MessagesState`), `RouterSchema`, `UserPreferences`, `EmailData` |
| Prompts | `src/email_assistant/prompts.py` | Triage/system prompt templates, default preference profiles, memory-update instructions |
| Tool registry | `src/email_assistant/tools/base.py` | `get_tools(tool_names, include_gmail)` name→tool registry |
| Mock tools | `src/email_assistant/tools/default/` | `write_email`, `schedule_meeting`, `check_calendar_availability`, `Question`, `Done`, `triage_email` |
| Gmail tools | `src/email_assistant/tools/gmail/gmail_tools.py` | `fetch_emails_tool`, `send_email_tool`, `check_calendar_tool`, `schedule_meeting_tool`, `mark_as_read` |
| Ingestion CLI | `src/email_assistant/tools/gmail/run_ingest.py` | Gmail search → filter → submit each email as a LangGraph run |
| Cron setup | `src/email_assistant/tools/gmail/setup_cron.py` | Creates a hosted cron via `client.crons.create` |
| OAuth setup | `src/email_assistant/tools/gmail/setup_gmail.py` | Desktop OAuth flow producing `.secrets/token.json` |
| Helpers | `src/email_assistant/utils.py` | Email parsing (`parse_email`, `parse_gmail`), markdown formatting, tool-call extraction |
| Evaluation | `src/email_assistant/eval/`, `tests/` | Ground-truth dataset, triage experiment, pytest suite (see [EVALUATION.md](EVALUATION.md)) |

`src/email_assistant/configuration.py` is a placeholder `Configuration` dataclass (it maps
env vars / `RunnableConfig` fields but declares no fields yet); no graph consumes it today.

## End-to-end data flow (Gmail variant)

1. **Ingestion** — `run_ingest.py` (manually, or the hosted `cron` graph on a schedule)
   builds a Gmail search query from CLI flags (`to:X OR from:X`, `after:timestamp`,
   `is:unread` unless `--include-read`), then applies two code-level filters unless
   `--skip-filters`: skip messages the user sent, and skip messages that are not the
   latest in their thread.
2. **Run creation** — for each surviving message, the script derives a deterministic
   LangGraph thread ID (`uuid.UUID(md5(gmail_thread_id))`), fetches-or-creates the
   thread, deletes that thread's previous runs, stamps the thread metadata with the
   Gmail message ID, and creates a run for `email_assistant_hitl_memory_gmail` with
   `multitask_strategy="rollback"`.
3. **Triage** — `triage_router` parses the email, loads `triage_preferences` from the
   store, and classifies with a structured-output LLM (`RouterSchema`: reasoning +
   `ignore | respond | notify`). It returns a `Command` that both updates state and
   routes: `respond` → response agent, `notify` → triage interrupt, `ignore` → END.
4. **Notify interrupt** — `triage_interrupt_handler` raises `interrupt()` with the
   rendered email; Agent Inbox shows it. A human reply routes into the response agent
   (and updates triage memory); an ignore ends the run (also updating triage memory).
5. **Response loop** — `llm_call` loads `response_preferences` and `cal_preferences`
   from the store, assembles the system prompt, and calls `gpt-4.1` with
   `tool_choice="required"`. Because a tool call is forced on every turn, the loop
   terminates only when the model calls the `Done` tool.
6. **Tool-gate interrupt** — `interrupt_handler` walks the tool calls serially.
   Non-gated tools (e.g. `check_calendar_availability`) execute immediately. Gated
   tools (`write_email`, `schedule_meeting`, `Question`) raise `interrupt()` with a
   per-tool capability config (accept/edit/respond/ignore) and block until Agent Inbox
   answers. Accept executes as-is; edit rewrites the AI message's tool call
   immutably (`model_copy`) then executes; respond feeds the feedback back to the
   model without executing; ignore ends the run.
7. **Memory update** — every edit, feedback, or ignore triggers `update_memory`, which
   feeds the current profile plus the correction transcript to a structured-output LLM
   (`UserPreferences`) and writes the rewritten profile back to the store.
8. **Completion** — on `Done`, the Gmail variant routes to `mark_as_read_node`, which
   calls the Gmail API to mark the message read, then ends. Human decisions and final
   state live in the thread's checkpoint history; traces go to LangSmith.

The mock variants short-circuit this flow: no ingestion, tools return canned strings,
and (in the basic graph) `notify` simply ends the run.

## Orchestration analysis

- **Sequential by design.** Triage strictly precedes response. Inside the response
  agent, tool calls from one model turn are processed in a `for` loop, one at a time,
  and each gated call blocks on a human interrupt before the next is examined. For an
  agent whose tools send email and create calendar events, serializing side effects
  behind approvals is the correct trade — throughput is bounded by human latency
  anyway, and out-of-order sends would be observable errors.
- **Nothing is parallel inside a graph.** There is no fan-out; the only concurrency in
  the repository is client-side: `run_ingest.py` is `asyncio`-based over the LangGraph
  SDK, and `pytest-xdist` is available for the test suite.
- **Async at the edges.** Ingestion and cron are asynchronous relative to the graphs:
  they submit runs over HTTP and return. `multitask_strategy="rollback"` means a new
  email arriving on the same thread supersedes an in-flight run instead of queuing
  behind it — for an inbox, the newest message is the only one worth answering.
- **Interrupts are the control plane.** HITL is not a callback or a polling loop; it is
  LangGraph's native `interrupt()`, which persists the paused state in the checkpointer
  and resumes on a `Command(resume=...)`. This is what lets a human answer hours later
  from Agent Inbox without any process staying alive.

## State and context engineering

**Session state.** `StateInput` (`email_input: dict`) is the public input schema;
`State` extends `MessagesState` with `classification_decision`. Message history
accumulates via the standard reducer. Checkpointing is provided by the runtime
(`langgraph dev` / Platform supply the checkpointer and store; tests compile the same
`overall_workflow` with `MemorySaver` + `InMemoryStore`).

**Long-term memory.** Three profiles in a `BaseStore`, all under key
`"user_preferences"`:

| Namespace | Seeded from | Updated when |
|---|---|---|
| `("email_assistant", "triage_preferences")` | `default_triage_instructions` | Human overrides a notify decision, or ignores a gated draft/question |
| `("email_assistant", "response_preferences")` | `default_response_preferences` | Human edits or gives feedback on `write_email` |
| `("email_assistant", "cal_preferences")` | `default_cal_preferences` | Human edits or gives feedback on `schedule_meeting` |

`get_memory` lazily seeds a missing profile with the default and returns the stored
text; `update_memory` rewrites the whole profile through a structured-output LLM
guided by `MEMORY_UPDATE_INSTRUCTIONS` (plus a reinforcement suffix to keep edits
conservative). Memory is therefore human-feedback-driven only — the agent never
writes memory from its own behavior.

**Context assembly.** Each LLM call builds its context deterministically from parts:
prompt template + background profile + the relevant memory profiles + the email
rendered to markdown (`format_email_markdown` / `format_gmail_markdown`). The context
is naturally bounded: one email thread, one system prompt, and the running message
list for this thread only. No retrieval, no cross-thread context.

## Design decisions and trade-offs visible in the code

- **Router as structured output, not a tool.** Triage uses
  `with_structured_output(RouterSchema)` with a required `reasoning` field, and routes
  with `Command(goto=...)`. This keeps classification single-shot and typed. (A
  `triage_email` tool also exists in `tools/default/email_tools.py` but no graph uses
  it — the notebooks explore that alternative.)
- **`tool_choice="required"` + `Done` tool.** Forcing a tool call every turn removes
  the ambiguous "assistant replied with prose" terminal state; the model must
  explicitly call `Done`. The cost is one extra schema in the tool list and a
  conditional edge that special-cases it.
- **Per-tool interrupt capability matrix.** `write_email` and `schedule_meeting`
  allow accept/edit/respond/ignore; `Question` allows respond/ignore only (you cannot
  "accept" a question to yourself). The matrix is explicit in `interrupt_handler`,
  and unknown tools raise `ValueError` rather than passing silently.
- **Immutable state edits.** When a human edits a tool call, the code replaces the AI
  message via `model_copy(update={"tool_calls": ...})` instead of mutating in place —
  required for checkpoint consistency.
- **Whole-profile memory rewrite.** Memory updates rewrite the entire preference
  profile each time. Simple and inspectable (the profile is human-readable text), at
  the cost of an LLM call per correction and no concurrency control on the store key.
- **Deterministic thread identity.** Hashing the Gmail thread ID into a UUID makes
  re-ingestion idempotent at the thread level and lets all messages of a conversation
  share one LangGraph thread (and thus one memory of prior turns). Prior runs are
  deleted before a new one is created to avoid state accumulation; a message-level
  dedup check is still a `TODO` in `run_ingest.py`.
- **Fail-loud graph nodes, fail-soft edges.** Inside graphs, invalid classifications
  and unknown interrupt responses raise `ValueError`. At the integration edges
  (ingestion, Gmail API, run cleanup), errors are caught, printed, and processing
  continues with the next item.
- **Model choice is hard-coded.** Every call site constructs
  `init_chat_model("openai:gpt-4.1", temperature=0.0)` inline. Consistent and simple,
  but switching providers today means editing four files (see below).

## Extending this system

Grounded next steps that the current architecture makes cheap:

1. **Finish ingestion idempotency.** `run_ingest.py` already stamps each thread's
   metadata with the last processed Gmail message ID and carries a `--rerun` flag whose
   check is an explicit `TODO`. Comparing the incoming message ID against the stored
   metadata would close the loop and make the cron safe against overlapping windows.
2. **Make the model configurable.** `configuration.py` is an empty
   `Configuration.from_runnable_config` scaffold. Adding a `model` field there and
   threading it through the `init_chat_model` call sites in the four graph modules
   would allow per-deployment
   model selection (the `init_chat_model("provider:model")` indirection already supports
   any LangChain-integrated provider) without touching graph logic.
3. **Bring the HITL and memory graphs under test.** `tests/run_all_tests.py` documents
   exactly why only the basic graph is tested: the ground-truth dataset lacks `Question`
   tool expectations and the resume command is hard-coded to accept. Extending the
   dataset and driving interrupts with scripted `Command(resume=...)` sequences would
   cover the graphs that actually ship.
4. **Few-shot triage from the store.** `utils.format_few_shot_examples` already formats
   stored email examples for prompting but has no caller. Persisting confirmed triage
   decisions as store examples and injecting the nearest ones into the triage prompt is
   a natural upgrade from profile-text memory toward episodic memory.
5. **A second mail provider behind the same registry.** `get_tools(include_gmail=...)`
   isolates provider tools behind a name→tool registry, and the graph names tools, not
   providers. An Outlook/IMAP adapter exposing the same four tool names would slot in
   with a new variant module and zero changes to the graph shape.

## Absorbed operational components (2026 consolidation)

Two formerly separate repositories were consolidated into this one so the agent, its
platform integration, and its operational surface live together:

- **Agent Inbox / LangGraph Platform integration** — `src/email_assistant/tools/gmail/`
  gained `agent_inbox_parser.py`, `langgraph_platform_fetcher.py`, `langsmith_parser.py`,
  `run_ingest_agentinbox.py`, and `setup_cron_agentinbox.py`, plus root-level deployment
  guides (`LANGRAPH_PLATFORM_DEPLOYMENT_GUIDE.md`, `LANGSMITH_DEPLOYMENT_GUIDE.md`) and
  integration tests (`test_agentinbox_integration.py`, `test_langgraph_platform_integration.py`,
  `test_langsmith_integration.py`). These connect the compiled graph to a hosted LangGraph
  Platform deployment and surface interrupts in Agent Inbox.
- **Operations dashboard** — `ops-dashboard/` is a small Flask application
  (`app.py`, `templates/dashboard.html`) with a Gmail-to-LangSmith ingestion runner
  (`ingest_to_langsmith.py`) and a Vercel deployment configuration. It monitors runs and
  feeds real mailbox traffic into LangSmith for tracing; it contains no agent logic.
