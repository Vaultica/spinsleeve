# SpinSleeve: Multi-Agent & Autonomous Build Guardrails (`AGENT_WORKFLOW_GUARDRAILS.md`)

Operational constitution for running single or parallel Gemini CLI agents in spec-driven, non-interactive sessions on **SpinSleeve** (`https://spinsleeve.cc`) without stepping on shared files, live databases, or production infrastructure.

---

## 1. Core Execution Rules for Autonomous / Non-Interactive Sessions

1. **Spec-Driven Entry:** Every coding session must bind to an explicit backlog ID (`APP-XX`, `POLISH-XX`, `INFRA-XX`, `OPS-XX`) defined in `PROJECT_ROADMAP.md` and `ROADMAP_TECHNICAL_SPECS.md`.
2. **Hard Command Prohibitions (Never Execute Unattended):**
   - **Live Deployments:** `gcloud run deploy`, `gcloud run jobs deploy`, `firebase deploy`, `gcloud scheduler jobs ...`
   - **Remote Git Mutations:** `git push`, `git push --force`, branch deletion on `origin`
   - **Destructive / Production Data Mutations:** `bq rm`, `DROP TABLE`, `TRUNCATE TABLE`, unbatched `DELETE`/`MERGE` on production `spotify_v2.*` tables, or writes/deletes against live Datastore `User`, `UserCatalogCache`, `PalCompatibilityCache`, or `UserAnalyticsCache` entities.
3. **Mandatory Local Validation:** Before reporting completion or opening a PR, the agent MUST pass:
   ```bash
   .venv/bin/python3 -m unittest discover tests
   ```

---

## 2. Parallel Worktree & File Ownership Discipline

When running multiple autonomous agents simultaneously:

1. **Git Worktree Isolation:**
   - Each agent operates in its own dedicated git worktree and branch:
     ```bash
     git worktree add ../spinsleeve-<feature-id> -b feat/<feature-id>-<slug>
     ```
2. **Forbidden Files in Feature Branches:**
   - Parallel branches **MUST NOT** modify shared release artifacts or global configuration files to prevent merge conflicts:
     - `CHANGELOG.md`
     - `src/report_v2/app_config.py` (`APP_VERSION`)
     - `firebase.json`
   - Version bumps and changelog synchronization are strictly reserved for the final integration/session closure phase.

---

## 3. Data, Schema & Cache Namespacing

To prevent parallel test runs or pipeline jobs from corrupting production BigQuery tables or shared Datastore caches:

1. **BigQuery Tables:**
   - Experimental pipelines, schema migrations, or backfills must write to feature-suffixed tables (e.g., `*_app_16`, `*_test_*`) rather than production tenant partitions unless explicitly testing live multi-tenancy.
2. **Datastore Caching:**
   - Unit tests must use mock Datastore client fixtures or isolated test tenant IDs to avoid invalidating live user analytics or pal compatibility caches.

---

## 4. Integration & Merge Protocol

1. **Rebase Before PR:**
   - Before requesting review or merging, rebase feature branches against `origin/master`:
     ```bash
     git fetch origin && git rebase origin/master
     ```
2. **Verification Gate:**
   - Run the full test suite (`.venv/bin/python3 -m unittest discover tests`) after rebasing and before signaling completion.

---

## 5. Roadmap Reconciliation & Session Closure Audit

1. **Mandatory Checklist Reconciliation:**
   - During session closure (`@session_closer`), agents **MUST** audit `CHANGELOG.md` and recent git commits against `PROJECT_ROADMAP.md`.
   - Every feature ID (`APP-XX`, `POLISH-XX`, etc.) completed during the session must have its corresponding status matrix row checked off (`✅ ~~...~~`) with the correct release tag before commit and push.
