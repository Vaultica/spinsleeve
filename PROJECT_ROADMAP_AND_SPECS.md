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
 │ [BRAND]  Brand Identity, Public Landing & Monetization                 │
 │ [DOCS]   Architecture Mapping & Documentation                          │
 └────────────────────────────────────────────────────────────────────────┘
```

### Summary Feature Index

| Code | Title | Category | Estimated Effort | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **`INFRA-01`** | Fresh GCP Project Migration & Environment Isolation | Infrastructure | 6–8 hours | Medium |
| **`INFRA-02`** | Declarative Infrastructure as Code (IaC) via Terraform | Infrastructure | 8–12 hours | Medium |
| **`INFRA-03`** | Sub-100ms Multi-Tier Caching & BQ Materialization Architecture | Infrastructure | 6–8 hours | Medium |
| **`OPS-01`** | CI/CD Pipelines via GitHub Actions & Branch Protection | DevOps | 6–8 hours | Medium |
| **`OPS-02`** | Production Observability, Alerting & Health Monitoring | DevOps | 4–6 hours | Low–Med |
| **`OPS-03`** | Real-Time Admin Alerts for User Join Requests | DevOps | 3–4 hours | Low |
| **`APP-01`** | 12" Gatefold Tracklisting & Side A / Side B Breakdown | Core App | 4–6 hours | Low–Med |
| **`APP-02`** | Cross-Platform Apple Music Library Onboarding (Phase 7) | Core App | 16–24 hours | Medium |
| **`APP-03`** | In-App Feedback & Liner Notes Wishlist Collector | Core App | 5–7 hours | Low–Med |
| **`APP-04`** | Music Legend Illustrated Avatar Persona Picker | Core App | 4–5 hours | Low |
| **`APP-05`** | ✅ ~~Album Sleeve Normalized Play Count Badge ("🔥 X Plays")~~ | Core App | 2–3 hours | Completed (Revision `00018-c67`) |
| **`APP-06`** | ✅ ~~Crate Digger & SpinPals "Top Pick" Horizon (30D vs. All Time)~~ | Core App | 5–7 hours | Completed |
| **`APP-07`** | Played But Not Owned ("You Should Save These") Library Crate | Core App | 4–6 hours | Low–Med |
| **`BRAND-01`** | Homepage & Public Login Redesign with Feature Showcase | Brand & Growth | 6–8 hours | Low–Med |
| **`BRAND-02`** | "Buy Me a Coffee" Supporter Integration | Monetization | 1–2 hours | Low |
| **`DOCS-01`** | Comprehensive Technical Project Architecture Map (README) | Documentation | 3–4 hours | Low |

---

## 3. Detailed Feature Specifications

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
* **Solution:**  
  Integrate complete tracklists into the 12" gatefold modal:
  1. **Data Ingestion:** Fetch album tracklisting (track number, title, duration in mm:ss, explicit flag) via Spotify Web API or iTunes Search API.
  2. **Physical Vinyl Layout:** Format tracks split into virtual vinyl sides:
     - Side A: Tracks 1 to N/2
     - Side B: Tracks N/2+1 to N
  3. **Inline Needle-Drop:** Clicking any track name instantly swaps the audio preview player to audition that specific track's 30-second snippet.
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

### 🎨 Category: Brand Identity, Public Landing & Monetization (`BRAND`)

#### `BRAND-01`: Homepage & Public Login Redesign with Feature Showcase
* **Problem:**  
  The current public landing page (`/login`) is a minimal auth modal. Prospective users and friends don't get a visual tour of what SpinSleeve offers before connecting their streaming account.
* **Solution:**  
  An editorial, highly aesthetic public landing page:
  1. **Hero Section:** Rotating 33⅓ RPM turntable branding, bold typography, and 1-click Spotify / Apple Music login buttons.
  2. **"Why SpinSleeve Exists" Narrative:** A short manifesto explaining the mission—rescuing the physical ritual of vinyl, sleeve artwork, and liner notes from algorithmic streaming feeds.
  3. **Interactive Feature Showcase:**
     - *Virtual Vinyl Crate & Library Explorer:* Screenshots showing gatefold sleeve reader and needle-drop preview controls.
     - *Smart Crate Digger:* Highlighting discovery by vibe, era, and subgenre.
     - *Listening Telemetry:* Visualizing listening clock heatmaps and taste velocity.
     - *SpinPals (CrateMates):* Demonstrating acoustic kinship gauges and friend shelf borrowing.
  4. **Invite Guidance:** Clear instructions on requesting private access from Serge.
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
| **`BRAND-01`** | Landing Page Redesign & Feature Showcase | Brand & Growth | 6–8h | Tailwind CSS, HTML5, Responsive Screenshots | **High:** Professional public face, manifesto narrative, and visual feature showcase. |
| **`BRAND-02`** | Buy Me a Coffee Integration | Monetization | 1–2h | BuyMeACoffee API / Embed, HTML | **Low:** Easy community support channel for hosting and API costs. |
| **`DOCS-01`** | Technical Architecture Map (README Overhaul) | Documentation | 3–4h | Markdown, Mermaid Diagrams | **High:** Complete developer transparency and comprehensive system mapping. |
