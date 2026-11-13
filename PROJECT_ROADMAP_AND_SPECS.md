# SpinSleeve: Architecture, Roadmap & Feature Backlog

**Production Domain:** `https://spinsleeve.cc`  
**Current GCP Project ID:** `secret-compass-181513` | **Compute Region:** `europe-west2` (London) | **BigQuery Region:** `US`

---

## Table of Contents
1. [1. Executive Summary & Implemented Milestones](#1-executive-summary--implemented-milestones)
2. [2. Product & Engineering Backlog (By Category)](#2-product--engineering-backlog-by-category)
   - [Summary Feature Index](#summary-feature-index)
3. [3. Detailed Feature Specifications](#3-detailed-feature-specifications)
   - [🏛️ Category: Infrastructure & Cloud Architecture (`INFRA`)](#category-infrastructure--cloud-architecture-infra)
   - [🚀 Category: DevOps, CI/CD, Reliability & Observability (`OPS`)](#category-devops-cicd-reliability--observability-ops)
   - [🎵 Category: Core Application & Vinyl Streaming (`APP`)](#category-core-application--vinyl-streaming-app)
   - [🛠️ Category: Tactical Polish, UX Streamlining & Quick Fixes (`POLISH`)](#category-tactical-polish-ux-streamlining--quick-fixes-polish)
   - [🎨 Category: Brand Identity, Public Landing & Monetization (`BRAND`)](#category-brand-identity-public-landing--monetization-brand)
   - [📚 Category: Architecture Mapping & Documentation (`DOCS`)](#category-architecture-mapping--documentation-docs)
4. [4. Master Engineering Backlog Matrix](#4-master-engineering-backlog-matrix)

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
* **Phase 6g: Spotify Full Scrobble Historical Data Upload & Ingestion (`APP-13`)**
  - In-memory ZIP/JSON streaming history parser supporting Extended and Legacy GDPR formats with podcast filtering and short-scrobble elimination (<30s).
  - Dedicated QA reconciliation tables (`playback_history_qa`) and automated validation scripts.
  - UI settings integration and masthead navigation relocation.
  - Deployed live revision `spotify-dashboard-beta-00034-6lq` (`v2.5.0`).
* **Phase 6h: UI Polish, Header Navigation Consistency & Persistent Audio Mute (`POLISH-09` to `POLISH-13`)**
  - Landing page version number alignment (`v2.5.1`).
  - Consistent header navigation tabs and audio toggles across Library, Crate Digger, Analytics & SpinPals.
  - Cross-page audio mute state persistence via `localStorage`.
  - URL parameter tab routing (`?tab=unowned`, `?tab=saved`).
  - Mobile user settings menu overflow and positioning fix.
  - Deployed live release `v2.5.1`.
* **Phase 6i: Legacy Streaming History Format Support & BigQuery Partition Limit Fix (`v2.5.3`)**
  - Extended and legacy (`StreamingHistory_music_*.json`) Spotify GDPR ZIP extraction filter support.
  - Year-by-year BigQuery DML batching (`MERGE`/`INSERT`) to prevent `400 Too many partitions produced by query` ceiling errors on multi-year lifetime archives.
  - Strict pandas-level dataframe deduplication (`drop_duplicates`) prior to staging load for 100% upload idempotency.
  - Deployed live release `v2.5.3`.

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
| **`INFRA-03`** | ✅ ~~Sub-100ms Multi-Tier Caching & BQ Materialization Architecture~~ | Infrastructure | 6–8 hours | Completed (`v2.5.2`: INFRA-03c/d/e Live) |
| **`INFRA-04`** | Dedicated QA Environment & BigQuery Production Dataset Clone | Infrastructure | 4–6 hours | Medium |
| **`INFRA-05`** | Zero-Cold-Start & High-Concurrency Production Architecture (`--min-instances=1`, 100% Zero-BQ Caching) | Infrastructure | 4–6 hours | Low–Medium |
| **`OPS-01`** | CI/CD Pipelines via GitHub Actions & Branch Protection | DevOps | 6–8 hours | Medium |
| **`OPS-02`** | Production Observability, Alerting & Health Monitoring | DevOps | 4–6 hours | Low–Med |
| **`OPS-03`** | Real-Time Admin Alerts for User Join Requests | DevOps | 3–4 hours | Low |
| **`OPS-04`** | Monolithic App Modularisation & AI Parsing Optimization | DevOps & Efficiency | 4–6 hours | Low–Med |
| **`APP-01`** | 12" Gatefold Tracklisting & Side A / Side B Breakdown | Core App | 4–6 hours | Low–Med |
| **`APP-02`** | Cross-Platform Apple Music Library Onboarding (Phase 7) | Core App | 16–24 hours | Medium |
| **`APP-03`** | In-App Feedback & Liner Notes Wishlist Collector | Core App | 5–7 hours | Low–Med |
| **`APP-04`** | ✅ ~~Music Legend Illustrated Avatar Persona Picker~~ | Core App | 4–5 hours | Completed (`v2.3.0`) |
| **`APP-05`** | ✅ ~~Album Sleeve Normalized Play Count Badge ("🔥 X Plays")~~ | Core App | 2–3 hours | Completed (Revision `00018-c67`) |
| **`APP-06`** | ✅ ~~Crate Digger & SpinPals "Top Pick" Horizon (30D vs. All Time)~~ | Core App | 5–7 hours | Completed (Revision `00019-9ds`) |
| **`APP-07`** | ✅ ~~Played But Not Owned ("You Should Save These") Library Crate~~ | Core App | 4–6 hours | Completed (`v2.4.0`: Revision `00032-6f2`) |
| **`APP-08`** | Full-Length Virtual Turntable Player (Spotify Web Playback SDK) | Core App | 8–12 hours | Medium |
| **`APP-09`** | Granular Track-Level Telemetry & Audio Archive | Core App | 6–8 hours | Medium |
| **`APP-10`** | Local Gig Radar: Top Artists Live in Your City (Bandsintown API) | Core App | 6–8 hours | Medium |
| **`APP-11`** | Collector’s Inscriptions: Personal Album Ratings & Archival Notes | Core App | 5–7 hours | Low–Med |
| **`APP-12`** | ✅ ~~Header Profile Dropdown, User Settings & Community Action Center~~ | Core App | 3–4 hours | Completed (`v2.6.3`): SpinPals opt-in/out and Scrobble Sync Pause toggles, backend sync pause guard. |
| **`APP-13`** | ✅ ~~Spotify Full Scrobble Historical Data Upload & Automated Ingestion~~ | Core App | 6–8 hours | Completed (`v2.5.0`: Revision `00034-6lq`) |
| **`APP-14`** | Headless API & Firestore/Datastore Catalog Rearchitecture (Phase 1) | Core App | 12–16 hours | Medium |
| **`APP-15`** | Native iOS SwiftUI Companion App & Mobile Crate Browsing (Phase 2) | Core App | 20–30 hours | Medium–High |
| **`APP-16`** | Semantic Liner Notes & Description Classification for Crate Digger Relevance | Core App | 6–8 hours | Medium |
| **`POLISH-01`** | ✅ ~~Harmonise "Heavy Rotation" Filter & Simplify Crate Digger~~ | Tactical Polish | 2–3 hours | Completed (`v2.2.1`) |
| **`POLISH-02`** | ✅ ~~Library Explorer Heavy Rotation Initial Sort (Strict 30D on Load)~~ | Tactical Polish | 1 hour | Completed (`v2.2.2`) |
| **`POLISH-03`** | ✅ ~~Play Count Badge Refinement (Decimal Plays / Newly Added)~~ | Tactical Polish | 1–2 hours | Completed (`v2.2.2`) |
| **`POLISH-04`** | ✅ ~~Semantic Build Versioning (Replace "beta v2" with Version)~~ | Tactical Polish | 1–2 hours | Completed (`v2.2.0`: Revision `00022-z5t`) |
| **`POLISH-05`** | ✅ ~~Clean Header Profile Avatar (Remove Admin Switcher from Header)~~ | Tactical Polish | 1–2 hours | Completed (Revision `00022-z5t`) |
| **`POLISH-06`** | Admin Portal Table Column Alignment & Layout Polish | Tactical Polish | 1–2 hours | Low |
| **`POLISH-07`** | ✅ ~~De-duplicate Crate Digger "Spin Again" Header Button~~ | Tactical Polish | 0.5 hours | Completed (`v2.2.1`) |
| **`POLISH-08`** | ✅ ~~Tab Navigation UX Simplification & Hardware Segmented Sub-Tab Deck~~ | Tactical Polish | 2–3 hours | Completed (`v2.4.1`) |
| **`POLISH-09`** | ✅ ~~Landing Page Version Number Alignment (`v2.5.0`)~~ | Tactical Polish | 0.2 hours | Completed (`v2.5.1`) |
| **`POLISH-10`** | ✅ ~~Header Navigation & Audio Toggle Consistency Across All Views~~ | Tactical Polish | 1 hour | Completed (`v2.5.1`) |
| **`POLISH-11`** | ✅ ~~Cross-Page Audio Mute State Persistence (`localStorage`)~~ | Tactical Polish | 1 hour | Completed (`v2.5.1`) |
| **`POLISH-12`** | ✅ ~~URL Parameter Tab Routing (`?tab=unowned` / `?tab=saved`)~~ | Tactical Polish | 0.5 hours | Completed (`v2.5.1`) |
| **`POLISH-13`** | ✅ ~~Mobile User Settings Menu Overflow & Positioning Fix~~ | Tactical Polish | 0.5 hours | Completed (`v2.5.1`) |
| **`BRAND-01`** | ✅ ~~Homepage & Public Login Redesign with Feature Showcase~~ | Brand & Growth | 6–8 hours | Completed (`v2.5.2`) |
| **`BRAND-02`** | "Buy Me a Coffee" Supporter Integration | Monetization | 1–2 hours | Low |
| **`BRAND-03`** | ✅ ~~Public Roadmap & Release Transparency Portal (`/roadmap`)~~ | Brand & Growth | 3–4 hours | Completed (`v2.5.2`) |
| **`BRAND-04`** | ✅ ~~Software License & IP Protection Review (PolyForm Noncommercial 1.0.0)~~ | Legal & Brand | 2–4 hours | Completed (`v2.2.2`) |
| **`DOCS-01`** | ✅ ~~Comprehensive Technical Project Architecture Map (README)~~ | Documentation | 3–4 hours | Completed |

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

#### `INFRA-04`: Dedicated QA Environment & BigQuery Production Dataset Clone
* **Problem:**  
  Testing new features (such as `APP-07` or schema updates) currently runs either against production BigQuery dataset `spotify_v2` or requires mock test fixtures. There is no isolated QA environment to test multi-tenant sync jobs, OAuth token refreshes, and database migrations prior to production cutover.
* **Solution:**  
  Provision an isolated QA environment with zero-cost BigQuery data cloning:
  1. **Parallel GCP QA Project / Service:** Deploy Cloud Run service `spotify-dashboard-qa` in a dedicated QA environment with an isolated Cloud Datastore namespace.
  2. **BigQuery Zero-Cost Dataset Cloning (`spotify_v2_qa`):** Leverage BigQuery dataset copy / table cloning mechanisms (`bq cp` or snapshot policies) to replicate production dataset `spotify_v2` into `spotify_v2_qa`. BigQuery table clones are metadata-only copy operations with zero storage cost until source data changes.
  3. **Automated Preview Deployments:** Configure GitHub Actions workflow (`qa-deploy.yml`) triggered on pull requests and staging branches to build and deploy automatically to `spotify-dashboard-qa`.
* **Effort & Complexity:** ~4–6 hours (0.5 to 1 day) • **Complexity:** **Medium**

---

#### `INFRA-05`: Zero-Cold-Start & High-Concurrency Production Architecture (`--min-instances=1`, 100% Zero-BQ Caching)
* **Problem:**  
  While Tier 2 caching (`UserCatalogCache`) successfully eliminates BigQuery queries for library browsing, cold starts on Cloud Run and on-demand queries for analytics (`/analytics`) and social compatibility (`/pals`) can introduce latency spikes when scaling to hundreds of concurrent users.
* **Solution:**  
  Implement the full zero-cold-start and 100% zero-BQ-on-demand production architecture:
  1. **Cloud Run Minimum Warm Instance (`--min-instances=1`):** Keep at least 1 container instance warm 24/7 (`1 vCPU, 512MB RAM`, ~~$5.40/mo idle cost), eliminating cold starts entirely and ensuring sub-50ms instant response times.
  2. **100% Zero-BQ Analytics & Pal Caching (`INFRA-03d/e`):** Extend pre-aggregated document caching to analytics listening heatmaps and SpinPals acoustic compatibility payloads during background `sync.py` runs. The backend serves static JSON directly from Cloud Datastore with zero BigQuery queries during live user sessions.
  3. **Edge CDN Delivery (Firebase Hosting):** Serve frontend static assets globally via Firebase CDN, allowing instant (<20ms) page shell loading and async API hydration.
* **Effort & Complexity:** ~4–6 hours (0.5 day) • **Complexity:** **Low–Medium**

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

#### `OPS-03`: Real-Time Admin Alerts for User Join Requests (Twilio WhatsApp API)
* **Problem:**  
  When an uninvited user logs in for the first time, their account sits in `PENDING` state until the admin happens to inspect the Admin Control Deck.
* **Solution:**  
  Instant WhatsApp notifications pushed directly to Serge whenever a new Spotify user authenticates:
  - **Service:** Twilio Programmable Messaging API (`whatsapp:+...`).
  - **Payload:** User display name, Spotify ID, email, and a 1-click approval URL:
    ```text
    📢 New SpinSleeve Member Request!
    • Name: Charlie Watts
    • Spotify ID: charliewatts123
    • Email: charlie@rollingstones.com
    👉 Approve: https://spinsleeve.cc/admin
    ```
* **Effort & Complexity:** ~3–4 hours (0.5 day) • **Complexity:** **Low**

---

#### `OPS-04`: Monolithic App Modularisation & AI Parsing Optimization
* **Problem:**  
  `src/report_v2/app.py` has grown into a monolithic file containing route definitions, business logic, BigQuery queries, Datastore access, and Spotify API integrations. This large file structure increases context window consumption during AI-assisted development, slows down static analysis, and makes parallel development and unit testing more difficult.
* **Solution:**  
  Modularise the application code by breaking down the monolith into small, single-responsibility modules and smaller `.py` files. This optimizes AI token efficiency, improves code maintainability, enables faster parallelized unit testing, and establishes a clean dependency tree.
  
  **Target Directory Structure:**
  ```text
  src/report_v2/
  ├── app.py                 # Thin entrypoint (< 150 lines: app init, middleware, error handlers)
  ├── config.py              # Environment variables, GCP project IDs, constants
  ├── routes/
  │   ├── __init__.py
  │   ├── auth.py            # OAuth callbacks, session cookies, logout
  │   ├── crate.py           # Virtual crate browsing, pagination, filtering
  │   ├── pals.py            # SpinPals Lounge, compatibility matching
  │   └── telemetry.py       # Scrobbles, play counts, album spin calculations
  ├── services/
  │   ├── bigquery.py        # SQL queries, materialization, telemetry aggregation
  │   ├── datastore.py       # Token vaults, user metadata, entity caches
  │   └── spotify.py         # Web API client, token refresh logic
  └── templates/             # Jinja partials and pages
  ```

  **Additional Architectural Benefits:**
  1. **AI Context Efficiency:** AI models can load specific domain files (`routes/pals.py` or `services/bigquery.py`) rather than parsing a massive monolith, reducing token consumption by ~70% per turn.
  2. **Isolating Side Effects:** Clear boundaries between HTTP routing, third-party API clients (Spotify), and analytical data storage (BigQuery/Datastore).
  3. **Parallel Collaboration & Testability:** Enables independent unit testing of services without spinning up the full Flask WSGI application server.
  4. **Faster Linters & Type Checkers:** Incremental type checking and linting (`ruff`, `mypy`) execute significantly faster on modularized files.
* **Effort & Complexity:** ~4–6 hours (0.5 to 1 day) • **Complexity:** **Low–Medium**

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

#### `APP-13`: Spotify Full Scrobble Historical Data Upload & Automated Ingestion
* **Problem:**  
  Spotify's standard Web API and automated sync window only capture recent listening history (up to ~50 recent tracks or limited endpoints), leaving lifetime historical scrobbles prior to app onboarding uncaptured. Users want to import their complete historical listening data from Spotify personal data export requests (JSON streaming history files).
* **Solution:**  
  1. **UI Upload Portal:** Add a dedicated upload tab/section in user personal settings (`/settings` or profile management) enabling users to upload their Spotify personal data export JSON files (`StreamingHistory*.json` or extended streaming history files).
  2. **Staging Area & Cloud Storage:** Securely stream and upload files to a temporary staging cloud storage bucket (`gs://.../staging/`).
  3. **Automated Parsing & Validation:** Background worker / ingestion pipeline parsing JSON scrobble records, validating timestamps, matching track metadata/URIs, and deduplicating against existing BigQuery `spotify_v2.playback_history`.
  4. **BigQuery Automated Merge:** Fully automated merge pipeline loading staged historical scrobbles into the tenant's partition in BigQuery and re-materializing user album features and Datastore catalog cache.
* **Effort & Complexity:** ~6–8 hours (1 day) • **Complexity:** **Medium**

---

#### `APP-14`: Headless API & Firestore/Datastore Catalog Rearchitecture (Phase 1)
* **Problem:**  
  SpinSleeve's Flask backend (`src/report_v2/app.py`) is currently monolithic, rendering Jinja2 HTML templates directly on the server. Supporting a native iOS companion app (`APP-15`) requires decoupling the presentation layer from backend logic, exposing clean REST/JSON endpoints, and ensuring sub-20ms latency for mobile client requests without increasing cloud spend.
* **Solution:**  
  1. **Headless API Route Layer (`/api/v1/...`):**
     - Refactor Flask application routes to expose structured JSON endpoints (`/api/v1/library`, `/api/v1/recommendations`, `/api/v1/analytics`, `/api/v1/pals`).
     - Share core BigQuery querying and data pipelines while completely decoupling HTML rendering from API responses.
  2. **Firebase Hosting CDN & Reverse Proxy Routing (`firebase.json`):**
     - Configure Firebase Hosting static asset hosting to serve frontend builds globally from CDN.
     - Set up declarative rewrites (`/api/**`) pointing to Cloud Run service (`spotify-dashboard-beta`, region `europe-west2`, `pinTag: true`).
  3. **Cloud Firestore / Datastore Document Store Caching:**
     - Utilize Cloud Datastore (`UserCatalogCache`) and gzipped document payloads to guarantee O(1) read latency (~15–20ms) for mobile library payloads.
* **Effort & Complexity:** ~12–16 hours (1.5–2 days) • **Complexity:** **Medium**

---

#### `APP-15`: Native iOS SwiftUI Companion App & Mobile Crate Browsing (Phase 2)
* **Problem:**  
  SpinSleeve collectors want a native, portable mobile experience on their iPhones to browse their virtual vinyl crate, check heavy rotation, audition 30-second audio previews, and view 12" gatefold liner notes without being tethered to a desktop web browser.
* **Solution:**  
  1. **Native Swift & SwiftUI Architecture:**
     - Built natively using Apple's declarative SwiftUI framework with smooth animations (33⅓ RPM rotating vinyl platters, gatefold slide-out sheets, and fluid navigation).
     - State management via `@Observable` and async/await `URLSession` networking communicating with Cloud Run `/api/v1/` endpoints.
  2. **Spotify OAuth PKCE on iOS:**
     - Secure authentication flow utilizing `ASWebAuthenticationSession` to authenticate users via Spotify and securely store tokens in iOS Keychain Services.
  3. **Core Mobile Features:**
     - **Virtual Vinyl Crate Explorer:** Lazy-loaded grid (`LazyVGrid`) of album sleeves with search, sorting (Heavy Rotation vs All-Time), and local image caching (Kingfisher / Nuke).
     - **30-Second Needle-Drop Audio Previews:** Integrated `AVPlayer` streaming snippet previews on card tap.
     - **12" Gatefold Archival Sheets:** Slide-up sheet presentation displaying Wikipedia summaries, Discogs/Pitchfork ratings, and tracklists.
     - **Played But Not Owned ("You Should Save These") Crate:** Mobile view for discovering unsaved heavy rotation records with 1-click save to Spotify.
  4. **Distribution & Testing:**
     - Local unit testing with XCTest, SwiftUI live previews, and automated TestFlight beta distribution.
* **Effort & Complexity:** ~20–30 hours (3–4 days) • **Complexity:** **Medium–High**

---

#### `APP-16`: Semantic Liner Notes & Description Classification for Crate Digger Relevance
* **Problem:**  
  Raw Spotify API genre tags give a jarring mix of broad tags ("Rock") and hyper-niche tags ("Kosmische Musik"), making Crate Digger discovery and vibe filtering noisy and imprecise.
* **Solution:**  
  1. **Enrichment Text Parsing (`src/pipeline_v2/enrich.py`):** Pass scraped Wikipedia and Discogs archival descriptions and gatefold liner notes through text classification, keyword scoring, and atmosphere extraction.
  2. **Derived Structured Attributes:** Automatically map unstructured narratives into clean macro-categories (`derived_moods`, `macro_genre`, `descriptive_tags`) during the daily enrichment pipeline.
  3. **Semantic Similarity & "If You Like This Gatefold..." Recommendations:** Vectorize narrative descriptions (via TF-IDF or lightweight keyword scoring) to power kindred spirit recommendations in Crate Digger even when official Spotify tags differ.
  4. **Zero-Latency Read Path:** Pre-computed BigQuery columns queried instantly by Crate Digger (`/recommend`) with zero runtime latency penalty.
* **Effort & Complexity:** ~6–8 hours (1 day) • **Complexity:** **Medium**

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

#### `APP-04`: Music Legend Illustrated Avatar Persona Picker [✅ Completed `v2.3.0`]
* **Problem:**  
  Users without custom Spotify profile pictures need recognizable, stylized artistic personas inside the vinyl club.
* **Solution:**  
  12 curated illustrated vector avatars of musical legends spanning two centuries of genres:
  - 🎹 Ludwig van Beethoven (*Classical / Romantic titan*)
  - 🎺 Chet Baker (*West Coast cool jazz noir*)
  - 🕶️ Miles Davis (*Kind of Blue modal jazz & Harmon mute*)
  - 🎸 Bob Dylan (*Greenwich Village folk & harmonica rack*)
  - ⚡ David Bowie (*Aladdin Sane lightning bolt*)
  - 🎹 Stevie Wonder (*Motown soul, braids & gold shades*)
  - 🎸 Jimi Hendrix (*Psychedelic purple afro & headband*)
  - 🎷 Fela Kuti (*Afrobeat clay face-paint & gold sax*)
  - 👑 Madonna (*80s pop lace bow & crucifix*)
  - 🎤 Amy Winehouse (*Camden beehive & winged eyeliner*)
  - 🤖 Daft Punk (*Chrome robot helmet & rainbow LED visor*)
  - 🦉 Drake (*Certified Lover Boy heart fade & OVO owl*)
  - Interactive click-to-open dropdown attached to the user avatar pill in navigation header.
  - 1-click selection updates Datastore `User` entity (`custom_avatar_id` & `avatar_url`), session cache, and all views in real time.
  - Option to revert back to original Spotify photo.
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

#### `APP-07`: Played But Not Owned ("You Should Save These") Library Crate [✅ Completed]
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

#### `POLISH-08`: Tab Navigation UX Simplification & Hardware Segmented Sub-Tab Deck
* **Problem:** Top-level navigation was cluttered with 4 separate tabs (`Library Explorer`, `Crate Digger`, `Analytics`, `SpinPals`). Crate Digger is functionally a discovery mode of the music collection, so separating it into a top-level tab created unnecessary navigation friction.
* **Solution:** 
  1. Streamline top-level navigation from 4 to 3 tabs (`Library`, `Analytics`, `SpinPals`).
  2. Nest **Crate Digger** under the Library Explorer domain as a sub-tab, placed between "My Saved Vinyl" and "You Should Save These" (leaving unowned recommendations as the rightmost subtab).
  3. Replace busy emojis with minimalist SVG line icons and a hardware-inspired segmented pill control deck (`spinsleeve_nav_mockup.html`).
* **Effort & Complexity:** ~2–3 hours • **Complexity:** **Low**

---

#### `POLISH-09`: Landing Page Version Number Alignment
* **Problem:** The version badge displayed on the landing page is hardcoded as `v2.3.0` instead of matching the current release version (`v2.5.0`).
* **Solution:** Update `APP_VERSION = "v2.5.0"` (or current release constant) in `src/report_v2/app.py`.
* **Effort & Complexity:** ~0.2 hours • **Complexity:** **Low (Trivial)**

---

#### `POLISH-10`: Consistent Header Navigation & Audio Toggle Across All Views
* **Problem:** Certain pages (such as landing/auth or auxiliary views) are missing the main tab selection bar (`Library | Analytics | SpinPals`) and/or audio controls in the header masthead.
* **Solution:** Standardize the persistent header masthead across all authenticated views so the tab bar and audio toggle are universally present.
* **Effort & Complexity:** ~1 hour • **Complexity:** **Low**

---

#### `POLISH-11`: Cross-Page Audio Mute State Persistence (`localStorage`)
* **Problem:** When hover audio is disabled by the user, the preference resets back to enabled (`ON`) upon navigating to another page.
* **Solution:** Save and load `isAudioEnabled` state using browser `localStorage` (`spinAudioEnabled`) across page transitions.
* **Effort & Complexity:** ~1 hour • **Complexity:** **Low**

---

#### `POLISH-12`: URL Parameter Tab Routing (`?tab=unowned` / `?tab=saved`)
* **Problem:** Visiting or clicking links with `?tab=unowned` (e.g. `https://spinsleeve.cc/beta/?tab=unowned`) sometimes still displays the default library view instead of switching to the unowned crate tab.
* **Solution:** Add DOMContentLoaded URLSearchParams query parameter parsing to automatically trigger `switchCrateTab('unowned')` or `switchCrateTab('saved')` on page load.
* **Effort & Complexity:** ~0.5 hours • **Complexity:** **Low**

---

#### `POLISH-13`: Mobile User Settings Menu Overflow & Positioning Fix
* **Problem:** The user settings and avatar dropdown menu in the header uses `absolute right-0 w-72`, causing it to overflow off the left side of the screen on narrow mobile viewports.
* **Solution:** Add responsive constraints (`max-w-[calc(100vw-2rem)] right-0 sm:right-0`) to ensure the settings dropdown stays safely within mobile viewport bounds.
* **Effort & Complexity:** ~0.5 hours • **Complexity:** **Low**

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
| **`OPS-03`** | Real-Time Admin Alerts for Join Requests | DevOps | 3–4h | Twilio WhatsApp API, Cloud Run | **Medium:** Instant 1-click mobile approvals for new friends. |
| **`APP-01`** | 12" Gatefold Tracklisting & Side A/B Splits | Core App | 4–6h | Spotify Web API, Jinja2, Tailwind CSS | **Medium:** Completes tactile physical record feel with track-level auditioning. |
| **`APP-02`** | Apple Music Library Onboarding (Phase 7) | Core App | 16–24h | MusicKit JS v3, Apple Developer Key (.p8), BigQuery | **Massive:** Bypasses Spotify allowlist limits and expands to Apple Music collectors. |
| **`APP-03`** | In-App Feedback & Wishlist Collector | Core App | 5–7h | Cloud Datastore (`Feedback`), Flask, Admin UI | **Medium:** Frictionless feedback loop directly from active listeners. |
| **`APP-04`** | Music Legend Illustrated Avatars | Core App | 4–5h | SVG Vector Graphics, Datastore, Tailwind CSS | **Low:** Aesthetic charm and personal flair for users without profile photos. |
| **`APP-05`** | ✅ ~~Album Sleeve Normalized Play Count Badge~~ | Core App | 2–3h | Jinja2, Tailwind CSS, JavaScript | ✅ **Completed** (Revision `00018-c67`): Normalized spins with flame badge, singular/plural formatting, and detailed hover tooltip across Library Explorer, Crate Digger, and SpinPals. |
| **`APP-06`** | ✅ ~~Crate Digger & SpinPals Dynamic Time Horizon~~ | Core App | 5–7h | BigQuery SQL, Python Flask, JavaScript | ✅ **Completed:** Rolling 30D play count aggregation in BQ view, 2-way horizon toggles in Crate Digger & SpinPals, and 30D library sort. |
| **`APP-07`** | ✅ ~~Played But Not Owned ("You Should Save These") Crate~~ | Core App | 4–6h | BigQuery SQL, Flask, Spotify API | ✅ **Completed** (`v2.4.0`: Revision `00032-6f2`): Uncovers streamed favourites missing from the vinyl shelf with amber dashed sleeves, multi-track rule, time horizons, and 1-click Spotify Search API library save. |
| **`APP-08`** | Full-Length Virtual Turntable Web Player | Core App | 8–12h | Spotify Web Playback SDK, CSS Keyframes, Web Audio | **High:** Immersive full-length streaming with vinyl disc sliding from sleeve onto rotating 33⅓ platter. |
| **`APP-09`** | Granular Track-Level Telemetry & Audio Archive | Core App | 6–8h | BigQuery SQL, Spotify Web API, Tailwind CSS, JavaScript | **Medium:** Granular track-level playback history, dynamic genre filtering, 30s needle-drop previews, and relative timestamps. |
| **`APP-10`** | Local Gig Radar: Top Artists Live in Your City | Core App | 6–8h | Bandsintown API, DICE Deep-Links, BigQuery SQL, Flask, Tailwind CSS | **High:** Connects vinyl listening telemetry to live concerts in the user's city with 1-click DICE checkout. |
| **`APP-11`** | Collector’s Inscriptions & Ratings | Core App | 5–7h | Cloud Datastore, BigQuery, Jinja2, Tailwind CSS | **High:** Personal 5-star ratings, handwritten liner notes, and dual OLTP/BigQuery storage for taste analysis. |
| **`APP-12`** | ✅ ~~Header Profile Dropdown, User Settings & Community Action Center~~ | Core App | 3–4h | Flask, Jinja2, Tailwind CSS | ✅ **Completed** (`v2.6.3`, Revision `00047-lqd`): SpinPals opt-in/out and Scrobble Sync Pause toggles, backend sync pause pipeline guard. |
| **`APP-13`** | ✅ ~~Spotify Full Scrobble Historical Data Upload & Ingestion~~ | Core App | 6–8h | Python, BigQuery, Jinja2 | ✅ **Completed** (`v2.5.0`: Revision `00034-6lq`): Extended and legacy GDPR JSON/ZIP streaming history ingestion with QA table reconciliation and UI settings integration. |
| **`APP-14`** | Headless API & Firestore/Datastore Catalog Rearchitecture (Phase 1) | Core App | 12–16h | Flask REST JSON API, Firebase CDN Reverse Proxy | **Medium:** Decouples Flask monolithic templates into clean REST endpoints and Firebase CDN proxy. |
| **`APP-15`** | Native iOS SwiftUI Companion App & Mobile Crate Browsing (Phase 2) | Core App | 20–30h | SwiftUI, Swift, Spotify OAuth PKCE | **High:** Native iOS app with Spotify OAuth PKCE authentication and 33⅓ RPM crate browsing. |
| **`APP-16`** | Semantic Liner Notes & Description Classification for Crate Digger Relevance | Core App | 6–8h | NLP Text Parsing, BigQuery Schema Expansion | **Medium:** Keyword scoring and text parsing to derive macro-genres and moods for Crate Digger relevance. |
| **`POLISH-01`** | ✅ ~~Harmonise "Heavy Rotation" Filter & Crate Digger UX~~ | Tactical Polish | 2–3h | Jinja2, JavaScript, Tailwind CSS | ✅ **Completed** (`v2.2.1`): Streamlined 2-tier console, single-dimension crate target, balanced vibes. |
| **`POLISH-02`** | ✅ ~~Library Explorer Heavy Rotation Initial Sort (Strict 30D on Load)~~ | Tactical Polish | 1h | JavaScript, DOM Lifecycle | ✅ **Completed** (`v2.2.2`): Initial sort triggers `onFilterChange()` on DOMContentLoaded for strict 30D heavy rotation sorting. |
| **`POLISH-03`** | ✅ ~~Play Count Badge Refinement (Decimal Plays / Newly Added)~~ | Tactical Polish | 1–2h | Python, Jinja2, JavaScript | ✅ **Completed** (`v2.2.2`): Decimal fractional scrobbles, integer whole spins, and contextual "Newly Added" / "Never Played" tags. |
| **`POLISH-04`** | ✅ ~~Semantic Build Version Numbering (Remove "beta v2")~~ | Tactical Polish | 1–2h | Flask, Jinja2, CI/CD | ✅ **Completed** (`v2.2.0`: Revision `00022-z5t`): Replaced static beta badge with dynamic semantic release version. |
| **`POLISH-05`** | ✅ ~~Clean Header Profile Avatar (Remove Admin Switcher)~~ | Tactical Polish | 1–2h | Jinja2, HTML5, Flask Session | ✅ **Completed** (Revision `00022-z5t`): Clean standard user avatar for all users; impersonation housed in Admin Portal. |
| **`POLISH-06`** | Admin Portal Table Column Alignment & Layout Polish | Tactical Polish | 1–2h | HTML5, Tailwind CSS | **Low:** Eliminates table misalignment, button wrapping, and truncation on admin portal. |
| **`POLISH-07`** | ✅ ~~De-duplicate Crate Digger "Spin Again" Header Button~~ | Tactical Polish | 0.5h | Jinja2, HTML5 | ✅ **Completed** (`v2.2.1`): Removed header duplicate; harmonized Control Deck button to "Spin Again". |
| **`POLISH-08`** | Tab Navigation UX Simplification & Hardware Sub-Tab Deck | Tactical Polish | 2–3h | Jinja2, Tailwind CSS, SVG, JS | **High:** Streamlines top-level navigation from 4 to 3 tabs by nesting Crate Digger under Library Explorer alongside Saved & Unowned crates with hardware-inspired segmented pill bar and minimalist SVG line icons (`spinsleeve_nav_mockup.html`). |
| **`BRAND-01`** | ✅ ~~Landing Page Redesign & Feature Showcase~~ | Brand & Growth | 6–8h | Tailwind CSS, HTML5, Responsive Screenshots | ✅ **Completed** (`v2.5.2`): Professional public landing page with feature showcase, authentic album artwork CDN integration, and admin test switchers. |
| **`BRAND-02`** | Buy Me a Coffee Integration | Monetization | 1–2h | BuyMeACoffee API / Embed, HTML | **Low:** Easy community support channel for hosting and API costs. |
| **`BRAND-03`** | ✅ ~~Public Roadmap & Release Transparency Portal (`/roadmap`)~~ | Brand & Growth | 3–4h | Flask, Jinja2, Tailwind CSS, Semantic Versioning | ✅ **Completed** (`v2.5.2`): Public release transparency portal at `/roadmap` showcasing shipped and upcoming features. |
| **`BRAND-04`** | ✅ ~~Software License & IP Protection Review~~ | Legal & Brand | 2–4h | PolyForm Noncommercial 1.0.0 | ✅ **Completed** (`v2.2.2`): Migrated repository to PolyForm Noncommercial 1.0.0 to prevent unauthorized commercial exploitation while keeping non-commercial use & contributions free. |
| **`DOCS-01`** | ✅ ~~Technical Architecture Map (README Overhaul)~~ | Documentation | 3–4h | Markdown, Mermaid Diagrams | ✅ **Completed**: Complete developer transparency and comprehensive system mapping with Mermaid topology diagram. |
