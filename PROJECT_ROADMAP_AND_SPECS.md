# SpinSleeve: Architecture, Roadmap & Feature Backlog

**Production Domain:** `https://spinsleeve.cc`  
**Current GCP Project ID:** `secret-compass-181513` | **Compute Region:** `europe-west2` (London) | **BigQuery Region:** `US`

---

## 1. Executive Summary & Implemented Milestones

SpinSleeve transforms digital streaming libraries into physical-style virtual vinyl crates, delivering 12" gatefold archival liner notes, 30-second needle-drop preview snippets, deep listening telemetry, and friend-to-friend acoustic compatibility.

### ✅ Completed Implementation Phases

* **Phase 1: Multi-Tenant Data Foundation & User Vault**
  - BigQuery `spotify_v2` dataset with partitioned/clustered tables (`playback_history`, `user_saved_albums`) isolated by `user_id`. Universal shared `album_enriched_metadata` table.
  - Serverless Cloud Datastore `User` vault storing credentials, display names, avatars, approval gates, and offline OAuth refresh tokens.
  - Standalone `manage_users.py` administrative CLI.
* **Phase 2: Spotify OAuth 2.0 PKCE & Beta Routing**
  - Multi-user PKCE authorization code flow with dynamic callback URI resolution (`https://spinsleeve.cc/callback`, `/beta/callback`) and `show_dialog=True` account chooser enforcement.
  - Firebase CDN reverse proxy preserving `__session` cookies at `path="/"`.
  - Automatic 50-track and 50-album background ingestion on first approved login.
* **Phase 3: Feature Parity & Smart Crate Digger**
  - 30-second audio preview snippets on card hover and gatefold modals with animated soundwaves.
  - Smart Crate Digger (`/recommend`): Algorithmic discovery engine with vibe (*Late Night/Chill, Energetic, Mellow, Vintage*), era, and subgenre filters.
  - Listening Telemetry (`/analytics`): Dynamic timeframes (24h, 7d, 30d, 60d, 90d, This Year, All Time, Custom range), listening clock heatmaps, and taste velocity.
* **Phase 4: Automated Multi-Tenant Pipeline**
  - Cloud Run Job `spotify-v2-pipeline-job` refreshing tokens and ingesting telemetry across all approved users.
  - Cloud Scheduler `spotify-v2-sync-scheduler` executing every 2 hours via OIDC service account authentication.
* **Phase 5a: SpinPals Social (CrateMates Edition)**
  - The Listening Lounge community directory with active member avatars and record counts.
  - Hybrid acoustic chemistry gauge (50% artist overlap + 50% album overlap) with kinship badges (*Vinyl Soulmates, Acoustic Kin, Crate Companions*).
  - Algorithmic Top 5 borrow recommendations and virtual crate digging with `🤝 Both Own` comparison tags.
* **Phase 5b: Pre-Production Gatefold & Admin Polish**
  - Compact mobile header (`<110px`) eliminating vertical scrolling on screens `<768px`.
  - Interactive 30-second needle-drop audio progress scrubber with mouse/touch seeking and timestamp display.
  - Archival deep links to original Pitchfork reviews, Discogs release pressings, and Wikipedia entries.
  - Direct Apple Music universal app deep links.
  - SpinPals social privacy gate (disabled by default for new users; admin opt-in).
  - Admin identity assumption (`/admin/assume/<id>`) with persistent `↩ Revert` banner and zero-lockout protection.
  - Restored authentic 33⅓ RPM spinning turntable Spotify logo across all views and dynamic `/favicon.svg`.
* **Phase 6: Production Cutover & Live Deployment**
  - Zero-downtime Firebase CDN rewrite flip pointing root domain `https://spinsleeve.cc` to the multi-tenant V2 application.
  - Symmetrical root URL routing (`/`, `/recommend`, `/analytics`, `/pals`, `/admin`, `/login`, `/logout`) with full backward compatibility for `/beta/*`.
  - Paused legacy single-user Cloud Scheduler `spotify-daily-sync`.
* **Phase 6b: Tactical Sleeve Polish (`APP-05`)**
  - Normalized album spins calculation $\lfloor \text{track\_plays} / \text{tracks\_total} \rfloor$ with zero-track fallback.
  - Tactile `🔥 X Plays` (and `🔥 1 Play`) sleeve badges across Library Explorer, Crate Digger (spotlight & pool), and SpinPals (Top Borrow & crate).
  - Hover tooltips detailing complete breakdown: *"Estimated complete album spins based on {P} track plays across {T} tracks"*.
  - Normalized play count sorting in Library Explorer with raw scrobbles tiebreaker.
  - Deployed live revision `spotify-dashboard-beta-00018-c67`.
* **Phase 6c: Dynamic Time Horizon (`APP-06`)**
  - Updated BigQuery view `user_albums_features` with single-pass conditional aggregation (`COUNTIF`) for rolling 30-day metrics (`album_track_plays_30d`, `album_plays_30d`).
  - Interactive 2-way horizon switcher in Crate Digger (`🔥 Heavy Rotation (Last 30 Days)` vs `🏛️ All-Time Collection`), tuning recommendation weights and candidate pools.
  - Dynamic time horizon toggle in SpinPals Top 5 to Borrow (`?horizon=30d` vs `?horizon=all_time`), highlighting pal's current obsessions this month.
  - Added `🔥 Heavy Rotation (Last 30 Days)` sorting in Library Explorer with dynamic 30D badge display.
  - Deployed live revision `spotify-dashboard-beta-00019-9ds`.
* **Phase 6d: Materialized High-Performance Analytical Table (`INFRA-03a`)**
  - Created clustered physical table `secret-compass-181513.spotify_v2.user_albums_features_table` (`CLUSTER BY user_id`), replacing dynamic view compilation with pre-computed reads (2.3x query speedup).
  - Added automated re-materialization step in `src/pipeline_v2/sync.py` (`rematerialize_user_albums_features`).
  - Switched `src/report_v2/app.py` queries in `fetch_user_album_data` and `compute_pal_compatibility` to the physical clustered table.
  - Deployed live revision `spotify-dashboard-beta-00020-vrw`.
* **Phase 6e: Cloud Datastore Document Store Catalog Cache (`INFRA-03b`)**
  - Integrated Tier 2 Cloud Datastore document cache (`UserCatalogCache`) with gzip compression (7.5x compression ratio, 324 KB compressed for 1,825 albums).
  - Reduced cold catalog load latency from ~3,800ms down to **~50ms** (70x speedup) at $0 additional cost.
  - Added automatic cache invalidation in `src/pipeline_v2/sync.py` when new listening events or saved albums are ingested.
  - Added unit test suite in `tests/test_datastore_cache.py` (42/42 tests passing).
  - Deployed live revision `spotify-dashboard-beta-00021-42p`.
* **Phase 6f: Header Polish & Semantic Release Versioning (`POLISH-04`, `POLISH-05`)**
  - Removed static "beta v2" badge, replaced with dynamic `APP_VERSION = "v2.2.0"` globally injected via Flask context processor.
  - Standardized user profile widget in global navigation header with normal user avatar and display name across all views.
  - Removed admin user-switcher clutter (`👑 Serge`, `👩 Sarah`, `🐹 GuineaPig`) from header, keeping impersonation strictly housed inside `/admin` with clear `↩ Revert` escape button.
  - Deployed live revision `spotify-dashboard-beta-00022-z5t`.

---

## 2. Product & Engineering Backlog (By Category)

Features are indexed with unique alphanumeric category codes. Prioritization and release scheduling will be assigned across subsequent phases.

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │ FEATURE CATEGORIES & CODES                                             │
 ├────────────────────────────────────────────────────────────────────────┤
 │ [INFRA]  Infrastructure & Cloud Architecture                           │
 │ [OPS]    DevOps, CI/CD, Reliability & Observability                    │
 │ [APP]    Music Digging, 12" Gatefolds & Cross-Platform Streaming       │
 │ [POLISH] Tactical Polish, UX Streamlining & Quick Fixes               │
 │ [BRAND]  Brand Identity, Public Landing & Monetization                 │
 │ [DOCS]   Architecture Mapping & Documentation                          │
 └────────────────────────────────────────────────────────────────────────┘
