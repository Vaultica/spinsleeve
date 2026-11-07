# SpinSleeve: Vibe Coding Agent Manual

A quick-reference developer guide for vibe coding on **SpinSleeve** with Gemini CLI, optimizing token costs, dynamically switching models, and orchestrating specialized subagents.

---

## 1. The Vibe Coding Workflow

Vibe coding is about moving fast from idea to working software while letting the AI handle boilerplate, mechanical refactoring, and repetitive verification. 

To maintain quality and keep cloud costs lean, follow the three golden loops:
1. **Explore & Plan (High Reasoning):** Formulate architecture or schema changes before modifying code.
2. **Build & Iterate (Balanced Speed):** Implement surgical code changes with instant feedback.
3. **Verify & Document (Ultra-Budget):** Delegate test runs, git staging, and documentation updates to cheap subagents.

---

## 2. Model Tiering & Cost Strategy

| Tier | Model ID | Cost / Token Weight | When to Use in SpinSleeve |
| :--- | :--- | :--- | :--- |
| **Ultra-Budget Lite** | `gemini-3.1-flash-lite`<br>`gemini-2.5-flash-lite` | **~10–20% of Flash**<br>(Ultra-cheap, fast) | • Running test suites (`unittest` / `pytest`)<br>• Git commands (`git diff`, commit drafting)<br>• Updating markdown docs (`CHANGELOG.md`, `ROADMAP`)<br>• Code formatting and boilerplate |
| **Workhorse (Default)** | `gemini-3.8-flash`<br>`gemini-3.5-flash` | **Standard**<br>(Fast tool calling & reasoning) | • Writing Flask endpoints (`src/report_v2/app.py`)<br>• Crafting BigQuery SQL & Python ETL (`sync.py`, `enrich.py`)<br>• Frontend HTML/CSS/JS tactile UI interactions |
| **Deep Reasoning** | `gemini-2.5-pro`<br>`gemini-3.1-pro-preview` | **Pro Tier**<br>(High depth, higher cost) | • Architectural redesigns & major refactors<br>• Multi-tenant security & data boundary audits<br>• Complex algorithmic design (e.g. acoustic affinity) |

---

## 3. Dynamic Model Switching

You do not need to restart the CLI to change models. You can switch models dynamically right inside your active chat session.

### Quick Slash Commands
```bash
# 1. Directly switch to the cheap model before running tests or writing docs:
/model set gemini-3.1-flash-lite

# 2. Directly switch back to the workhorse model for coding:
/model set gemini-3.8-flash

# 3. Open the interactive model picker dialog:
/model

# 4. Make your model choice permanent across CLI restarts:
/model set gemini-3.8-flash --persist
```

### Launching with a Specific Model
```bash
# Start CLI with a specific model flag:
gemini -m gemini-3.8-flash

# Or set an environment variable in your shell profile (~/.zshrc):
export GEMINI_MODEL="gemini-3.8-flash"
```

---

## 4. Specialized Project Subagents (`.gemini/agents/`)

Subagents run in their own isolated context loops using their assigned model. Heavy token outputs (such as 2,000 lines of test traces or massive git diffs) stay compressed inside the subagent and do not inflate your main session history.

### The Team

#### 1. `@scribe` (`.gemini/agents/scribe.md`)
* **Assigned Model:** `gemini-3.1-flash-lite`
* **Role:** Documentation maintainer and Git commit specialist.
* **Example Prompts:**
  - `@scribe update CHANGELOG.md with our recent crate digger fix`
  - `@scribe stage the modified files and draft a conventional commit message`
  - `@scribe mark APP-06 as completed in PROJECT_ROADMAP_AND_SPECS.md`

#### 2. `@tester` (`.gemini/agents/tester.md`)
* **Assigned Model:** `gemini-3.1-flash-lite`
* **Role:** Test runner and regression investigator.
* **Example Prompts:**
  - `@tester run the test suite and confirm nothing broke`
  - `@tester run tests/test_crate_digger_polish.py and analyze the failure`
  - `@tester write a new test for the 30-day sort feature`

---

## 5. How to Add a New Subagent

To create another specialized subagent (e.g., a BigQuery SQL optimizer, CSS designer, or security auditor):

1. Create a markdown file under `.gemini/agents/<name>.md`.
2. Add the required YAML frontmatter:

```markdown
---
name: designer
description: Frontend CSS and UI aesthetics specialist for vinyl sleeves and animations.
model: gemini-3.1-flash-lite
temperature: 0.2
tools:
  - read_file
  - replace
  - write_file
  - grep_search
---

You are an expert CSS and UI styling specialist. 
Your focus is vinyl aesthetic polish, tailwind classes, tactile animations, and mobile responsiveness (<110px headers).
```

3. Save the file. The new agent is immediately available via `@designer` or autonomous delegation!

---

## 6. Context Hygiene (`.geminiignore`)

Every file read or searched consumes tokens. To keep sessions responsive and prevent bloated context windows:

* **Location:** `.geminiignore` in the project root.
* **What is ignored:** `.venv/`, `__pycache__/`, `.pytest_cache/`, `.git/`, `.env`, temporary logs, and build artifacts.
* **Adding rules:** Add patterns matching `.gitignore` syntax:
  ```text
  # Ignore heavy scratch directories or big datasets
  data/*.csv
  tmp/
  ```
* **Note:** When you update `.geminiignore`, restart your CLI session for changes to take full effect.

---

## 7. Fast Developer Testing Cheatsheet

* **Run all tests:**
  ```bash
  .venv/bin/python3 -m unittest discover tests
  ```
* **Run a single test file:**
  ```bash
  .venv/bin/python3 -m unittest tests/test_normalized_plays.py
  ```
* **Run web app locally with live auto-auth bypass (no Spotify login needed):**
  ```bash
  # Visit http://localhost:8080/dev/auto-auth for instant local admin session
  python3 src/report_v2/app.py
  ```
* **Check local git status & diff:**
  ```bash
  git status && git diff HEAD
  ```

---

## 8. Enhancing This Manual

This manual is meant to be a living document. In future sessions, you can tell Gemini:
> *"Update `VIBE_CODING_MANUAL.md` to add [new tip / subagent / shortcut]."*
