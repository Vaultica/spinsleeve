# SpinSleeve: Project Memory & Developer Guidelines

This file is automatically loaded by Gemini CLI at the start of every session in this workspace. It acts as the definitive persistent context, architectural source of truth, and project tracker.

---

## 1. Project Overview & Environments

* **Application:** **SpinSleeve** — A physical-style virtual vinyl crate, 12" gatefold archival liner notes reader, listening telemetry engine, and friend-to-friend taste compatibility platform.
* **Production URL:** `https://spinsleeve.cc` (currently routing to single-user V1).
* **Beta URL (Multi-Tenant V2):** `https://spinsleeve.cc/beta` (Cloud Run service `spotify-dashboard-beta`).
* **GCP Project ID:** `secret-compass-181513`
* **Compute Region:** `europe-west2` (London) for Cloud Run services, jobs, and Cloud Scheduler.
* **BigQuery Region:** `US` (Multi-region) for dataset `spotify_v2`.
* **User Vault:** Cloud Datastore (Kind: `User`, Key: Spotify ID).
* **Reverse Proxy & SSL:** Google Firebase Hosting (routes `/beta/**` to beta, `**` to prod).

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
   - Redirect URI: `https://spinsleeve.cc/beta/callback`.

---

## 3. Project File Map

* **`src/report_v2/app.py`:** Multi-tenant Flask application:
  - `Library Explorer` (`/beta/`): Virtual record crate, 30s hover previews, 12" gatefold reader, sort by *Artist (A-Z), Albums (Year desc)*.
  - `Crate Digger` (`/beta/recommend`): Discovery engine with vibe (*Chill, Energetic, Mellow, Vintage*), era, and subgenre filters.
  - `Analytics` (`/beta/analytics`): Listening telemetry, "This Year" and custom date filters, listening clock heatmap, taste velocity.
  - `SpinPals: CrateMates` (`/beta/pals`): The Listening Lounge member directory, hybrid acoustic compatibility gauge, top 5 borrow recommendations, and virtual crate digging.
  - `Admin Control Deck` (`/beta/admin`): Whitelist pre-approvals and toggle access for friends.
* **`src/pipeline_v2/sync.py`:** Automated multi-tenant sync engine. Iterates approved Datastore users, refreshes individual tokens, and loads new plays/albums into `spotify_v2`.
* **`manage_users.py`:** Standalone CLI tool to list, approve, and revoke users in Datastore.
* **`INFRASTRUCTURE_RUNBOOK.md`:** Comprehensive disaster recovery guide with DDL, Cloud Run deploy commands, and Cloud Scheduler setups.
* **`PROJECT_ROADMAP_AND_SPECS.md`:** Product specification covering completed phases, upcoming roadmap, and future feature designs.

---

## 4. Current State & Roadmap

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | Multi-Tenant BigQuery `spotify_v2` & Datastore Vault | ✅ COMPLETED |
| **Phase 2** | Spotify OAuth 2.0 PKCE, Firebase Reverse Proxy & Beta App | ✅ COMPLETED |
| **Phase 3** | Feature Parity: 30s Audio Previews, Crate Digger, Analytics | ✅ COMPLETED |
| **Phase 4** | Automated Multi-Tenant Pipeline (`spotify-v2-pipeline-job`) | ✅ COMPLETED |
| **Phase 5a** | Multi-User Social: **SpinPals (CrateMates Edition)** | ✅ COMPLETED (Deployed: revision `00012-rz4`) |
| **Phase 5b** | **Pre-Production Gatefold & Admin Polish** (Mobile <110px header, audio scrubber, SpinPals default-off with Admin opt-in, Admin 'assume view', 33 RPM spinning logo) | ✅ COMPLETED |
| **Phase 6** | **Production Cutover** (Zero-downtime Firebase rewrite flip to `spinsleeve.cc`) | ⏳ **CURRENT NEXT FOCUS** |
| **Phase 7** | **Cross-Platform: Apple Music Library Collection Onboarding** (MusicKit JS & BQ Sync) | ⏳ Planned |

---

## 5. Quick Commands

```bash
# Execute multi-tenant pipeline on-demand
gcloud run jobs execute spotify-v2-pipeline-job --region=europe-west2

# Deploy updated beta app
CLOUDSDK_PYTHON=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
  gcloud builds submit src/report_v2 --tag=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-dashboard-v2:latest
gcloud run deploy spotify-dashboard-beta \
  --image=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-dashboard-v2:latest \
  --region=europe-west2

# Fast test accounts in header
# 👑 Serge: sergebou (Admin) | 👩 Sarah: sarahboosch | 🐹 GuineaPig: 31sevhztrcbajfcowsahl7z2p26q
```
