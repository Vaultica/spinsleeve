# SpinSleeve: Project Memory & Architectural Constitution

Automatically loaded by Gemini CLI at session start. Defines non-negotiable architectural invariants, module boundaries, and active project state. Historical release notes live in `CHANGELOG.md`.

---

## 1. Project Overview & Environments

* **Application:** **SpinSleeve** — Virtual vinyl crate, 12" gatefold archival reader, listening telemetry engine, and friend-to-friend taste compatibility platform.
* **Production URL:** `https://spinsleeve.cc` (routes `/**` via Firebase Hosting `secret-compass-181513` to Cloud Run `spotify-dashboard-beta`; `/beta/*` routes remain backwards-compatible).
* **GCP Project:** `secret-compass-181513` | **Compute:** `europe-west2` | **BigQuery:** `US` (`spotify_v2`) | **Vault & Cache:** Cloud Datastore (`User`, `UserCatalogCache`, `PalCompatibilityCache`, `UserAnalyticsCache`).

---

## 2. Non-Negotiable Architectural Invariants

1. **Strict Layer & Blueprint Separation:**
   - Flask route blueprints (`src/report_v2/routes/*.py`) MUST ONLY handle HTTP request/response parsing, session checks, and template/JSON rendering.
   - Route handlers MUST NEVER import BigQuery or Datastore clients directly; all data access and business logic live in `src/report_v2/services/*.py`.
2. **Multi-Tenancy & BigQuery Cost/Partition Guardrails:**
   - Every query or DML operation on tenant tables (`playback_history`, `user_saved_albums`, `user_albums_features_table`) MUST filter and cluster by `user_id`.
   - Album title joins MUST use composite key `(LOWER(TRIM(album_name)), LOWER(TRIM(artist_name)))`.
   - Shared metadata (`album_enriched_metadata`) is global across tenants keyed by `album_id`.
   - DML writes/merges to partitioned BigQuery tables MUST batch by year/partition (preventing `400 Too many partitions` errors) and set `maximum_bytes_billed` on ad-hoc/analytics queries.
3. **Cache Invalidation Discipline:**
   - Mutations that alter user library, scrobbles, or privacy settings (sync completion, GDPR upload, `/settings` toggles, `?clear_cache=1`) MUST explicitly invalidate affected Datastore cache keys (`UserCatalogCache`, `PalCompatibilityCache`, `UserAnalyticsCache`).
4. **Data Cleanliness & Zero `NaN`s:**
   - BigQuery/Pandas outputs MUST be sanitized via `safe_str()`, `safe_int()`, and `safe_float()`. Never serialize raw `NaN` or `NaT` into JSON responses.
5. **Session Cookie & OAuth PKCE:**
   - Flask session cookie MUST be named `__session` with `path="/"` (Firebase Hosting strips all other cookies).
   - Always instantiate `SpotifyOAuth(..., show_dialog=True)` to prevent cross-account token pollution.
6. **Admin Impersonation & Zero-Lockout:**
   - `/admin/assume/<id>` enforces the assumed user's permission flags while `admin_required` checks `session["admin_user_id"] in ADMIN_USER_IDS`. Locked views MUST render escape links to `/admin/revert` and `/admin`.
7. **SpinPals Privacy & Sync Pause Guards:**
   - New users default to `pals_opt_in: False`. `fetch_pals_directory()` strictly filters `pals_opt_in == True`.
   - `pipeline_v2/sync.py` MUST skip users where `sync_paused == True`.
8. **Python Module Headers & Modularity:**
   - Every `.py` file MUST begin with a module docstring stating its architectural purpose, responsibilities, and key exports. Keep modules focused (<400 lines where practical).

---

## 3. Modular Project Map

* **`src/report_v2/` (Cloud Run Web Application):**
  * `app.py`: Thin Flask entrypoint, middleware, error handlers, and blueprint registration.
  * `app_config.py`: Single source of truth for `APP_VERSION`, environment constants, `ADMIN_USER_IDS`, and static SVG/icon assets.
  * `routes/`: Modular Flask blueprints (`auth`, `crate`, `analytics`, `pals`, `admin`).
  * `services/`: Data access, BigQuery queries, Datastore caching, and recommendation/compatibility engines.
  * `templates/`: Jinja2 HTML views and shared navigation/audio components.