```

### Summary Feature Index

| Code | Title | Category | Estimated Effort | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **`INFRA-01`** | Fresh GCP Project Migration & Environment Isolation | Infrastructure | 6–8 hours | Medium |
| **`INFRA-02`** | Declarative Infrastructure as Code (IaC) via Terraform | Infrastructure | 8–12 hours | Medium |
| **`INFRA-03`** | Sub-100ms Multi-Tier Caching & BQ Materialization Architecture | Infrastructure | 6–8 hours | In Progress (Phase 6e Live: Revision `00021-42p`) |
| **`OPS-01`** | CI/CD Pipelines via GitHub Actions & Branch Protection | DevOps | 6–8 hours | Medium |
| **`OPS-02`** | Production Observability, Alerting & Health Monitoring | DevOps | 4–6 hours | Low–Med |
| **`OPS-03`** | Real-Time Admin Alerts for User Join Requests | DevOps | 3–4 hours | Low |
| **`APP-01`** | 12" Gatefold Tracklisting & Side A / Side B Breakdown | Core App | 4–6 hours | Low–Med |
| **`APP-02`** | Cross-Platform Apple Music Library Onboarding (Phase 7) | Core App | 16–24 hours | Medium |
| **`APP-03`** | In-App Feedback & Liner Notes Wishlist Collector | Core App | 5–7 hours | Low–Med |
| **`APP-04`** | Music Legend Illustrated Avatar Persona Picker | Core App | 4–5 hours | Low |
| **`APP-05`** | ✅ ~~Album Sleeve Normalized Play Count Badge ("🔥 X Plays")~~ | Core App | 2–3 hours | Completed (Revision `00018-c67`) |
| **`APP-06`** | ✅ ~~Crate Digger & SpinPals "Top Pick" Horizon (30D vs. All Time)~~ | Core App | 5–7 hours | Completed (Revision `00019-9ds`) |
| **`APP-07`** | Played But Not Owned ("You Should Save These") Library Crate | Core App | 4–6 hours | Low–Med |
| **`APP-08`** | Full-Length Virtual Turntable Player (Spotify Web Playback SDK) | Core App | 8–12 hours | Medium |
| **`APP-09`** | Granular Track-Level Telemetry & Audio Archive | Core App | 6–8 hours | Medium |
| **`APP-10`** | Local Gig Radar: Top Artists Live in Your City (Bandsintown API) | Core App | 6–8 hours | Medium |
| **`APP-11`** | Collector’s Inscriptions: Personal Album Ratings & Archival Notes | Core App | 5–7 hours | Low–Med |
| **`APP-12`** | Header Profile Dropdown, User Settings & Community Action Center | Core App | 3–4 hours | Low |
| **`POLISH-01`** | ✅ ~~Harmonise "Heavy Rotation" Filter & Simplify Crate Digger~~ | Tactical Polish | 2–3 hours | Completed (`v2.2.1`) |
| **`POLISH-02`** | [Fix] Library Explorer Heavy Rotation Initial Sort (Strict 30D on Load) | Tactical Polish | 1 hour | Low |
| **`POLISH-03`** | Play Count Badge Refinement (Decimal Plays / Newly Added) | Tactical Polish | 1–2 hours | Low |
| **`POLISH-04`** | ✅ ~~Semantic Build Versioning (Replace "beta v2" with Version)~~ | Tactical Polish | 1–2 hours | Completed (`v2.2.0`: Revision `00022-z5t`) |
| **`POLISH-05`** | ✅ ~~Clean Header Profile Avatar (Remove Admin Switcher from Header)~~ | Tactical Polish | 1–2 hours | Completed (Revision `00022-z5t`) |
| **`POLISH-06`** | Admin Portal Table Column Alignment & Layout Polish | Tactical Polish | 1–2 hours | Low |
| **`POLISH-07`** | ✅ ~~De-duplicate Crate Digger "Spin Again" Header Button~~ | Tactical Polish | 0.5 hours | Completed (`v2.2.1`) |
| **`BRAND-01`** | Homepage & Public Login Redesign with Feature Showcase | Brand & Growth | 6–8 hours | Low–Med |
| **`BRAND-02`** | "Buy Me a Coffee" Supporter Integration | Monetization | 1–2 hours | Low |
| **`BRAND-03`** | Public Roadmap & Release Transparency Portal (`/roadmap`) | Brand & Growth | 3–4 hours | Low |
| **`BRAND-04`** | ✅ ~~Software License & IP Protection Review (PolyForm Noncommercial 1.0.0)~~ | Legal & Brand | 2–4 hours | Completed (`v2.2.2`) |
| **`DOCS-01`** | Comprehensive Technical Project Architecture Map (README) | Documentation | 3–4 hours | Low |

---

## 3. Detailed Feature Specifications

> 💡 **Architectural Decoupling Notice:**  
> This roadmap articulates the **WHAT** and **WHY** (user stories, feature scope, product rationale, and effort).  
> For the comprehensive, deep-dive system architecture, database schemas, API contracts, and implementation blueprints (**HOW**), refer to [**`TECHNICAL_SPECS.md`**](./TECHNICAL_SPECS.md).

### 🏛️ Category: Infrastructure & Cloud Architecture (`INFRA`)

#### `INFRA-01`: Fresh GCP Project Migration & Clean Isolation
* **Problem:**  
  The current GCP project (`secret-compass-181513`) contains obsolete artifacts, leftover resources from unrelated pet projects, ambiguous IAM roles, and shared quotas. A pristine, production-grade cloud boundary is required for security, clean billing, and proper asset ownership.
* **Solution:**  
  Provision a dedicated Google Cloud project (e.g., `spinsleeve-prod` or `spinsleeve-app`) and migrate all multi-tenant services with zero data loss:
  1. **Project Provisioning:** Enable Cloud Run, BigQuery, Cloud Datastore (Firestore in Datastore mode), Secret Manager, Cloud Build, Cloud Scheduler, and Artifact Registry.
  2. **Data Migration:** Export Datastore `User` entities and BigQuery `spotify_v2` tables to Cloud Storage bucket (`gs://...`), then restore into the target project.
  3. **Secret Provisioning:** Store `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, and `FLASK_SECRET_KEY` in new project's Secret Manager.
  4. **Compute Deployment:** Build and deploy `spotify-dashboard-beta` (or `spotify-dashboard-service`) and `spotify-v2-pipeline-job`.
  5. **Domain Switch:** Connect `spinsleeve.cc` custom domain in Firebase Hosting on the new project, update DNS A/AAAA records, and verify SSL issuance.
* **Effort & Complexity:** ~6–8 hours (1 day) • **Complexity:** **Medium**

---

#### `INFRA-02`: Declarative Infrastructure as Code (IaC) via Terraform
* **Problem:**  
  Cloud resources are currently provisioned through manual console actions and ad-hoc shell commands, making disaster recovery, auditing, and environment replication time-consuming.
* **Solution:**  
  Author modular Terraform declarations in `/terraform` covering all cloud assets:
  - `modules/cloud_run`: Cloud Run service definitions (concurrency, memory/CPU limits, environment variables).
  - `modules/cloud_run_job`: Ingestion job and Cloud Scheduler cron triggers with OIDC service accounts.
  - `modules/bigquery`: Dataset `spotify_v2`, partition expiration rules, clustering keys, and views.
  - `modules/datastore`: Datastore index definitions (`index.yaml`).
  - `modules/secrets`: Secret Manager resource definitions (with placeholder values).
  - `modules/iam`: Least-privilege service accounts (`spinsleeve-app-sa`, `spinsleeve-pipeline-sa`).
  - `backend.tf`: Remote state storage in a locked GCS bucket with state locking.
* **Effort & Complexity:** ~8–12 hours (1.5 days) • **Complexity:** **Medium**

---

#### `INFRA-03`: Sub-100ms Multi-Tier Caching & BigQuery Materialization Architecture
* **Problem:**  
  Navigating between tabs (`/`, `/recommend`, `/analytics`, `/pals`) incurs 2–4s latency on cache misses because:
  - Cloud Run instances scale to zero when idle, discarding in-memory cache (`CACHE_TTL = 60s`).
  - BigQuery has an inherent analytical query latency floor (~1.2s to 2.5s) and dynamically executes complex CTEs, window functions (`ROW_NUMBER`), and joins on every uncached evaluation of `user_albums_features`.
  - Every tab navigation is a full multi-page application (MPA) reload that re-transfers ~1.5 MB of embedded HTML/JSON.
  - SpinPals (`/pals`) executes three separate BigQuery queries sequentially on cache misses.
* **Solution (Zero Added Monthly Cloud Cost):**  
  Implement a four-tier caching and storage hierarchy bypassing BigQuery query-time compilation without requiring expensive managed Redis ($50–70/mo) or Cloud SQL ($25–40/mo):
  1. **BigQuery Table Materialization:** In `sync.py` and enrichment jobs, write the output of `user_albums_features` into a clustered physical table (`user_albums_features_table` clustered by `user_id`), cutting BigQuery scan latency from ~2.5s down to ~600ms.
  2. **Cloud Datastore Document Store (`UserCatalogCache`):** Store pre-serialized user album catalogs and KPIs directly in Google Cloud Datastore entities (`UserCatalogCache`) with a 24-hour TTL, invalidated automatically upon pipeline sync completion. Document fetch latency drops from 2,500ms to **~15–25ms** at $0 additional cost (within Datastore's 50,000 free daily reads).
  3. **SpinPals Multi-Query Consolidation & Pal Caching:** Consolidate the 3 sequential BigQuery queries in `compute_pal_compatibility` into a single query and cache pal compatibility payloads in Datastore.
  4. **Browser Session Storage & Client-Side Navigation:** Cache user catalog payloads in browser `sessionStorage` and introduce `/api/user/catalog`. Cross-tab switches between Library Explorer and Crate Digger render instantaneously (<10ms) without re-transferring full HTML documents.
* **Effort & Complexity:** ~6–8 hours (1 day) • **Complexity:** **Medium**

---

### 🚀 Category: DevOps, CI/CD, Reliability & Observability (`OPS`)

#### `OPS-01`: CI/CD Pipelines via GitHub Actions & Branch Protection
* **Problem:**  
  Deployments currently depend on manual execution from local terminals (`gcloud builds submit`, `firebase deploy`), risking inconsistent local dependencies and untested commits directly to `master`.
* **Solution:**  
  Implement automated GitHub Actions workflows with strict branch protection:
  1. **Continuous Integration (`.github/workflows/ci.yml`):**
     - Triggers on pull requests targeting `master`.
     - Sets up Python 3.10 and 3.11 matrices.
     - Runs code compilation (`py_compile`), style checks (`ruff` / `flake8`), and executes the complete `unittest` suite in `tests/`.
     - Blocks merge if any check fails.
  2. **Continuous Deployment (`.github/workflows/deploy.yml`):**
     - Triggers automatically upon merge to `master`.
     - Authenticates to GCP via **Workload Identity Federation** (eliminating downloaded JSON service account keys).
     - Submits container build to Google Cloud Build, deploys revision to Cloud Run, and deploys Firebase Hosting rewrites.
  3. **Repository Security:** Enforce branch protection on `master` (require pull request reviews, require linear history, disallow force-pushes).
* **Effort & Complexity:** ~6–8 hours (1 day) • **Complexity:** **Medium**

---

#### `OPS-02`: Production Observability, Alerting & Health Monitoring
* **Problem:**  
  If Cloud Run encounters memory exhaustion, Spotify API quota limits are hit, or background sync jobs fail, administrators only discover issues via user complaints.
* **Solution:**  
  Establish an observability and automated alerting baseline in Google Cloud Monitoring:
  1. **Cloud Run Health Metrics:** Track request latency (p95 > 2s), container CPU utilization (>80%), and memory consumption (>85%).
  2. **Error Rate Alerting:** Automated incident policy triggered if HTTP 5xx responses exceed 2% over a rolling 5-minute window.
  3. **Job Failure Detection:** Alert on non-zero exit codes from `spotify-v2-pipeline-job`.
  4. **Health Check Endpoint:** Add `@app.route("/healthz")` validating BigQuery query execution and Datastore client read availability.
  5. **Notification Channels:** Automated alert dispatches to `serge.bouschet@gmail.com` and optional Discord/Slack operational webhook.
* **Effort & Complexity:** ~4–6 hours (0.5 day) • **Complexity:** **Low–Medium**

---

#### `OPS-03`: Real-Time Admin Alerts for User Join Requests
* **Problem:**  
  When an uninvited user logs in for the first time, their account sits in `PENDING` state until the admin happens to inspect the Admin Control Deck.
* **Solution:**  
  Instant notifications pushed directly to Serge whenever a new Spotify user authenticates:
  - **Channels:** Telegram Bot API webhook or Discord Webhook.
  - **Payload:** User display name, Spotify ID, email, profile avatar, and a 1-click approval URL:
    ```text
    📢 New SpinSleeve Member Request!
    • Name: Charlie Watts
    • Spotify ID: charliewatts123
    • Email: charlie@rollingstones.com
    👉 Approve: https://spinsleeve.cc/admin
    ```
* **Effort & Complexity:** ~3–4 hours (0.5 day) • **Complexity:** **Low**

---

### 🎵 Category: Music Digging, 12" Gatefolds & Streaming (`APP`)

#### `APP-01`: 12" Gatefold Tracklisting & Side A / Side B Disc Breakdown
* **Problem:**  
  The gatefold modal provides rich narrative liner notes and personnel rosters, but lacks the tracklist—the core structural element of a vinyl record sleeve.
* **Agreed Architectural Design (Hybrid Model & Option A):**
  1. **Primary Structural Source (Spotify Web API `sp.album_tracks(album_id)`):**
     - Fetch exact track sequence, titles, durations (`duration_ms`), explicit flags, and Spotify track URIs (`spotify:track:...`) using existing `album_id`.
     - Direct technical alignment with upcoming turntable player (`APP-08`).
  2. **Storage & Caching (Option A - On-Demand Datastore Cache):**
     - Dedicated endpoint: `/api/album/<album_id>/tracks`
     - On first open of an album's gatefold modal, fetch from Spotify API, compute vinyl sides, and cache in Cloud Datastore (`AlbumTracksCache`, shared across all tenants) with a 30-day TTL. Sub-50ms subsequent loads with zero BQ migrations.
  3. **Physical Vinyl Splitting Algorithm:**
     - **Single Disc (`disc_count == 1`):** Split $N$ tracks into Side A ($1 \dots \lceil N/2 \rceil$) and Side B ($\lceil N/2 \rceil + 1 \dots N$).
     - **Multi-Disc (`disc_count >= 2`):** Map Disc 1 to Side A / Side B, Disc 2 to Side C / Side D.
  4. **Inline Needle-Drop Auditioning:**
     - Clicking any track name audits that track's 30s snippet using Spotify `preview_url` or falling back to `/api/preview?artist=...&track=...` via iTunes.
* **Effort & Complexity:** ~4–6 hours (0.5 to 1 day) • **Complexity:** **Low–Medium**

---

#### `APP-02`: Cross-Platform Apple Music Library Onboarding (Phase 7)
* **Problem:**  
  Many music lovers stream on Apple Music, and Spotify's 25-user development allowlist artificially restricts SpinSleeve's growth.
* **Solution:**  
  Full Apple Music onboarding allowing Apple Music subscribers to import their collection into SpinSleeve:
  1. **MusicKit JS v3:** Client-side authentication popup (`music.authorize()`) yielding `Music-User-Token`.
  2. **Developer Token Minting:** Automated ES256 JWT generation using Apple Developer Private Key (`.p8`) from Secret Manager.
  3. **Library Sync:** Ingest user saved albums via `GET /v1/me/library/albums` into BigQuery `spotify_v2.user_saved_albums`.
  4. **Cross-Platform Crate Digging:** Enable shared vinyl comparison and acoustic kinship calculation between Spotify and Apple Music users.
* **Effort & Complexity:** ~16–24 hours (2–3 days) • **Complexity:** **Medium**

---

#### `APP-12`: Header Profile Dropdown, User Settings & Community Action Center
* **Problem:**  
  Because SpinSleeve features endless scrolling catalogs, traditional bottom footers are rarely seen. Important user controls (SpinPals opt-in/out, nickname editing, scrobble collection pause) and community touchpoints (Roadmap, GitHub, Feedback, Buy Me a Coffee) need to be accessible instantly from anywhere in the app.
* **Solution:**  
  Redesign the top-right user profile avatar into an interactive, sleek dropdown menu (`bg-neutral-900 border border-neutral-800 rounded-xl shadow-2xl`):
  1. **User Identity & Status:** Displays avatar, display name, and admin badge if applicable.
  2. **User Settings & Privacy Toggles:**
     - 🤝 **SpinPals Opt-In / Opt-Out:** Toggle presence in the Listening Lounge directory (`pals_opt_in`).
     - ✏️ **Custom Display Name / Nickname:** Edit how your name appears to CrateMates.
     - ⏸️ **Pause Scrobble Sync:** Temporarily opt-out of automated playback history ingestion.
  3. **Community & Support Center:**
     - 🗺️ Link to `/roadmap`.
     - 🐙 Link to GitHub repository.
     - 💬 In-app Feedback drawer trigger.
     - ☕ **"Buy Me a Coffee"** Supporter integration modal/link (`BRAND-02`).
  4. **Session Controls:** 1-click Logout (and Admin Revert if impersonating).
* **Effort & Complexity:** ~3–4 hours (0.5 day) • **Complexity:** **Low**

---

#### `APP-03`: In-App Feedback & Liner Notes Wishlist Collector
* **Problem:**  
  Friends testing SpinSleeve need a quick, seamless way to suggest missing liner notes, report bugs, or recommend features without leaving the application.
* **Solution:**  
  A built-in floating drawer (`💬 Feedback`):
  - Form categories: `🐛 Bug Report`, `✨ Feature Request`, `💿 Liner Notes Request`, `❤️ Love`.
  - Captures user context automatically (user ID, browser agent, active route).
  - Stores submissions in Datastore (`Feedback` kind), managed via a triage dashboard in `/admin`.
* **Effort & Complexity:** ~5–7 hours (1 day) • **Complexity:** **Low–Medium**

---

#### `APP-04`: Music Legend Illustrated Avatar Persona Picker
* **Problem:**  
  Users without custom Spotify profile pictures need recognizable, stylized artistic personas inside the vinyl club.
* **Solution:**  
  Curated illustrated vector avatars of musical legends:
  - ⚡ David Bowie (*Aladdin Sane lightning bolt*)
  - 🕶️ The Beatles (*Abbey Road silhouettes*)
  - 🎹 Wolfgang Amadeus Mozart (*Classical wig*)
  - 🐝 Beyoncé (*Renaissance disco hat*)
  - 🕶️ Miles Davis (*Trumpet silhouette*)
  - 🎤 Amy Winehouse (*Beehive & eyeliner*)
  - Stored as `custom_avatar_id` in Datastore `User` entity.
* **Effort & Complexity:** ~4–5 hours (0.5 day) • **Complexity:** **Low**

---

#### `APP-05`: Album Sleeve Normalized Play Count Badge ("🔥 X Plays") [✅ Completed]
* **Problem:**  
  Currently, virtual vinyl album sleeves display a bare, uncontextualized number badge (e.g., `42`) in the top-right corner. Listeners cannot discern what this number measures—individual track scrobbles or full album spins—diminishing the visual storytelling of personal vinyl listening history.
* **Solution:**  
  Update album sleeve badges across all views (Library Explorer, Crate Digger, SpinPals) to display clear, tactile play metrics:
  1. **Visual Badge:** Styled pill with flame icon and contextual label: `🔥 {album_plays} Plays` (or `🔥 1 Play`).
  2. **Normalized Album Plays Calculation:** Calculate full album spins by dividing total user scrobbles for that album by the album's track count:  
     $$\text{Album Plays} = \left\lfloor \frac{\text{Total Track Scrobbles}}{\text{Total Tracks in Album}} \right\rfloor$$  
     *(Fallback: If total tracks is unavailable or zero, use track scrobbles with a clear tooltip).*
  3. **Tooltip Detail:** Hover tooltip explaining: *"Estimated complete album spins based on {total_track_plays} track plays across {track_count} tracks"*.
* **Effort & Complexity:** ~2–3 hours (0.5 day) • **Complexity:** **Low**

---

#### `APP-06`: Crate Digger & SpinPals "Top Pick" Time Horizon (Heavy Rotation 30D vs. All Time) [✅ Completed]
* **Problem:**  
  In both Crate Digger (`/recommend`) and SpinPals (`/pals`), "Top Pick" recommendations and borrow candidates currently rank records solely against lifetime aggregate scrobbles. Because all-time play counts are cumulative and slow to change, the spotlight repeatedly surfaces the same static records week after week, failing to reflect what users and their friends are actively obsessing over right now.
* **Solution:**  
  Introduce an interactive time horizon toggle for recommendations with an active rotation bias:
  1. **Time Horizon Controls:** A 2-way segmented pill toggle:
     - 🔥 **Heavy Rotation (Last 30 Days)** *(Default)*: Evaluates scrobbles within the rolling past 30 days (`played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)`). Surfaces fresh, high-velocity records currently on repeat.
     - 🏛️ **All Time**: Evaluates lifetime scrobble counts, honoring long-term cornerstone albums.
  2. **Crate Digger Application:** Ranks spotlight selections (`🥇 Prime Selection`, `🥈 Vibe Match`, `🥉 Hidden Gem`) and candidate crates against the selected horizon.
  3. **SpinPals Application:** Recalculates friend borrow recommendations (`top_borrow`) using the pal's 30-day heavy rotation, allowing friends to borrow what the other is currently spinning rather than albums listened to years ago.
  4. **Query & Backend Optimization:** Fetch 30-day play counts alongside all-time counts in BigQuery query aggregation in `fetch_user_album_data` without adding redundant roundtrips.
* **Effort & Complexity:** ~5–7 hours (1 day) • **Complexity:** **Low–Medium**

---

#### `APP-07`: Played But Not Owned ("You Should Save These") Library Crate
* **Problem:**  
  Listeners frequently stream albums or tracks they love, but haven't formally clicked "Save Album" in Spotify. Because SpinSleeve's primary Library Explorer defaults strictly to `user_saved_albums`, high-affinity played albums remain hidden unless searched or discovered through Analytics scrobble history.
* **Solution:**  
  Introduce an unowned crate view / filter inside the Library Explorer ("You Should Save These"):
  1. **BigQuery Query Aggregation:** Identify albums present in `playback_history` for `user_id` with significant listening activity (e.g., $\ge 3$ scrobbles or $\ge 1$ full normalized play) that do NOT exist in `user_saved_albums`.
  2. **Library View Switcher:** Add a segmented toggle to the crate header:
     - 📦 **My Saved Vinyl** *(Default)*: Current saved collection.
     - ✨ **You Should Save These** *(Played But Unsaved)*: Surfaces unowned albums ordered by play count / recency.
  3. **Tactile Badge & Action:** Sleeves display an unowned indicator badge with a 1-click `➕ Save to Spotify` action (calling Spotify Web API `PUT /v1/me/albums?ids=...`).
* **Effort & Complexity:** ~4–6 hours (0.5 to 1 day) • **Complexity:** **Low–Medium**

---

#### `APP-08`: Full-Length Virtual Turntable Web Player (Spotify Web Playback SDK & Spinning Vinyl Disc)
* **Problem:**  
  While the 30-second needle-drop preview snippets provide quick auditioning, listeners cannot stream full album tracks directly inside SpinSleeve. Listeners who want to spin an entire record must leave the web app to open Spotify, breaking the immersive physical vinyl ritual.
* **Solution:**  
  Build an interactive, physical-style Virtual Turntable Player powered by the **Spotify Web Playback SDK**:
  1. **Vinyl Disc Extraction Animation:** Clicking "Spin Record" triggers a tactile animation where the high-res 12" vinyl disc slides out from the album jacket sleeve and drops onto the turntable platter.
  2. **Authentic 33⅓ RPM Platter Rotation:** The vinyl platter and center label art rotate at authentic 33⅓ RPM while playing, synchronized with the tonearm gently resting on the outer groove.
  3. **Full-Length Streaming (Spotify Premium):** Integrated Spotify Connect device (*"SpinSleeve Hi-Fi Turntable"*). Stream full album tracklists with play/pause, scrub, pitch control, and next/previous track controls.
  4. **Universal Free Tier Fallback:** If a listener has a Spotify Free account (or Web Playback SDK is unavailable), the player automatically falls back to the existing 30-second needle-drop preview snippets with clear guidance.
* **Effort & Complexity:** ~8–12 hours (1.5 days) • **Complexity:** **Medium**

---

#### `APP-09`: Granular Track-Level Telemetry & Audio Archive
* **Problem:**  
  The Analytics view aggregates scrobbles at high levels (heatmaps, velocity, top albums). Listeners lack visibility into granular, track-level playback history and cannot drill into songs by genre or specific historical timeframes without querying raw logs.
* **Solution:**  
  Introduce an interactive track telemetry and archival playback log:
  1. **Partitioned & Clustered Querying:** Query `playback_history` clustered by `user_id`, joined with `album_enriched_metadata` to retrieve genre/style classifications and acoustic tags.
  2. **Dynamic Range & Genre Filtering:** Quick-filter pill deck for rolling windows (24h, 7d, 30d, Custom Range) alongside dynamic genre chips for focused sonic digging.
  3. **Tactile Audio Auditioning:** 30s needle-drop preview with soundwave animation + Spotify web player deep link for instantaneous playback.
  4. **Relative Timestamp Display:** Human-readable scrobbled timestamps with relative display (e.g., *"Played 2 hours ago"*).
  5. **Performant Virtualization:** Cursor pagination / virtualized scrolling (50 tracks per batch) to ensure smooth client performance across large listening histories.
* **Effort & Complexity:** ~6–8 hours (1 day) • **Complexity:** **Medium**

---

#### `APP-10`: Local Gig Radar: Top Artists Live in Your City (Bandsintown API & DICE Deep-Links)
* **Problem:**  
  Listeners frequently spin records by artists they love without realizing those same artists are touring or performing nearby in their home city. Mainstream ticketing platforms don't connect a collector's deep vinyl listening telemetry and rolling heavy rotation directly to local gig calendars.
* **Solution:**  
  Build a dedicated "Local Gig Radar" view (`/gigs`) connecting vinyl telemetry to live concert discovery:
  1. **Telemetry Artist Ingestion:** Aggregate the listener's top 25–50 artists from `playback_history` (supporting both rolling 30-day Heavy Rotation and All-Time favorites).
  2. **Bandsintown Event Ingestion:** Query Bandsintown REST API (`GET /artists/{artist}/events`) to fetch upcoming tour dates, venue details, coordinates, lineups, and ticket URLs.
  3. **City & Distance Filtering:** Localized city selector (defaulting to the listener's configured city, e.g., London, UK) with radius filtering to spotlight upcoming concerts in their immediate area.
  4. **Gig Flier Interface:** Chronological concert timeline styled like an authentic live gig flier / poster, displaying date, venue, city, and listener spin count badges (*"🔥 42 Plays"*).
  5. **Direct DICE & Box Office Links:** Each gig card pairs official ticket links with a 1-click `🎲 Check on DICE` deep link (`https://dice.fm/search?query=...`) for rapid mobile checkout on fans' preferred ticketing platform.
  6. **Tiered Event Caching:** Cache artist tour responses in Datastore / memory (24h TTL) to ensure instant page loads and protect against external rate limits.
