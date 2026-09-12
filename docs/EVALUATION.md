# Evaluation

An honest account of what is tested today, how to run it, what edge cases the code
handles, and what a production evaluation harness should add.

## What exists

### Ground-truth dataset

`src/email_assistant/eval/email_dataset.py` defines 16 hand-written emails with, per
example: the expected triage label (8 `respond`, 6 `notify`, 2 `ignore`), the expected
tool-call sequence for `respond` emails, and a natural-language response criterion used
by the LLM judge. `examples_triage` packages the same data for the LangSmith
`evaluate` API.

### Automated tests (`tests/`)

Run with API keys set (`OPENAI_API_KEY`, `LANGSMITH_API_KEY`); results log to LangSmith:

```bash
python tests/run_all_tests.py          # wrapper; sets the LangSmith project/experiment
pytest tests/test_response.py -v --agent-module=email_assistant   # direct
python tests/test_notebooks.py         # execute every notebook end to end
```

| Test | File | What it asserts |
|---|---|---|
| `test_email_dataset_tool_calls` | `tests/test_response.py` | For every dataset email labeled `respond`: all expected tool calls appear in the agent's trace. Extra calls are allowed; missing calls fail. |
| `test_response_criteria_evaluation` | `tests/test_response.py` | An LLM judge (`gpt-4o`, structured output `CriteriaGrade`: boolean grade + justification) grades the full message transcript against that email's criterion; the boolean must be true. |
| `test_notebook_runs_without_errors` | `tests/test_notebooks.py` | Every notebook under `notebooks/` executes without raising, 600 s timeout per notebook. |

`tests/conftest.py` adds `--agent-module` so the same suite can target any graph
module, and `notebooks/test_tools.py` runs a two-example smoke version of the
tool-call check.

**Scope limitation, stated in the code:** `tests/run_all_tests.py` runs only the basic
`email_assistant` graph. Its comments give the reason: the HITL/memory variants use the
`Question` tool, which the dataset's ground truth does not model, and the hard-coded
resume command (`Command(resume=[{"type": "accept", "args": ""}])`) is invalid for
`Question` interrupts, so those runs would loop. The graphs that add HITL, memory, and
Gmail — the ones closest to production — are therefore **not** covered by the
automated suite today.

### Triage experiment

`src/email_assistant/eval/evaluate_triage.py` creates (once) a LangSmith dataset from
`examples_triage`, runs the basic assistant over it via `client.evaluate`, scores with
an exact-match `classification_evaluator`, and renders a matplotlib comparison chart
into `src/email_assistant/eval/results/`. One generated artifact is committed
(`triage_comparison_20250411_151828.png`). No accuracy figures are asserted in code or
recorded in text, so none are quoted here; per-run metrics live in LangSmith when the
script is executed.

## Edge cases the code visibly handles

Enumerated from the source, not from intent:

- **Invalid model output**: `triage_router` raises `ValueError` on a classification
  outside `ignore | respond | notify`; interrupt handlers raise on unknown response
  types and unknown gated tools (`email_assistant*.py`).
- **Unseeded memory**: `get_memory` lazily writes the default profile on first read
  (`email_assistant_hitl_memory*.py`).
- **Credential fallback chain**: Gmail token is read from the `GMAIL_TOKEN` env var
  first, then `.secrets/token.json`; each parse is wrapped in try/except
  (`run_ingest.py`, `gmail_tools.py`).
- **MIME variance**: message extraction recursively walks multipart payloads,
  preferring `text/plain`, falling back to `text/html`, returning `""` when nothing
  decodes (`run_ingest.py`, `gmail_tools.py`).
- **Empty inbox**: ingestion returns cleanly when the Gmail search matches nothing.
- **Thread races at the server**: thread fetch falls back to create; stale-run deletion
  failures are caught per run and skipped; `multitask_strategy="rollback"` supersedes
  an in-flight run when a newer message arrives (`run_ingest.py`).
- **Ingestion isolation**: the cron graph wraps the whole fetch in try/except and
  returns `{"status": "error", ...}` instead of crashing the scheduled run (`cron.py`).
- **Test-side tolerance**: extra tool calls do not fail the tool-call test; notebook
  execution is bounded by a timeout; graph state extraction handles both state shapes
  (`tests/`).

**Known absences** (verified by search): no retry/backoff logic anywhere, no explicit
HTTP timeouts on Gmail/SDK calls, message-level ingestion dedup is a `TODO`, and no CI
pipeline runs the test suite.

## Proposed evaluation harness

The following does not exist and is design, not description.

1. **Golden dataset, versioned and split.** Keep the 16 examples as a smoke set; grow a
   versioned JSONL golden set (target ≥100 emails) with fields
   `{email_input, triage_label, expected_tools, forbidden_tools, response_criteria,
   hitl_script}` — `hitl_script` being a scripted sequence of interrupt responses
   (accept / edit-with-args / respond-with-feedback / ignore) so the HITL and memory
   graphs become drivable end to end with `Command(resume=...)`.
2. **Deterministic-first gating.** Gate merges on the deterministic checks only:
   triage exact-match accuracy (per-class, so the 2-example `ignore` class cannot hide
   in the average), tool-call precision/recall, and a no-`write_email`-without-approval
   invariant for HITL runs. Track the LLM-judge pass rate as a trend metric, not a hard
   gate, until judge variance is characterized (temperature 0, fixed judge model,
   double-grade a 10% sample).
3. **Memory-update regression tests.** Given a fixed correction transcript, assert the
   rewritten profile preserves unrelated preferences and encodes the correction
   (string-level containment checks are enough to start); assert store writes land in
   the correct namespace.
4. **CI wiring.** Run the smoke set on every PR (the suite already parallelizes with
   `pytest-xdist`) and the full golden set nightly, with LangSmith experiment names
   keyed to the commit SHA so regressions bisect cleanly.
5. **Ingestion tests without Gmail.** The Gmail search→filter→submit pipeline is pure
   logic around two API clients; faking both (recorded message payloads, in-memory SDK)
   would let the thread-identity, filtering, and rollback behavior be tested offline.
