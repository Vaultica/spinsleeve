# SpinSleeve Technical Specifications & System Architecture Design

**Target Application:** SpinSleeve (`https://spinsleeve.cc`)  
**Production Platform:** Google Cloud Platform (`europe-west2`, London & `US` Multi-Region)  
**Document Purpose:** Definitive technical design and engineering architecture for all backlog features. This document articulates **HOW** each feature is engineered (schemas, API contracts, caching tiers, algorithms, and security boundaries), cleanly decoupled from the product roadmap's **WHAT** (user value and prioritization).

---

## Table of Contents
1. [Core Architectural Invariants](#1-core-architectural-invariants)
2. [Category: Infrastructure & Cloud Architecture (`INFRA`)](#2-category-infrastructure--cloud-architecture-infra)
   - [`INFRA-01`: Fresh GCP Project Migration & Environment Isolation](#infra-01-fresh-gcp-project-migration--environment-isolation)
   - [`INFRA-02`: Infrastructure as Code via Terraform](#infra-02-infrastructure-as-code-via-terraform)
   - [`INFRA-03`: Sub-100ms Multi-Tier Caching & Query Consolidation](#infra-03-sub-100ms-multi-tier-caching--query-consolidation)
3. [Category: DevOps, CI/CD, Observability & Reliability (`OPS`)](#3-category-devops-cicd-observability--reliability-ops)
   - [`OPS-01`: Automated GitHub Actions CI/CD Pipeline](#ops-01-automated-github-actions-cicd-pipeline)
   - [`OPS-02`: Cloud Monitoring Baseline, Alerting & Health Probes](#ops-02-cloud-monitoring-baseline-alerting--health-probes)
   - [`OPS-03`: Instant Admin Notifications for User Join Requests](#ops-03-instant-admin-notifications-for-user-join-requests)
4. [Category: Core Application & Vinyl Streaming (`APP`)](#4-category-core-application--vinyl-streaming-app)
   - [`APP-01`: 12" Gatefold Tracklisting & Side A / Side B Breakdown](#app-01-12-gatefold-tracklisting--side-a--side-b-breakdown)
   - [`APP-02`: Cross-Platform Apple Music Library Onboarding](#app-02-cross-platform-apple-music-library-onboarding)
   - [`APP-03`: In-App User Feedback & Liner Notes Wishlist Collector](#app-03-in-app-user-feedback--liner-notes-wishlist-collector)
   - [`APP-04`: Music Legend Illustrated Avatar Persona Engine](#app-04-music-legend-illustrated-avatar-persona-engine)
   - [`APP-07`: "Played But Not Owned" Discovery Crate](#app-07-played-but-not-owned-discovery-crate)
   - [`APP-08`: Full-Length Virtual Turntable Player (Spotify Web Playback SDK)](#app-08-full-length-virtual-turntable-player-spotify-web-playback-sdk)
5. [Category: Tactical Polish & UX Streamlining (`POLISH`)](#5-category-tactical-polish--ux-streamlining-polish)
   - [`POLISH-02`: Library Explorer 30-Day Sort Initialization Fix](#polish-02-library-explorer-30-day-sort-initialization-fix)
   - [`POLISH-03`: Normalized Decimal Play Count & Contextual Badges](#polish-03-normalized-decimal-play-count--contextual-badges)
   - [`POLISH-06`: Admin Portal Table Formatting & Column Alignment](#polish-06-admin-portal-table-formatting--column-alignment)
6. [Category: Brand Identity, Public Landing & Monetization (`BRAND`)](#6-category-brand-identity-public-landing--monetization-brand)
   - [`BRAND-01`: Public Landing Page & Feature Showcase Architecture](#brand-01-public-landing-page--feature-showcase-architecture)
   - [`BRAND-02`: Buy Me a Coffee Supporter Integration](#brand-02-buy-me-a-coffee-supporter-integration)
7. [Category: Technical Documentation (`DOCS`)](#7-category-technical-documentation-docs)
   - [`DOCS-01`: Comprehensive Architecture Blueprint (Mermaid Topology)](#docs-01-comprehensive-architecture-blueprint-mermaid-topology)

---

## 1. Core Architectural Invariants

All new features and architectural changes must strictly adhere to these verified invariants:

1. **Multi-Tenancy & Composite Key Isolation:**
   - Every analytical table in BigQuery (`playback_history`, `user_saved_albums`, `user_albums_features_table`) MUST partition and cluster by `user_id`.
   - All joins and aggregations matching album titles MUST join on composite key `(LOWER(TRIM(album_name)), LOWER(TRIM(artist_name)))` to prevent homonymous collision.
   - The archival liner notes table (`album_enriched_metadata`) is universal and keyed strictly by `album_id` to eliminate redundant scraping across tenants.
2. **Session Cookie Naming:**
   - The Flask session cookie MUST be named exactly `__session` with `path="/"`. Firebase Hosting SSL reverse proxy drops all cookies that do not match `__session`.
3. **Data Sanitization & JSON Safety:**
   - BigQuery/Pandas outputs containing `None`, `NaN`, or `NaT` MUST pass through sanitization helpers (`safe_str()`, `safe_int()`, `safe_float()`) prior to serialization. Raw `NaN` values cause fatal browser-side `JSON.parse` exceptions.
4. **Zero-Lockout Admin Guarantee:**
   - Admin routes require `session.get("admin_user_id") in ADMIN_USER_IDS`. Locked user states must always provide an unauthenticated or escape banner linking to `/admin/revert`.

---

## 2. Category: Infrastructure & Cloud Architecture (`INFRA`)

### `INFRA-01`: Fresh GCP Project Migration & Environment Isolation
* **Technical Objective:** Provision a clean, dedicated GCP project (`spinsleeve-prod`), establishing strict IAM boundaries, isolating billing, and shedding legacy test resources.
* **Architecture & Migration Sequence:**
  1. **New GCP Project Provisioning:** Create project `spinsleeve-prod` attached to master billing account.
  2. **API Enablement:**
     ```bash
     gcloud services enable run.googleapis.com \
                            bigquery.googleapis.com \
                            datastore.googleapis.com \
                            secretmanager.googleapis.com \
                            cloudscheduler.googleapis.com \
                            cloudbuild.googleapis.com \
                            artifactregistry.googleapis.com \
                            --project=spinsleeve-prod
     ```
  3. **IAM Least-Privilege Service Accounts:**
     - `spinsleeve-app-sa@spinsleeve-prod.iam.gserviceaccount.com`: Assigned `roles/datastore.user`, `roles/bigquery.dataViewer`, `roles/bigquery.jobUser`, `roles/secretmanager.secretAccessor`.
     - `spinsleeve-pipeline-sa@spinsleeve-prod.iam.gserviceaccount.com`: Assigned `roles/datastore.user`, `roles/bigquery.admin`, `roles/secretmanager.secretAccessor`.
  4. **Data Migration Pipeline:**
     - BigQuery: Copy dataset `secret-compass-181513.spotify_v2` to `spinsleeve-prod.spotify_v2` via BigQuery Data Transfer Service or cross-project table copy:
       ```sql
       CREATE SNAPSHOT TABLE `spinsleeve-prod.spotify_v2.playback_history`
       CLONE `secret-compass-181513.spotify_v2.playback_history`;
       ```
     - Datastore: Export `User` entities to Cloud Storage bucket, import into `spinsleeve-prod` via `gcloud datastore import`.
  5. **Custom Domain Cutover:** Re-link Firebase Hosting site `spinsleeve` to domain `spinsleeve.cc`. Zero downtime achieved via pre-warmed Cloud Run service.

---

### `INFRA-02`: Infrastructure as Code via Terraform
* **Technical Objective:** Codify 100% of cloud resources into declarative, version-controlled HCL configurations under `/terraform`.
* **Module Structure:**
  ```text
  terraform/
  ├── main.tf                 # Provider setup & module orchestration
  ├── variables.tf            # Project ID, region, image tags
  ├── outputs.tf              # Service URLs and resource IDs
  ├── backend.tf              # GCS locked remote state
  └── modules/
      ├── bigquery/           # Datasets, tables, clustering, scheduled views
      ├── cloud_run/          # Cloud Run service & Cloud Run Jobs
      ├── datastore/          # Composite indexes (index.yaml)
      ├── scheduler/          # Cron triggers (Sync every 2h, Enrichment daily)
      ├── secrets/            # Secret Manager placeholders
      └── iam/                # Service accounts & IAM role bindings
  ```
* **State Management:** Remote state stored in Google Cloud Storage bucket `gs://spinsleeve-prod-tfstate` with Cloud Storage object versioning enabled for state locking.

---

### `INFRA-03`: Sub-100ms Multi-Tier Caching & Query Consolidation
* **Technical Objective:** Complete the remaining tiers of `INFRA-03` to drop load times across all views to <50ms.
* **Component Specs:**
  1. **`INFRA-03c`: SpinPals Multi-Query Consolidation & Pal Caching:**
     - *Consolidation:* Eliminate the 3 sequential BigQuery roundtrips in `compute_pal_compatibility()`. Run a single query returning both pal albums and current user library overlap in one pass:
       ```sql
       WITH current_user_albums AS (
         SELECT album_id, 1 as owns
         FROM `spotify_v2.user_saved_albums`
         WHERE user_id = @current_user_id
       )
       SELECT f.*, COALESCE(c.owns, 0) as current_user_owns
       FROM `spotify_v2.user_albums_features_table` f
       LEFT JOIN current_user_albums c ON f.album_id = c.album_id
       WHERE f.user_id = @pal_id;
       ```
     - *Tier 2 Cache:* Store pal compatibility calculations in Datastore `Kind: PalCompatibilityCache` keyed by `f"{user_id}::{pal_id}::{horizon}"` (gzipped binary payload, 24h TTL). Invalidate automatically upon `sync.py` completion.
  2. **`INFRA-03d`: Analytics Listening Telemetry Datastore Cache:**
     - Cache pre-aggregated analytics JSON (listening clock heatmap, era distributions, top artists, fresh vs repeat ratios) in Datastore `Kind: UserAnalyticsCache`.
     - Key format: `f"{user_id}::{range_param}::{genre_param}"`.
     - Invalidate automatically when `sync.py` writes new scrobbles for that user.
  3. **`INFRA-03e`: Browser `sessionStorage` & Instant Client-Side Tab Switching:**
     - Cache serialized user catalog payload in browser `sessionStorage.setItem('spinsleeve_catalog', ...)`.
     - When user switches between `/` (Library) and `/recommend` (Crate Digger), the view renders immediately from local memory (<10ms), eliminating full 2.5 MB HTML re-transfers.

---

## 3. Category: DevOps, CI/CD, Observability & Reliability (`OPS`)

### `OPS-01`: Automated GitHub Actions CI/CD Pipeline
* **Technical Objective:** Automate testing, linting, container builds, and deployment on every commit to `master`.
* **Workflow Specifications:**
  1. **Continuous Integration (`.github/workflows/ci.yml`):**
     - Triggers: Pull requests targeting `master`.
     - Matrix: Python 3.10 and 3.11.
     - Steps:
       ```bash
       pip install -r src/report_v2/requirements.txt
       python -m unittest discover -s tests
       ```
     - Enforce branch protection rule: Merges blocked unless all 51+ unit tests pass.
  2. **Continuous Deployment (`.github/workflows/deploy.yml`):**
     - Triggers: Direct push / PR merge to `master`.
     - Authentication: **Google Cloud Workload Identity Federation** (zero static JSON keys stored in GitHub Secrets).
     - Execution:
       ```bash
       gcloud builds submit src/report_v2 --tag=europe-west2-docker.pkg.dev/...
       gcloud run deploy spotify-dashboard-beta --image=...
       ```

---

### `OPS-02`: Cloud Monitoring Baseline, Alerting & Health Probes
* **Technical Objective:** Automated monitoring of service degradation, quotas, and background job failures.
* **Specifications:**
  - **Health Probe:** Add `@app.route("/healthz")` executing lightweight read verification against Datastore and BigQuery (`SELECT 1`).
  - **Uptime Check:** Cloud Monitoring HTTP check probing `https://spinsleeve.cc/healthz` every 60 seconds from 3 worldwide regions.
  - **Alert Policies:**
    - HTTP 5xx Error Rate > 2% over a 5-minute rolling window.
    - Cloud Run CPU saturation > 85% for 10 minutes.
    - Cloud Run Job `spotify-v2-pipeline-job` exit code != 0.
  - **Notification Channels:** Automated email dispatch to `serge.bouschet@gmail.com` with incident runbook link.

---

### `OPS-03`: Instant Admin Notifications for User Join Requests
* **Technical Objective:** Push real-time mobile notifications when a new user signs in for the first time.
* **Webhook Payload & Architecture:**
  - Triggered in `src/report_v2/app.py` inside the OAuth callback (`/beta/callback`) when a new `User` entity is written with `is_approved=False`.
  - Service: Telegram Bot API (`https://api.telegram.org/bot<TOKEN>/sendMessage`).
  - Message Template:
    ```text
    🔔 New SpinSleeve Collector Request!
    • Name: {display_name}
    • Spotify ID: {spotify_id}
    • Email: {email}
    👉 1-Click Approval: https://spinsleeve.cc/admin
    ```

---

## 4. Category: Core Application & Vinyl Streaming (`APP`)

### `APP-01`: 12" Gatefold Tracklisting & Side A / Side B Breakdown
* **Technical Objective:** Embed complete vinyl tracklists into the 12" gatefold modal with physical disc breakdown and inline audio previews.
* **Data Ingestion & Caching (Approved Hybrid Model & Option A):**
  - **Primary API:** Spotify Web API `sp.album_tracks(album_id)`.
  - **Endpoint:** `GET /beta/api/album/<album_id>/tracks`
  - **Storage:** Cloud Datastore `Kind: AlbumTracksCache` (shared across all tenants, 30-day TTL). Zero BigQuery DDL migrations.
* **Vinyl Side Splitting Algorithm:**
  ```python
  def split_vinyl_sides(tracks):
      # Discs grouped by disc_number
      discs = {}
      for t in tracks:
          discs.setdefault(t["disc_number"], []).append(t)
      
      sides = {}
      side_letters = ["A", "B", "C", "D", "E", "F"]
      side_idx = 0
      for disc_num in sorted(discs.keys()):
          disc_tracks = discs[disc_num]
          n = len(disc_tracks)
          half = (n + 1) // 2  # Ceiling half
          sides[f"Side {side_letters[side_idx]}"] = disc_tracks[:half]
          side_idx += 1
          sides[f"Side {side_letters[side_idx]}"] = disc_tracks[half:]
          side_idx += 1
      return sides
  ```
* **Inline Needle-Drop Auditioning:**
  - Clicking any track name calls `playTrackSnippet(track_id, track_name, artist_name)`.
  - Uses Spotify `preview_url` if present, falling back to `/beta/api/preview?artist={artist}&track={track}` (iTunes Search API).

---

### `APP-02`: Cross-Platform Apple Music Library Onboarding
* **Technical Objective:** Support Apple Music subscribers via Apple MusicKit JS v3, expanding collector community beyond Spotify's 25-user sandbox limit.
* **Architecture & Authentication:**
  1. **Developer Key & Token Generation:**
     - Apple Developer Account MusicKit private key (`.p8`), Team ID, Key ID.
     - Server generates developer bearer JWT (`exp`: 180 days).
  2. **Client-Side Authorization:**
     - Initialize `MusicKit.configure({ developerToken, app: { name: 'SpinSleeve', build: '2.2.1' } })`.
     - User authorizes via Apple Music modal (`musicKit.authorize()`), returning `userToken`.
  3. **Data Ingestion:**
     - Fetch user's saved catalog via `https://api.music.apple.com/v1/me/library/albums`.
     - Ingest albums and scrobbles into `spotify_v2.user_saved_albums` tagged with `platform='apple_music'`.

---

### `APP-03`: In-App User Feedback & Liner Notes Wishlist Collector
* **Technical Objective:** Provide a seamless, in-app feedback channel for collectors to report missing liner notes, incorrect artwork, or feature ideas.
* **Data Model & Schema:**
  - **Datastore Kind:** `Feedback`
  - **Properties:**
    - `user_id` (STRING)
    - `user_display_name` (STRING)
    - `album_id` (STRING, optional)
    - `category` (STRING: `liner_notes`, `bug`, `feature`, `general`)
    - `message` (TEXT)
    - `created_at` (TIMESTAMP)
    - `resolved` (BOOLEAN, default: False)
* **UI Integration:** Discreet "Suggest Correction" link inside the 12" gatefold back sleeve footer, opening a compact modal.

---

### `APP-04`: Music Legend Illustrated Avatar Persona Engine
* **Technical Objective:** Assign stylized, retro-illustrated music legend avatars (Miles Davis, Kate Bush, David Bowie, Nina Simone) to users who lack Spotify profile photos.
* **Implementation:**
  - Vector SVG avatars housed in `src/report_v2/static/avatars/`.
  - Deterministic fallback algorithm: Hash `user_id` modulo avatar pool size to assign a signature legend avatar automatically.
  - User selection preserved in Datastore `User.custom_avatar_slug`.

---

### `APP-07`: "Played But Not Owned" Discovery Crate
* **Technical Objective:** Surface albums the user streams heavily on Spotify but has not saved to their vinyl collection library.
* **Analytical SQL Query:**
  ```sql
  WITH played_albums AS (
    SELECT 
      album_id,
      album_name,
      artist_name,
      COUNT(*) as total_plays,
      MAX(played_at) as last_played
    FROM `spotify_v2.playback_history`
    WHERE user_id = @user_id AND album_id IS NOT NULL AND album_id != ""
    GROUP BY album_id, album_name, artist_name
    HAVING total_plays >= 5
  )
  SELECT p.*
  FROM played_albums p
  LEFT JOIN `spotify_v2.user_saved_albums` s
    ON s.user_id = @user_id AND p.album_id = s.album_id
  WHERE s.album_id IS NULL
  ORDER BY p.total_plays DESC
  LIMIT 50;
  ```
* **UI Action:** "Save to Shelf" button issuing `PUT https://api.spotify.com/v1/me/albums?ids={album_id}` via user's refresh token.

---

### `APP-08`: Full-Length Virtual Turntable Player (Spotify Web Playback SDK)
* **Technical Objective:** Immersive in-browser full-length record player where the vinyl disc physically slides out of the 12" gatefold sleeve and drops onto a rotating 33⅓ platter.
* **Architecture:**
  1. **SDK Initialization:**
     - Inject `https://sdk.scdn.co/spotify-player.js`.
     - Initialize `Spotify.Player({ name: 'SpinSleeve Turntable', getOAuthToken: cb => ... })`.
  2. **Turntable Canvas & Web Audio Animation:**
     - CSS Keyframes rotating vinyl platter at 33.33 RPM (`animation: spin 1.8s linear infinite`).
     - Needle arm SVG rotates inward dynamically according to track progress:
       $$\theta(t) = \theta_{\text{start}} + \left(\frac{t}{t_{\text{total}}}\right) \cdot (\theta_{\text{end}} - \theta_{\text{start}})$$
  3. **Playback Control:**
     - Clicking any gatefold track transfers playback to the Web SDK device ID via `PUT https://api.spotify.com/v1/me/player/play`.

---

## 5. Category: Tactical Polish & UX Streamlining (`POLISH`)

### `POLISH-02`: Library Explorer 30-Day Sort Initialization Fix
* **Technical Problem:** In `BETA_EXPLORER_HTML`, the dropdown shows `🔥 Heavy Rotation (Last 30 Days)` selected by default, but `DOMContentLoaded` runs `renderGrid()` instead of `onFilterChange()`. Because BigQuery returns albums ordered by all-time plays, the initial view is sorted by all-time favorites.
* **Implementation Fix:**
  ```javascript
  document.addEventListener("DOMContentLoaded", () => {
      onFilterChange(); // Evaluates sortSelect and applies plays_30d_desc immediately
  });
  ```
* **Tiebreaker Determinism:** Enforce primary sort on `album_normalized_plays_30d DESC`, secondary on `album_track_plays_30d DESC`, and tertiary on `album_track_plays DESC`.

---

### `POLISH-03`: Normalized Decimal Play Count & Contextual Badges
* **Technical Problem:** Albums with <1 full spin or zero plays show a bare `🔥 0 Plays` badge.
* **Implementation Fix:**
  - Update `compute_normalized_album_plays(track_plays, tracks_total)`:
    - If `track_plays == 0`: return badge `Newly Added` or `Unplayed` (gray badge).
    - If `0 < track_plays < tracks_total`: return decimal spins, e.g. `🔥 0.4 Plays` (amber badge).
    - If `track_plays >= tracks_total`: return integer full spins with fractional precision on hover.

---

### `POLISH-06`: Admin Portal Table Formatting & Column Alignment
* **Technical Objective:** Eliminate text wrapping, misaligned buttons, and inconsistent padding in `/admin`.
* **CSS & Layout Adjustments:**
  - Apply fixed column widths: `w-1/4` (Collector), `w-1/4` (Email), `w-1/6` (Approval Status), `w-1/6` (SpinPals Flag), `w-1/6` (Actions).
  - Add `whitespace-nowrap` to action buttons and truncate user email with native hover tooltip.

---

## 6. Category: Brand Identity, Public Landing & Monetization (`BRAND`)

### `BRAND-01`: Public Landing Page & Feature Showcase Architecture
* **Technical Objective:** Editorial public landing page at `/login` showcasing the virtual vinyl ritual before sign-in.
* **Structure:**
  - Unauthenticated visitors hitting `/` or `/login` receive `PUBLIC_LANDING_HTML`.
  - Live interactive demo component: Clickable mini-gatefold showing high-resolution sleeve opening and needle-drop audio preview.
  - Manifest narrative and feature grid (Library, Crate Digger, Analytics, SpinPals).

---

### `BRAND-02`: Buy Me a Coffee Supporter Integration
* **Technical Objective:** Community support widget to offset Google Cloud BigQuery and Cloud Run hosting costs.
* **Integration Points:**
  - Floating footer widget: `https://cdnjs.buymeacoffee.com/1.0.0/widget.prod.min.js`.
  - Subtle graphic badge embedded in the 12" gatefold archival liner notes reader footer.

---

## 7. Category: Technical Documentation (`DOCS`)

### `DOCS-01`: Comprehensive Architecture Blueprint (Mermaid Topology)
* **Technical Objective:** Production-grade `README.md` overhaul containing comprehensive architecture diagrams, disaster recovery steps, and module topologies.
* **Mermaid System Diagram:**
  ```mermaid
  graph TD
      A[Client Browser] -->|SSL HTTPS| B[Firebase Hosting Proxy]
      B -->|Forward __session| C[Cloud Run: spotify-dashboard-beta]
      C -->|Read / Write Users| D[Cloud Datastore: User Vault]
      C -->|Sub-50ms Document Cache| E[Cloud Datastore: UserCatalogCache]
      C -->|Clustered Analytics| F[(BigQuery: user_albums_features_table)]
      G[Cloud Scheduler] -->|Every 2h| H[Cloud Run Job: spotify-v2-pipeline-job]
      H -->|Ingest Scrobbles| I[(BigQuery: playback_history)]
      H -->|Ingest Library| J[(BigQuery: user_saved_albums)]
      H -->|Re-materialize| F
      K[Cloud Scheduler] -->|Daily 04:00 UTC| L[Cloud Run Job: spotify-v2-enrichment-job]
      L -->|Scrape Discogs / Wiki| M[(BigQuery: album_enriched_metadata)]
  ```