* **Effort & Complexity:** ~6–8 hours (1 day) • **Complexity:** **Medium**

---

#### `APP-11`: Collector’s Inscriptions: Personal Album Ratings & Archival Notes
* **Problem:**  
  1. **The Pre-Tracking Blindspot:** High-fidelity vinyl collectors and music enthusiasts have foundational cornerstone records they spun hundreds of times on physical vinyl, cassette, or CD before digital scrobble tracking began. Because these albums show low or zero Spotify scrobbles, SpinSleeve’s "Heavy Rotation" and play-count badges inadvertently relegate these masterpieces to the "Cold Shelf."
  2. **Frequency vs. Emotional Affinity:** Raw play frequency measures convenience, background utility, or recent loops, but not deep artistic resonance. An album listened to once a year with full emotional reverence may be a personal 10/10, yet telemetry alone cannot capture this.
  3. **Social Storytelling in SpinPals:** When crate digging through a friend's collection, the most meaningful experience isn't just seeing what they own—it’s hearing *why* they love it (*"Got this on our road trip to Big Sur in 2019"*, *"Listen with headphones in the dark—Side B will change your life"*).
* **Solution:**  
  Build a tactile rating and personal liner notes inscription system designed specifically for collectors, ensuring an unforced, sparse user experience and future-proof analytics:
  1. **Sparse UX & Non-Biased Visual Design:**
     - **Zero Visual Penalty for Unrated Albums:** Unrated albums never display empty gray stars (`☆☆☆☆☆`), `Unrated` tags, or dashed placeholders. Unrated sleeves remain 100% clean, focusing on artwork and primary normalized play metrics (`🔥 X Plays`).
     - **Earned Collector’s Seal Badge:** Only albums with an explicit rating or note display an unobtrusive gold badge (e.g., `★ 5.0` or `★ 4.5 📝` in the upper corner), acting like an earned "Staff Pick" or "Signature Record" seal rather than a missing checkbox.
     - **Subordinate Sorting & Filtering:** The default sort remains `🔥 Heavy Rotation (Last 30 Days)`. `⭐ Highest Rated` and `📝 Inscribed Sleeves` are placed as secondary, deliberate options in the sort dropdown and filter bar.
  2. **12" Gatefold Modal Inscription Card:**
     - Styled like an authentic archival index card or liner card insert tucked into the gatefold sleeve.
     - Tactile 5-star rating selector (0.5 increments, 1.0 to 5.0 stars) with smooth hover and click feedback.
     - Handwritten note textarea (up to 1,000 characters) with conversational placeholder prompts (*"Why is this record in your collection? Share a memory or why it spins..."*).
     - Instant AJAX save (`💾 Inscribe Sleeve`) with optimistic UI feedback and a privacy toggle (`🔒 Keep private / visible only to me`).
  3. **SpinPals Social Crate Digging (`/pals` & `/pals/<pal_id>`):**
     - When crate digging a friend's collection, sleeves display the pal's star rating seal.
     - Opening the pal's record in the gatefold displays their handwritten inscription in a distinct, warm quote card (*"Sarah's Inscription (★ 5.0): Spun this every Sunday morning in autumn..."*).
     - **Mutual Reflections:** If both you and your pal own and have inscribed the same album, display both notes side-by-side (*"Your Inscription"* vs *"Sarah's Inscription"*).
  4. **Dual-Storage & Asynchronous BigQuery Analytics Sync:**
     - **OLTP Tier (Cloud Datastore `AlbumReview`):** Delivers sub-15ms reads and writes when browsing or updating inscriptions in the web app, completely within GCP free-tier quotas.
     - **Analytical Tier (BigQuery `spotify_v2.user_album_reviews`):** Automated 2-hour Cloud Run Job (`src/pipeline_v2/sync.py`) syncs Datastore inscriptions into BigQuery (partitioned by date, clustered by `user_id, album_id`).
     - **Materialized Feature Join:** During pipeline rematerialization, merges user ratings into `user_albums_features_table` (`user_rating`, `user_notes`, `has_user_review`) for zero-latency queries.
     - **Future Analytics Unlocked:** Enables deep correlation analysis ("Reverence vs. Rotation / The Guilty Pleasure Index", "Collector vs. Critics: Pitchfork vs. Personal Rating", and friend taste agreement in SpinPals).
