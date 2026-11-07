# SpinSleeve: Project Memory & Developer Guidelines

This file is automatically loaded by Gemini CLI at the start of every session in this workspace. It acts as the definitive persistent context, architectural source of truth, and project tracker.

---

## 1. Project Overview & Environments

* **Application:** **SpinSleeve** — A physical-style virtual vinyl crate, 12" gatefold archival liner notes reader, listening telemetry engine, and friend-to-friend taste compatibility platform.
* **Production URL:** `https://spinsleeve.cc` (live multi-tenant V2 application, Cloud Run service `spotify-dashboard-beta`).
* **Beta URL (Backwards Compatible):** `https://spinsleeve.cc/beta` (canonical root and `/beta/*` routes fully supported).
* **GCP Project ID:** `secret-compass-181513`
* **Compute Region:** `europe-west2` (London) for Cloud Run services, jobs, and Cloud Scheduler.
* **BigQuery Region:** `US` (Multi-region) for dataset `spotify_v2`.
* **User Vault:** Cloud Datastore (Kind: `User`, Key: Spotify ID).
* **Reverse Proxy & SSL:** Google Firebase Hosting site `secret-compass-181513` (routes `**` to `spotify-dashboard-beta`).

---

## 2. Non-Negotiable Architectural Invariants

1. **Multi-Tenancy & Data Isolation:**
   - Every analytical table in `spotify_v2` (`playback_history`, `user_saved_albums`) MUST filter and cluster by `user_id`.
   - The universal metadata table (`album_enriched_metadata`) is shared across all tenants to prevent duplicate scraping costs.
2. **Session Cookie Naming (Firebase Hosting):**
   - The Flask session cookie MUST be named exactly `__session` and use `path="/"`. Firebase Hosting strips all cookies except `__session`.
3. **Data Cleanliness & Zero `NaN`s:**
   - BigQuery/Pandas outputs containing `None` or `NaN` MUST be sanitized using `safe_str()`, `safe_int()`, and `safe_float()`.
   - Never serialize raw Pandas/NumPy `NaN` into JSON responses; browser native `JSON.parse` will throw fatal syntax errors.
4. **Spotify OAuth PKCE:**
   - Always instantiate `SpotifyOAuth(..., show_dialog=True)` to force the account chooser and prevent accidental cross-account token pollution.
   - Redirect URI: `https://spinsleeve.cc/beta/callback` (and `https://spinsleeve.cc/callback`).
5. **Admin Impersonation & Zero-Lockout:**
   - When an admin assumes a user view (`/admin/assume/<id>`), permissions strictly reflect the assumed user's flags so the admin can accurately test the unapproved/locked experience.
   - However, `admin_required` checks `session["admin_user_id"] in ADMIN_USER_IDS`, and all locked screens include an escape banner linking to `/admin/revert` and `/admin`, guaranteeing zero admin lockout.
6. **SpinPals Social Privacy Gate:**
   - New users default to `pals_opt_in: False` (Admins default to `True`).
   - `fetch_pals_directory()` strictly filters for `pals_opt_in == True`. Non-opted-in users receive `PALS_LOCKED_HTML` when accessing `/pals`.
7. **Brand Identity & Favicons:**
   - All headers and browser tabs feature the original 33⅓ RPM rotating vinyl platter SVG (`ICON_A_SVG`) with CSS keyframes, served dynamically via `/favicon.svg`.

---

## 3. Project File Map

* **`src/report_v2/app.py`:** Production multi-tenant Flask application:
  - `Library Explorer` (`/` & `/beta/`): Virtual record crate, 30s hover previews, 12" gatefold reader, sort by *Artist (A-Z), Albums (Year desc)*.
  - `Crate Digger` (`/recommend` & `/beta/recommend`): Discovery engine with vibe (*Chill, Energetic, Mellow, Vintage*), era, and subgenre filters.
  - `Analytics` (`/analytics` & `/beta/analytics`): Listening telemetry, "This Year" and custom date filters, listening clock heatmap, taste velocity.
  - `SpinPals: CrateMates` (`/pals` & `/beta/pals`): The Listening Lounge member directory, hybrid acoustic compatibility gauge, top 5 borrow recommendations, and virtual crate digging.
  - `Admin Control Deck` (`/admin` & `/beta/admin`): Whitelist pre-approvals, SpinPals opt-in toggles, and 1-click user view assumption.
* **`src/pipeline_v2/sync.py`:** Automated multi-tenant sync engine. Iterates approved Datastore users, refreshes individual tokens, and loads new plays/albums into `spotify_v2`.
* **`src/pipeline_v2/enrich.py`:** V2 album metadata enrichment pipeline. Scrapes Wikipedia and Discogs for 12" gatefold archival liner notes, ratings, and personnel into shared table `spotify_v2.album_enriched_metadata`.
* **`manage_users.py`:** Standalone CLI tool to list, approve, and revoke users in Datastore.
* **`INFRASTRUCTURE_RUNBOOK.md`:** Comprehensive disaster recovery guide with DDL, Cloud Run deploy commands, and Cloud Scheduler setups.
* **`PROJECT_ROADMAP_AND_SPECS.md`:** Product roadmap articulating the "WHAT" and "WHY" across all phases and categorized backlog (`INFRA`, `OPS`, `APP`, `POLISH`, `BRAND`, `DOCS`).
* **`TECHNICAL_SPECS.md`:** Comprehensive technical specifications detailing the "HOW" (schemas, API contracts, caching tiers, algorithms, and security boundaries).
* **`CHANGELOG.md`:** Reverse-engineered release journal documenting every deployed version, technical rationale, and benchmark.