* **`src/pipeline_v2/` (Cloud Run Jobs):**
  * `sync.py`: Multi-tenant token refresh & incremental Spotify play/library sync into `spotify_v2`.
  * `enrich.py`: Wikipedia/Discogs scraper + NLP mood/genre classifier populating `album_enriched_metadata`.
* **`tests/`:** `unittest` suite covering invariants, caching, routes, and pipelines.
* **`.gemini/agents/`:** Specialized subagents (`reviewer`, `tester`, `scribe`, `deploy_assistant`, `session_closer`).
* **Docs:** `VIBE_CODING_MANUAL.md` (Agent Orchestration), `PROJECT_ROADMAP_AND_SPECS.md` (What/Why & Backlog), `TECHNICAL_SPECS.md` (Schemas/Contracts), `CHANGELOG.md` (Full Release History), `INFRASTRUCTURE_RUNBOOK.md` (DR & DDL).

---

## 4. Active State & Next Milestones

* **Current Production Release:** `v2.7.0` (Real-Time Admin Email Notifications via Resend (`OPS-03`), canonical album sibling deduplication, 66/66 tests passing).
* **Next Planned Milestone:** `Phase 7` — Cross-Platform Apple Music Library Onboarding (`APP-02`).

---

## 5. Standard Commands

```bash
# Run full unit test suite (standard across all agents)
.venv/bin/python3 -m unittest discover tests

# Trigger background Cloud Run jobs on-demand
gcloud run jobs execute spotify-v2-pipeline-job --region=europe-west2
gcloud run jobs execute spotify-v2-enrichment-job --region=europe-west2 --args="enrich.py,100"

# Fast test accounts in header
# Admin: sergebou | User: sarahboosch | Test: 31sevhztrcbajfcowsahl7z2p26q
```

---

## 6. Session Closure & Ledger (Last 3 Sessions)

When the user says **"close the build session"**, invoke `@session_closer` to verify `APP_VERSION` in `src/report_v2/app_config.py`, sync `CHANGELOG.md` and `PROJECT_ROADMAP_AND_SPECS.md`, log spend below, and push after confirmation.

| Release | Date | Turns | Est. Input | Est. Output | Est. Spend | Primary Deliverables |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`v2.6.5` (Pipeline Fix & Specs)** | 2026-11-17 | 12 | ~500,000 | ~10,000 | **~$0.04** | `INFRA-05` technical specs (`TECHNICAL_SPECS.md`), Cloud Run pipeline Dockerfile multi-context path fix (job green status), 100% album enrichment verification (2161/2161), 61/61 tests passing. |
| **`v2.6.6`** | 2026-11-18 | 22 | ~880,000 | ~16,500 | **~$0.07** | Canonical album sibling deduplication (`APP-14`), BigQuery backfill, admin session assume routing & logout cookie path fixes, 63/63 tests passing. |
| **`v2.7.0`** | 2026-11-19 | 10 | ~400,000 | ~10,000 | **~$0.03** | Real-Time Admin Email Notifications via Resend (`OPS-03`), auth notification integration, unit test suite, 66/66 tests passing. |

---

## 7. Agent Autonomy & Operational Workflow

* **Autonomous Code & Test Modifications:** 
  - The agent is fully authorized to edit source code (`src/`), test files (`tests/`), and configuration files directly when fulfilling user feature requests or bug fixes during active development sessions.
* **Gated Actions (Explicit Approval Required):**
  - **Live Deployments:** Pushing code/containers to Cloud Run (`gcloud run deploy`), Firebase Hosting, or production remotes requires explicit user sign-off.
  - **Data Changes:** Destructive BigQuery DML operations, schema migrations, or production Datastore modifications require prior user confirmation.
* **Validation Standard:**
  - Every code modification must be verified by running the unit test suite (`.venv/bin/python3 -m unittest discover tests`) to ensure all tests pass successfully prior to reporting completion.