* **Effort & Complexity:** ~5–7 hours (1 day) • **Complexity:** **Low–Medium**

---

### 🛠️ Category: Tactical Polish, UX Streamlining & Quick Fixes (`POLISH`)

#### `POLISH-01`: ✅ ~~Harmonise "Heavy Rotation" Filter Across Tabs & Simplify Crate Digger Selection~~
* **Problem:** Terminology, active filter states, and horizon controls differed or clashed between Listening Mode and Time Horizon, causing cognitive friction and consuming ~340px of vertical space with empty black padding. Mood vibes were heavily skewed towards energetic due to broad substring matching on `'rock'`.
* **Solution Implemented (`v2.2.1`):**
  1. **Single-Dimension Crate Target:** Replaced conflicting Listening Mode and Time Horizon rows with a clean 5-target selector (`🔥 Heavy Rotation (30D)`, `🔍 Unplayed Gems`, `❄️ Cold Shelf (30D+)`, `⭐ All-Time Favorites`, `🌌 Full Crate`).
  2. **Compact 2-Tier Console:** Compacted the filter box from ~340px down to ~95px, saving >240px of vertical height and pulling spotlight vinyl picks above the fold.
  3. **Balanced Vibe Classification:** Removed broad `'rock'` from energetic; enriched chill (`shoegaze`, `trip hop`, `ambient pop`, `idm`), mellow (`chamber pop`, `americana`, `bluegrass`), and vintage (`classic soul`, `motown`, `psychedelic rock`, and pre-1985 release years).