---

## 4. Current State & Roadmap

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | Multi-Tenant BigQuery `spotify_v2` & Datastore Vault | ✅ COMPLETED |
| **Phase 2** | Spotify OAuth 2.0 PKCE, Firebase Reverse Proxy & Beta App | ✅ COMPLETED |
| **Phase 3** | Feature Parity: 30s Audio Previews, Crate Digger, Analytics | ✅ COMPLETED |
| **Phase 4** | Automated Multi-Tenant Pipeline (`spotify-v2-pipeline-job`) | ✅ COMPLETED |
| **Phase 5a** | Multi-User Social: **SpinPals (CrateMates Edition)** | ✅ COMPLETED (Deployed: revision `00012-rz4`) |
| **Phase 5b** | **Pre-Production Gatefold & Admin Polish** (Mobile <110px header, audio scrubber, SpinPals default-off with Admin opt-in, Admin 'assume view', 33 RPM spinning logo) | ✅ COMPLETED (Deployed: revision `00015-ql8`) |
| **Phase 6** | **Production Cutover** (Zero-downtime Firebase rewrite flip to `spinsleeve.cc`) | ✅ COMPLETED (Deployed: revision `00017-749`) |
| **APP-05** | **Normalized Album Play Count Badges** (`🔥 X Plays` badge, hover tooltips, normalized sorting) | ✅ COMPLETED (Deployed: revision `00018-c67`) |
| **APP-06** | **Dynamic Time Horizon** (Rolling 30D vs All-Time in Crate Digger & SpinPals, 30D library sort) | ✅ COMPLETED (Deployed: revision `00019-9ds`) |
| **INFRA-03a** | **Materialized Clustered Analytical Table** (`user_albums_features_table`, 2.3x query speedup) | ✅ COMPLETED (Deployed: revision `00020-vrw`) |
| **INFRA-03b** | **Cloud Datastore Document Store Cache** (`UserCatalogCache` gzipped document store, ~50ms cold loads) | ✅ COMPLETED (Deployed: revision `00021-42p`) |
| **Phase 6f** | **Header Polish & Semantic Versioning** (`POLISH-04`, `POLISH-05`) (v2.2.0 release badge, clean profile avatar) | ✅ COMPLETED (Deployed: revision `00022-z5t`) |
| **POLISH-01 & 07** | **Crate Digger UX & Controls Harmonisation** (Single-dimension targets, 2-tier console, balanced VIBES, album artist isolation, de-duplicated Spin Again) | ✅ COMPLETED (Deployed: revision `00024-mdp`, `v2.2.1`) |
| **Phase 7** | **Cross-Platform: Apple Music Library Collection Onboarding** (`APP-02`) | ⏳ Backlog |

*See `PROJECT_ROADMAP_AND_SPECS.md` for full categorized backlog: `INFRA` (Fresh GCP project, Terraform, Sub-100ms Caching & Materialization), `OPS` (CI/CD GitHub Actions, Cloud Monitoring, Telegram alerts), `APP` (Tracklisting, Apple Music, Normalized Plays, Heavy Rotation Toggle, Played Not Owned, Turntable Web Player, Granular Track Telemetry, Local Gig Radar), `POLISH` (Harmonised Heavy Rotation, 30D sorting fix, decimal plays, dynamic versioning, clean header, admin table alignment), `BRAND` (Landing redesign, Buy Me a Coffee, Public Roadmap Portal), and `DOCS` (Technical architecture map).*

## 5. Quick Commands

```bash
# Execute multi-tenant pipeline on-demand (scheduled: every 2h via spotify-v2-sync-scheduler)
gcloud run jobs execute spotify-v2-pipeline-job --region=europe-west2

# Execute V2 album metadata enrichment on-demand (scheduled: daily at 04:00 UTC via spotify-v2-enrichment-scheduler)
gcloud run jobs execute spotify-v2-enrichment-job --region=europe-west2 --args="enrich.py,100"

# Deploy updated beta app
CLOUDSDK_PYTHON=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
  gcloud builds submit src/report_v2 --tag=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-dashboard-v2:latest
gcloud run deploy spotify-dashboard-beta \
  --image=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-dashboard-v2:latest \
  --region=europe-west2

# Fast test accounts in header
# 👑 Serge: sergebou (Admin) | 👩 Sarah: sarahboosch | 🐹 GuineaPig: 31sevhztrcbajfcowsahl7z2p26q
```
