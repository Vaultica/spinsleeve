# SpinSleeve: Vibe Coding Agent Manual

A quick-reference developer guide for vibe coding on **SpinSleeve** with Gemini CLI, preserving **Conceptual Integrity**, optimizing token costs, dynamically switching models, and orchestrating specialized subagents.

---

## 1. The Vibe Coding Delivery Loop

To move fast while preserving architectural integrity across blueprints, services, and pipelines, follow the four-step delivery loop:

1. **Explore & Plan (Workhorse / Pro):** Align on schema, service contracts, and blueprint boundaries before writing code.
2. **Build & Iterate (Workhorse):** Implement surgical changes inside `routes/`, `services/`, or `pipeline_v2/`.
3. **Audit & Verify (Ultra-Budget Subagents):** Run `@reviewer` (architectural invariant check) -> `@tester` (standardized `unittest` suite) -> `@scribe` (in-session specs & local commit).
4. **Ship & Close (Gated Subagents):** Run `@deploy_assistant` (builds container, pauses for human approval, deploys to Cloud Run, verifies live HTTP health) and `@session_closer` when finishing a build session.

---

## 2. Model Tiering & Cost Strategy

| Tier | Model ID | Cost / Token Weight | When to Use in SpinSleeve |
| :--- | :--- | :--- | :--- |
| **Ultra-Budget Lite** | `gemini-3.1-flash-lite`<br>`gemini-2.5-flash-lite` | **~10–20% of Flash**<br>(Ultra-cheap, fast) | • All 5 specialized subagents (`@reviewer`, `@tester`, `@scribe`, `@deploy_assistant`, `@session_closer`)<br>• Running `unittest` suites & git diffs<br>• Updating markdown docs & code formatting |
| **Workhorse (Default)** | `gemini-3.8-flash`<br>`gemini-3.5-flash` | **Standard**<br>(Fast tool calling & reasoning) | • Writing Flask blueprints (`src/report_v2/routes/*.py`)<br>• Crafting service layers (`src/report_v2/services/*.py`) & ETL (`sync.py`, `enrich.py`)<br>• Frontend Jinja2/CSS/JS tactile UI interactions |
| **Deep Reasoning** | `gemini-2.5-pro`<br>`gemini-3.1-pro-preview` | **Pro Tier**<br>(High depth, higher cost) | • Architectural redesigns & multi-service refactors<br>• Multi-tenant security & BigQuery partition optimization<br>• Complex algorithmic design (e.g., acoustic affinity) |

---

## 3. Dynamic Model Switching

```bash
# Switch to cheap model for routine edits:
/model set gemini-3.1-flash-lite

# Switch back to workhorse model for feature coding:
/model set gemini-3.8-flash

# Persist default model across restarts:
/model set gemini-3.8-flash --persist
```

---

## 4. Specialized Project Subagents (`.gemini/agents/`)

Subagents execute in isolated context loops on `gemini-3.1-flash-lite` so long test tracebacks, build logs, and diffs never bloat your main session context.

| Subagent | Role & Gate | Example Prompt |
| :--- | :--- | :--- |
| **`@reviewer`** | Audits `git diff` against `GEMINI.md` invariants, blueprint/service boundaries, and module docstrings. | `@reviewer audit my uncommitted changes before I run tests` |
| **`@tester`** | Runs `.venv/bin/python3 -m unittest discover tests`, diagnoses tracebacks, and writes unit tests. | `@tester run the full test suite and verify cache invalidation` |
| **`@scribe`** | Updates `TECHNICAL_SPECS.md` / `PROJECT_ROADMAP_AND_SPECS.md` and creates local Conventional Commits (never pushes). | `@scribe update TECHNICAL_SPECS.md and stage/commit my changes` |
| **`@deploy_assistant`** | Runs tests, submits Cloud Build, **pauses for human sign-off**, deploys to Cloud Run, pushes to GitHub, and curls `/` & `/beta/`. | `@deploy_assistant build and prepare production release` |
| **`@session_closer`** | Triggered by **"close the build session"**: verifies `APP_VERSION` in `app_config.py`, syncs `CHANGELOG.md` & `GEMINI.md` ledger, **pauses before `git push`**. | `close the build session` |

---

## 5. Context Hygiene (`.geminiignore`)

`.geminiignore` excludes `.venv/`, `__pycache__/`, `.pytest_cache/`, `.git/`, `.env`, and temporary artifacts so file searches stay fast and cheap. Restart Gemini CLI after editing `.geminiignore`.

---

## 6. Fast Developer Cheatsheet

```bash
# Run full standardized unit test suite:
.venv/bin/python3 -m unittest discover tests

# Run a single test module:
.venv/bin/python3 -m unittest tests/test_normalized_plays.py

# Run modular web app locally (visit http://localhost:8080/dev/auto-auth for dev bypass):
.venv/bin/python3 src/report_v2/app.py

# Inspect uncommitted changes:
git status && git diff HEAD
```