* **Effort & Complexity:** ~2–3 hours • **Status:** **Completed (`v2.2.1`)**

---

#### `POLISH-02`: [Fix] Library Explorer Heavy Rotation Initial Sort (Strict 30D on Initial Load)
* **Problem:** In Library Explorer (`/` and `/beta/`), the sort dropdown displays `🔥 Heavy Rotation (Last 30 Days)` selected by default, which is intended. However, on initial page load, `document.addEventListener("DOMContentLoaded")` directly invokes `renderGrid()` without running `onFilterChange()`. Because the underlying SQL query sorts by `ORDER BY album_plays DESC` (All-Time Most Played), the albums initially rendered on screen are ordered by all-time plays rather than 30-day plays until the user manually changes the dropdown.
* **Solution:**
  1. Trigger `onFilterChange()` instead of raw `renderGrid()` inside `DOMContentLoaded` so `plays_30d_desc` sorting is applied immediately on first load.
  2. Enforce deterministic primary ordering strictly by rolling 30-day play counts (`album_track_plays_30d DESC`, then `album_plays_30d DESC`, then raw plays tiebreaker).
* **Effort & Complexity:** ~1 hour • **Complexity:** **Low**

---

#### `POLISH-03`: Play Count Badge Refinement (Decimal Plays / "Newly Added" / "Never Played")
* **Problem:** Albums with zero scrobbles or partial scrobbles below 1 full spin currently show a bare `🔥 0 Plays` badge, which feels unrewarding and inaccurate for records with partial plays or newly acquired vinyl.
* **Solution:** Eliminate bare `0 Plays`. For unplayed records, display contextual tags like `Newly Added` or `Never Played`. For records with scrobbles totaling less than 1 full spin or between spins, display a clean decimal play count (e.g. `🔥 0.4 Plays`, `🔥 1.7 Plays`).
* **Effort & Complexity:** ~1–2 hours • **Complexity:** **Low**

---

#### `POLISH-04`: Semantic Build Version Numbering (Replace "beta v2" with Dynamic Version) [✅ Completed]
* **Problem:** The main Library page still displays the generic "beta v2" badge in the header, offering no visibility into which build or deployment revision is currently serving traffic.
* **Solution:** Remove the static "beta v2" label. Introduce a centralized semantic application version number (`APP_VERSION = "v2.2.0"`) globally injected via Flask context processor and visible in the header badge.
* **Effort & Complexity:** ~1–2 hours • **Complexity:** **Low**

---

#### `POLISH-05`: Standardize Header Profile Avatar (Remove Admin Impersonation from Global Header) [✅ Completed]
* **Problem:** The top-right user profile widget in the global header currently renders dev-switcher links (`👑 Serge`, `👩 Sarah`, `🐹 GuineaPig`) for admins, cluttering the clean navigation bar across every view.
* **Solution:** Standardize the top-right corner to show only a normal user profile avatar and logout button for all users (including admins). Keep admin user view assumption and impersonation strictly housed inside the dedicated Admin Portal (`/admin`).
* **Effort & Complexity:** ~1–2 hours • **Complexity:** **Low**

---

#### `POLISH-06`: Admin Portal Table Formatting & Column Alignment
* **Problem:** The user management table in the Admin control deck (`/admin`) suffers from uneven column widths, misaligned action buttons, and suboptimal text truncation on certain screen sizes.
* **Solution:** Redesign the Admin table with explicit column widths, consistent typography, aligned status chips (Approved, Whitelisted, Opted-In), and streamlined action buttons.
* **Effort & Complexity:** ~1–2 hours • **Complexity:** **Low**

---

#### `POLISH-07`: ✅ ~~De-duplicate Crate Digger "Spin Again" Header Button~~
* **Problem:** In Crate Digger (`/recommend` & `/beta/recommend`), there were two identical buttons that invoked `spinAgain()`: one in the global navigation header next to "Hover Audio: ON", and one on the right side of Row 1 in the new Control Deck console labeled "Shuffle Picks". Having both created visual clutter and redundant controls.
* **Solution Implemented (`v2.2.1`):**
  1. Removed the redundant `<span>🎲</span> Spin Again` button from the global navigation header.
  2. Retained the button located on the Control Deck console (which is in the optimal ergonomic location next to Crate Target filters) and renamed its label to `🎲 Spin Again`.
* **Effort & Complexity:** ~0.5 hours (30 min) • **Status:** **Completed (`v2.2.1`)**

---

### 🎨 Category: Brand Identity, Public Landing & Monetization (`BRAND`)

#### `BRAND-01`: Homepage & Public Login Redesign with Feature Showcase
* **Problem:**  
  1. The current public landing page (`/login`) is a minimal auth modal. Prospective users and friends don't get a visual tour of what SpinSleeve offers before connecting their streaming account.
  2. **Corporate Firewall & Web Filter Blocking:** When accessed from enterprise or workplace networks, the site is frequently blocked by security proxies (Zscaler, Palo Alto Networks PAN-DB, Fortinet FortiGuard, Cisco Umbrella). Because the domain (`spinsleeve.cc`) has a non-commercial TLD and root traffic redirects to Spotify OAuth without public corporate metadata, automated web crawlers categorize it under restrictive categories (*"Non-Commercial / Personal Sites"*, *"Streaming Media & Audio"*, or *"Uncategorized / Newly Seen Domains"*), preventing users from accessing their collection at work.
* **Solution:**  
  An editorial, highly aesthetic public landing page engineered for high user conversion and corporate security compliance:
  1. **Hero Section:** Rotating 33⅓ RPM turntable branding, bold typography, and 1-click Spotify / Apple Music login buttons.
  2. **"Why SpinSleeve Exists" Narrative:** A short manifesto explaining the mission—rescuing the physical ritual of vinyl, sleeve artwork, and liner notes from algorithmic streaming feeds.
  3. **Interactive Feature Showcase:**
     - *Virtual Vinyl Crate & Library Explorer:* Screenshots showing gatefold sleeve reader and needle-drop preview controls.
     - *Smart Crate Digger:* Highlighting discovery by vibe, era, and subgenre.
     - *Listening Telemetry:* Visualizing listening clock heatmaps and taste velocity.
     - *SpinPals (CrateMates):* Demonstrating acoustic kinship gauges and friend shelf borrowing.
  4. **Enterprise Firewall & Security Crawler Compliance:**
     - **Public Unauthenticated Root (`/` & `/login`):** Deliver an indexed public showcase rather than an abrupt OAuth redirect or bare login card.
     - **Standard Corporate Footers:** Dedicated `/about`, `/privacy` (Privacy Policy explaining zero user data tracking, read-only Spotify scopes, and session isolation), and `/terms` (Terms of Service).
     - **Developer Identity & Verified Ownership:** Explicit copyright notice (`Copyright © 2017–2026 Serge Bouschet`), developer contact info (`contact@spinsleeve.cc` / GitHub link), and structured OpenGraph/Twitter card metadata (`og:title`, `og:description`, `application-name="SpinSleeve"`, `category="Technology/Software & Web Applications"`).
     - **Security Recategorization Runbook:** Step-by-step submission guide to request categorization updates on Palo Alto Networks Test-A-Site, FortiGuard, Zscaler, and Cisco Talos (requesting *"Information Technology / Software & Web Applications"*).
     - **Commercial TLD Alias Ready:** Structure Firebase Hosting rewrites to support seamless aliasing to a secondary `.com` or `.app` domain (e.g., `spinsleeve.com` or `spinsleeve.app`) to bypass country-code TLD heuristics.
  5. **Invite Guidance:** Clear instructions on requesting private access from Serge.
* **Effort & Complexity:** ~6–8 hours (1 day) • **Complexity:** **Low–Medium**

---

#### `BRAND-02`: "Buy Me a Coffee" Supporter Integration
* **Problem:**  
  SpinSleeve is an independent labor of love with ongoing cloud infrastructure and API costs. Friends and enthusiastic listeners frequently ask for ways to support the project.
* **Solution:**  
  Tasteful integration of Buy Me a Coffee (`https://buymeacoffee.com/`):
  - Subtle floating or footer button: `☕ Buy the Creator a Coffee`.
  - Embedded badge in the 12" gatefold back sleeve liner notes reader.
  - Recognition badge in the Listening Lounge for club supporters.
* **Effort & Complexity:** ~1–2 hours • **Complexity:** **Low**

---

#### `BRAND-03`: Public Roadmap & Release Transparency Portal (`/roadmap`)
* **Problem:**  
  Prospective listeners, beta friends, and club supporters have no visibility into planned releases, active milestones, or upcoming features directly from the user interface.
* **Solution:**  
  Launch a dedicated public release and feature transparency portal at `/roadmap`:
  1. **Public-Facing Route:** Dedicated unauthenticated `/roadmap` route accessible to prospective listeners, beta friends, and club members without login barriers.
  2. **Global Navigation Link:** Prominent header and banner link (🗺️ *Roadmap*) in global navigation and the public landing page.
  3. **Visual Lane Kanban:** Categorized lane presentation across *Shipped*, *In Progress*, and *Up Next*, filterable by category (`INFRA`, `OPS`, `APP`, `POLISH`, `BRAND`, `DOCS`).
  4. **Release Notes Linkage:** Injects dynamic version (`v2.2.0`) linked directly to detailed release notes and changelog entries.
* **Effort & Complexity:** ~3–4 hours (0.5 day) • **Complexity:** **Low**

---

#### `BRAND-04`: Software License & IP Protection Review (AGPLv3 / PolyForm Noncommercial Migration)
* **Problem:**  
  1. The repository currently uses the permissive **MIT License** (`Copyright (c) 2017 Serge Bouschet`).
  2. Under MIT, while source code distributions must retain the copyright header, the license contains the well-known **"Hosted Web Service / SaaS Loophole"**: third parties or commercial entities can take the entire codebase, host it privately on Cloud Run or AWS as a paid service or clone, rebrand it, and monetize it without contributing code back, requesting permission, or giving public frontend attribution to Serge.
  3. Furthermore, MIT provides zero legal restrictions against third parties commercially exploiting SpinSleeve without revenue sharing.
* **Solution:**  
  Conduct a comprehensive legal and architectural review of the repository's licensing structure, evaluating and executing migration to stronger intellectual property protections:
  1. **Option A: AGPLv3 (GNU Affero General Public License v3):**
     - Closes the SaaS loophole: Any entity running SpinSleeve over a network (as a web application) is legally obligated to release their full modified source code to network users under AGPLv3, and retain prominent public copyright attribution.
     - Preserves true open-source status while preventing proprietary cloud freeloading.
  2. **Option B: PolyForm Noncommercial 1.0.0 (or PolyForm Free Trial):**
     - Grants free rights to students, hobbyists, and developers to inspect, run, modify, and test the software for noncommercial purposes.
     - Strictly forbids any commercial hosting, monetization, or proprietary commercial derivatives without a separately negotiated commercial license from Serge.
  3. **Dependency & Transitive License Audit:**
     - Verify compatibility of all dependencies in `src/report_v2/requirements.txt` and `src/pipeline_v2/requirements.txt` (Flask, spotipy, google-cloud-bigquery, google-cloud-datastore) with AGPLv3 and PolyForm.
  4. **License Migration Execution:**
     - Update `LICENSE`, file headers, `README.md`, and add a `CONTRIBUTING.md` defining contributor license agreements (CLA) or Developer Certificate of Origin (DCO).
* **Effort & Complexity:** ~2–4 hours (0.5 day) • **Complexity:** **Low**

---

### 📚 Category: Architecture Mapping & Documentation (`DOCS`)

#### `DOCS-01`: Comprehensive Technical Project Architecture Map (README Overhaul)
* **Problem:**  
  Technical details are currently dispersed across `GEMINI.md`, `INFRASTRUCTURE_RUNBOOK.md`, and session logs. The main `README.md` needs to serve as an authoritative, exhaustive engineering map of the system.
* **Solution:**  
  Complete overhaul of `README.md` featuring:
  1. **System Topology Diagram:** End-to-end ASCII/Mermaid flow mapping Firebase CDN → Cloud Run → Cloud Datastore → BigQuery → Spotify OAuth PKCE.
  2. **Component Directory:** Deep-dive descriptions of every service, job, and background process with technical design rationales.
  3. **Data Dictionary:** Schema specifications for `playback_history`, `user_saved_albums`, and `album_enriched_metadata`.
  4. **Non-Negotiable Invariants:** Explicit architectural constraints (Firebase `__session` cookie mechanics, sanitization routines, PKCE dialogue rules).
  5. **Disaster Recovery & Operational Cheatsheet:** Step-by-step rebuild and rollback procedures.
* **Effort & Complexity:** ~3–4 hours (0.5 day) • **Complexity:** **Low**

---

## 4. Master Engineering Backlog Matrix

| Code | Title | Category | Est. Effort | Tech Stack & Dependencies | Strategic Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`INFRA-01`** | Fresh GCP Project Migration | Infrastructure | 6–8h | GCP IAM, Cloud Run, BigQuery, Datastore, Firebase | **High:** Clean security boundary, zero pet project clutter, dedicated billing. |
| **`INFRA-02`** | Infrastructure as Code (Terraform) | Infrastructure | 8–12h | Terraform, HCL, Google Cloud Provider, GCS Backend | **High:** Reproducible disaster recovery and automated cloud provisioning. |
| **`INFRA-03`** | Sub-100ms Multi-Tier Caching & Materialization | Infrastructure | 6–8h | Cloud Datastore, BigQuery, sessionStorage, Flask | **High:** Eliminates 2–4s tab-switching latency; drops catalog response times to <25ms with $0 new cloud costs. |
| **`OPS-01`** | CI/CD GitHub Actions & Protected Master | DevOps | 6–8h | GitHub Actions, Workload Identity Federation, Pytest | **High:** Eliminates manual terminal deployments and prevents untested regressions. |
| **`OPS-02`** | Observability, Alerting & Health Monitoring | DevOps | 4–6h | Cloud Monitoring, Alert Policies, `/healthz` | **Medium:** Automated 5xx failure detection and resource saturation alerts. |
| **`OPS-03`** | Real-Time Admin Alerts for Join Requests | DevOps | 3–4h | Telegram Bot API / Discord Webhook, Cloud Run | **Medium:** Instant 1-click mobile approvals for new friends. |
| **`APP-01`** | 12" Gatefold Tracklisting & Side A/B Splits | Core App | 4–6h | Spotify Web API, Jinja2, Tailwind CSS | **Medium:** Completes tactile physical record feel with track-level auditioning. |
| **`APP-02`** | Apple Music Library Onboarding (Phase 7) | Core App | 16–24h | MusicKit JS v3, Apple Developer Key (.p8), BigQuery | **Massive:** Bypasses Spotify allowlist limits and expands to Apple Music collectors. |
| **`APP-03`** | In-App Feedback & Wishlist Collector | Core App | 5–7h | Cloud Datastore (`Feedback`), Flask, Admin UI | **Medium:** Frictionless feedback loop directly from active listeners. |
| **`APP-04`** | Music Legend Illustrated Avatars | Core App | 4–5h | SVG Vector Graphics, Datastore, Tailwind CSS | **Low:** Aesthetic charm and personal flair for users without profile photos. |
| **`APP-05`** | ✅ ~~Album Sleeve Normalized Play Count Badge~~ | Core App | 2–3h | Jinja2, Tailwind CSS, JavaScript | ✅ **Completed** (Revision `00018-c67`): Normalized spins with flame badge, singular/plural formatting, and detailed hover tooltip across Library Explorer, Crate Digger, and SpinPals. |
| **`APP-06`** | ✅ ~~Crate Digger & SpinPals Dynamic Time Horizon~~ | Core App | 5–7h | BigQuery SQL, Python Flask, JavaScript | ✅ **Completed:** Rolling 30D play count aggregation in BQ view, 2-way horizon toggles in Crate Digger & SpinPals, and 30D library sort. |
| **`APP-07`** | Played But Not Owned ("You Should Save These") Crate | Core App | 4–6h | BigQuery SQL, Flask, Spotify API | **Medium:** Uncovers streamed favourites missing from the vinyl shelf with 1-click library save. |
| **`APP-08`** | Full-Length Virtual Turntable Web Player | Core App | 8–12h | Spotify Web Playback SDK, CSS Keyframes, Web Audio | **High:** Immersive full-length streaming with vinyl disc sliding from sleeve onto rotating 33⅓ platter. |
| **`APP-09`** | Granular Track-Level Telemetry & Audio Archive | Core App | 6–8h | BigQuery SQL, Spotify Web API, Tailwind CSS, JavaScript | **Medium:** Granular track-level playback history, dynamic genre filtering, 30s needle-drop previews, and relative timestamps. |
| **`APP-10`** | Local Gig Radar: Top Artists Live in Your City | Core App | 6–8h | Bandsintown API, DICE Deep-Links, BigQuery SQL, Flask, Tailwind CSS | **High:** Connects vinyl listening telemetry to live concerts in the user's city with 1-click DICE checkout. |
| **`APP-11`** | Collector’s Inscriptions & Ratings | Core App | 5–7h | Cloud Datastore, BigQuery, Jinja2, Tailwind CSS | **High:** Personal 5-star ratings, handwritten liner notes, and dual OLTP/BigQuery storage for taste analysis. |
| **`POLISH-01`** | ✅ ~~Harmonise "Heavy Rotation" Filter & Crate Digger UX~~ | Tactical Polish | 2–3h | Jinja2, JavaScript, Tailwind CSS | ✅ **Completed** (`v2.2.1`): Streamlined 2-tier console, single-dimension crate target, balanced vibes. |
| **`POLISH-02`** | [Fix] Library Explorer Heavy Rotation Initial Sort (Strict 30D on Load) | Tactical Polish | 1h | JavaScript, DOM Lifecycle | **Medium:** Ensure DOMContentLoaded triggers `onFilterChange()` so 30D sort applies immediately on first load. |
| **`POLISH-03`** | Play Count Badge Refinement (Decimal / Newly Added) | Tactical Polish | 1–2h | Python, Jinja2, JavaScript | **Medium:** Replace bare "0 Plays" with decimal normalized spins or contextual new tags. |
| **`POLISH-04`** | ✅ ~~Semantic Build Version Numbering (Remove "beta v2")~~ | Tactical Polish | 1–2h | Flask, Jinja2, CI/CD | ✅ **Completed** (`v2.2.0`: Revision `00022-z5t`): Replaced static beta badge with dynamic semantic release version. |
| **`POLISH-05`** | ✅ ~~Clean Header Profile Avatar (Remove Admin Switcher)~~ | Tactical Polish | 1–2h | Jinja2, HTML5, Flask Session | ✅ **Completed** (Revision `00022-z5t`): Clean standard user avatar for all users; impersonation housed in Admin Portal. |
| **`POLISH-06`** | Admin Portal Table Column Alignment & Layout Polish | Tactical Polish | 1–2h | HTML5, Tailwind CSS | **Low:** Eliminates table misalignment, button wrapping, and truncation on admin portal. |
| **`POLISH-07`** | ✅ ~~De-duplicate Crate Digger "Spin Again" Header Button~~ | Tactical Polish | 0.5h | Jinja2, HTML5 | ✅ **Completed** (`v2.2.1`): Removed header duplicate; harmonized Control Deck button to "Spin Again". |
| **`BRAND-01`** | Landing Page Redesign & Feature Showcase | Brand & Growth | 6–8h | Tailwind CSS, HTML5, Responsive Screenshots | **High:** Professional public face, manifesto narrative, corporate firewall compliance, and visual showcase. |
| **`BRAND-02`** | Buy Me a Coffee Integration | Monetization | 1–2h | BuyMeACoffee API / Embed, HTML | **Low:** Easy community support channel for hosting and API costs. |
| **`BRAND-03`** | Public Roadmap & Release Transparency Portal (`/roadmap`) | Brand & Growth | 3–4h | Flask, Jinja2, Tailwind CSS, Semantic Versioning | **Low:** Public release transparency, active milestone visibility, and open roadmap portal for club supporters. |
| **`BRAND-04`** | ✅ ~~Software License & IP Protection Review~~ | Legal & Brand | 2–4h | PolyForm Noncommercial 1.0.0 | ✅ **Completed** (`v2.2.2`): Migrated repository to PolyForm Noncommercial 1.0.0 to prevent unauthorized commercial exploitation while keeping non-commercial use & contributions free. |
| **`DOCS-01`** | Technical Architecture Map (README Overhaul) | Documentation | 3–4h | Markdown, Mermaid Diagrams | **High:** Complete developer transparency and comprehensive system mapping. |
