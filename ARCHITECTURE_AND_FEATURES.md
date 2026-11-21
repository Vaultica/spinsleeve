# SpinSleeve V2: System Architecture, Existing Features & "As-Built" Ledger

This document serves as the definitive technical reference for SpinSleeve's **existing ("as-built") features, pipeline mechanics, and architectural rationales**, decoupled from future roadmaps and release specs.

---

## Table of Contents
1. [Core Architectural Invariants](#1-core-architectural-invariants)
2. [Module Topology & Blueprint Separation](#2-module-topology--blueprint-separation)
3. [Existing Features & User Workflows ("As-Built")](#3-existing-features--user-workflows-as-built)
   - [Library Explorer (`/crate`) & Normalized Play Counts](#library-explorer-crate--normalized-play-counts)
   - [Smart Crate Digger (`/recommend`) & Time Horizons](#smart-crate-digger-recommend--time-horizons)
   - [SpinPals Social CrateMates (`/pals`) & Acoustic Chemistry](#spinpals-social-cratemates-pals--acoustic-chemistry)
   - [12" Gatefold Archival Reader & Needle-Drop Preview](#12-gatefold-archival-reader--needle-drop-preview)
   - [Spotify Full Scrobble Historical Upload (`APP-13`)](#spotify-full-scrobble-historical-upload-app-13)
4. [Deep-Dive: Metadata Enrichment Pipeline (`src/pipeline_v2/enrich.py`)](#4-deep-dive-metadata-enrichment-pipeline-srcpipeline_v2enrichpy)
   - [Pipeline Execution Flow](#pipeline-execution-flow)
   - [Wikipedia & Discogs Scraping Mechanics](#wikipedia--discogs-scraping-mechanics)
   - [Root Causes of Sparse Data & Missing Gatefolds](#root-causes-of-sparse-data--missing-gatefolds)
5. [Architectural & Design Decision Rationale](#5-architectural--design-decision-rationale)
6. [Physical Data Models, Schemas & Constraints](#6-physical-data-models-schemas--constraints)
   - [BigQuery Multi-Tenant Dataset (`spotify_v2`)](#bigquery-multi-tenant-dataset-spotify_v2)
   - [Cloud Datastore Entities (NoSQL Cache & Auth Vault)](#cloud-datastore-entities-nosql-cache--auth-vault)

---

## 1. Core Architectural Invariants

1. **Strict Layer & Blueprint Separation:** Flask route blueprints (`src/report_v2/routes/*.py`) MUST only handle HTTP parsing, session checks, and rendering. All data access and business logic live in `src/report_v2/services/*.py`.
2. **Multi-Tenancy & Partition Guardrails:** Every query and DML operation on tenant tables (`playback_history`, `user_saved_albums`, `user_albums_features_table`) MUST filter and cluster by `user_id`.
3. **Composite Album Key Sibling Deduplication:** Album joins and queries MUST use composite key `(LOWER(TRIM(album_name)), LOWER(TRIM(artist_name)))` and `canonical_album_key` regex normalization to collapse variant releases (*Deluxe*, *Remastered*, *Anniversary*).
4. **Cache Invalidation Discipline:** State-mutating actions (sync completion, GDPR upload, settings toggles) MUST invalidate affected Datastore cache keys (`UserCatalogCache`, `PalCompatibilityCache`, `UserAnalyticsCache`).
5. **Zero `NaN` Serialization:** BigQuery/Pandas outputs MUST pass through sanitization helpers (`safe_str()`, `safe_int()`, `safe_float()`) prior to JSON serialization.

---

## 2. Module Topology & Blueprint Separation

```text
src/report_v2/
├── app.py                  # Flask entrypoint, middleware, error handlers, blueprint registration
├── app_config.py           # Global version constants, admin IDs, asset registry
├── routes/                 # Thin HTTP controllers (auth, crate, analytics, pals, admin)
├── services/               # Core data access, BQ queries, Datastore caching, recommendation engine
└── templates/              # Jinja2 HTML templates and modal components
```

---

## 3. Existing Features & User Workflows ("As-Built")

### Library Explorer (`/crate`) & Normalized Play Counts
* **Workflow:** Displays user's saved albums as a virtual vinyl crate with tactile card covers, eras, and play badges.
* **Normalized Play Calculation:** Computed as $\lfloor \text{track\_plays} / \text{tracks\_total} \rfloor$ with zero-track fallback (`APP-05`), displaying badges like `🔥 X Plays` and hover breakdowns estimating complete album spins.

### Smart Crate Digger (`/recommend`) & Time Horizons
* **Workflow:** Algorithmic discovery engine surfacing albums collectors played but do not own (*"You Should Save These"*), filterable by vibe (*Late Night/Chill, Energetic, Mellow, Vintage*), era, subgenre, and dynamic 2-way time horizon (`🔥 Heavy Rotation (Last 30 Days)` vs `🏛️ All-Time Collection`).

### SpinPals Social CrateMates (`/pals`) & Acoustic Chemistry
* **Workflow:** Community directory and taste compatibility gauge (50% artist overlap + 50% album overlap) assigning kinship badges (*Vinyl Soulmates, Acoustic Kin, Crate Companions*), Top 5 borrow recommendations, and virtual crate comparison (`🤝 Both Own`).

### 12" Gatefold Archival Reader & Needle-Drop Preview
* **Workflow:** Interactive modal opening album liner notes, Wikipedia prose summaries, Discogs personnel credits, critic scores (Pitchfork, Metacritic, AllMusic, Guardian), and 30-second needle-drop audio preview snippets with animated soundwaves and progress scrubbers.

### Spotify Full Scrobble Historical Upload (`APP-13`)
* **Workflow:** In-memory ZIP/JSON streaming history parser supporting Extended and Legacy GDPR formats (`StreamingHistory_music_*.json`), filtering podcasts and short scrobbles (<30s) with year-by-year BigQuery batching and duplicate prevention.

---

## 4. Deep-Dive: Metadata Enrichment Pipeline (`src/pipeline_v2/enrich.py`)

### Pipeline Execution Flow
1. **Candidate Query:** Selects unenriched albums from `user_saved_albums` ordered by total play count and collector count.
2. **Search Normalization (`clean_search_term`):** Strips edition suffixes (`(remastered)`, `(deluxe)`, `(anniversary)`, `[edition]`) via regular expressions.
3. **Wikipedia Scraping (`fetch_wikipedia_data`):**
   - Queries MediaWiki search API for `"{clean_artist} {clean_album} album"`.
   - Fetches REST summary and parses wikitext infoboxes for review scores (`MC`, `Pitchfork`, `AllMusic`, `Guardian`).
4. **Discogs Scraping (`fetch_discogs_data`):**
   - Queries Discogs `/database/search` and fetches release details for **`results[0]`** (top hit).
   - Extracts community ratings, genres/styles, release notes, and up to 20 personnel credits (`extraartists`).
5. **BigQuery Append:** Stitches enriched data into `spotify_v2.album_enriched_metadata`.

### Root Causes of Sparse Data & Missing Gatefolds
* **Rigid Wikipedia Infobox Parsing:** Wikipedia articles lacking standard `infobox album` templates or custom rating variables fail regex extraction, resulting in blank critic scores.
* **Discogs First-Result Blindness (`results[0]`):** Automatically picking the top search result without verifying format can land on a compilation, cassette, or foreign edition lacking liner notes or personnel credits.
* **Niche/Independents Gap:** Underground releases often lack dedicated Wikipedia pages and have sparse Discogs contributor entries.
* **Title Variation Mismatches:** Subtitles, special characters, or alternate naming conventions can cause search queries to miss relevant articles.

---

## 5. Architectural & Design Decision Rationale

* **Composite Album Key Sibling Deduplication:** Merging edition variants (*RAM* vs *RAM (Archive Collection)*) via regex normalization (`canonical_album_key`) prevents telemetry double-counting and clutter in library explorer and recommendations.
* **Cloud Datastore Document Store Cache (`UserCatalogCache`):** Gzip-compressing cached catalog JSON payloads reduced cold load latency from ~3,800ms down to ~50ms (70x speedup) at zero additional infrastructure cost.
* **BigQuery Partition & Cluster Guardrails:** Partitioning and clustering tenant tables by `user_id` ensures O(1) multi-tenant isolation and strict ad-hoc cost limits (`maximum_bytes_billed`).
* **Zero-Lockout Admin Session Assumption (`/admin/assume/<id>`):** Housing impersonation strictly within the admin portal with persistent revert banners guarantees administrative security without user lockout risk.

---

## 6. Physical Data Models, Schemas & Constraints

SpinSleeve employs a hybrid persistence tier: **Google BigQuery** for partitioned relational telemetry and materialization, and **Google Cloud Datastore** for transactional user state and gzipped document caching.

```
┌────────────────────────────────────────────────────────┐
│                   Cloud Datastore                      │
│  User (Auth/Flags)  •  UserCatalogCache (Gzip Blob)    │
│  PalCompatibilityCache  •  UserAnalyticsCache          │
└───────────────────────────▲────────────────────────────┘
                            │ (Sub-100ms Read Tier)
┌───────────────────────────┴────────────────────────────┐
│                    Google BigQuery                     │
│  playback_history       (Partition: DATE, Cluster: UID)│
│  user_saved_albums      (Cluster: UID, artist_name)    │
│  album_enriched_metadata(Global Universal Table)       │
│  user_albums_features_table (Materialized Cluster: UID)│
└────────────────────────────────────────────────────────┘
```

### BigQuery Multi-Tenant Dataset (`spotify_v2`)
* **GCP Project:** `secret-compass-181513` | **Location:** `US` Multi-Region | **Dataset:** `spotify_v2`

#### 1. Table `playback_history` (Partitioned Listening Telemetry)
* **Storage Model:** Append-only physical time-series table.
* **Partitioning:** `PARTITION BY DATE(played_at)`
* **Clustering:** `CLUSTER BY user_id, artist_name`
* **Deduplication Key:** Composite `(user_id, track_id, played_at)`

| Column | Type | Mode | Constraints & Notes |
| :--- | :--- | :--- | :--- |
| `user_id` | `STRING` | **`REQUIRED`** | Unique Spotify user ID (e.g., `sergebou`). Tenant isolation partition key. |
| `played_at` | `TIMESTAMP` | **`REQUIRED`** | UTC timestamp of the scrobble event. |
| `track_uri` | `STRING` | `NULLABLE` | Spotify Track URI format: `spotify:track:[A-Za-z0-9]{22}`. |
| `track_id` | `STRING` | `NULLABLE` | Spotify 22-character base62 track identifier. |
| `track_name` | `STRING` | `NULLABLE` | Track title as reported by Spotify Web API. |
| `artist_id` | `STRING` | `NULLABLE` | Primary artist Spotify 22-character identifier. |
| `artist_name` | `STRING` | `NULLABLE` | Display name of the primary performing artist. |
| `album_id` | `STRING` | `NULLABLE` | Spotify 22-character base62 album identifier. |
| `album_name` | `STRING` | `NULLABLE` | Album title associated with the track playback event. |
| `canonical_album_key` | `STRING` | `NULLABLE` | Sibling normalization key format: `{artist}::{album_clean}`. |

* **Ingestion Filters:** Short scrobbles under 30 seconds (`ms_played < 30000`) and podcast/non-music streams (`episode == true`) are filtered out prior to insertion.

---

#### 2. Table `user_saved_albums` (Tenant Library State)
* **Storage Model:** Physical state table representing saved albums in user libraries.
* **Clustering:** `CLUSTER BY user_id, artist_name`
* **Uniqueness Key:** Composite `(user_id, album_id)`

| Column | Type | Mode | Constraints & Notes |
| :--- | :--- | :--- | :--- |
| `user_id` | `STRING` | **`REQUIRED`** | Tenant Spotify ID. |
| `album_id` | `STRING` | **`REQUIRED`** | Spotify 22-character album ID. |
| `album_uri` | `STRING` | `NULLABLE` | Format: `spotify:album:[A-Za-z0-9]{22}`. |
| `album_name` | `STRING` | **`REQUIRED`** | Album display name. |
| `artist_id` | `STRING` | `NULLABLE` | Primary artist Spotify ID. |
| `artist_name` | `STRING` | **`REQUIRED`** | Artist display name. |
| `added_at` | `TIMESTAMP` | `NULLABLE` | UTC timestamp when the user saved the album to Spotify library. |
| `release_date` | `STRING` | `NULLABLE` | Standard release date string (`YYYY`, `YYYY-MM`, or `YYYY-MM-DD`). |
| `release_year` | `INT64` | `NULLABLE` | Range: `[1900, 2100]`. Extracted 4-digit year. |
| `tracks_total` | `INT64` | `NULLABLE` | Range: $\ge 1$. *(Filtered to $> 2$ in vinyl crate views to exclude singles).* |
| `album_type` | `STRING` | `NULLABLE` | Allowed values: `album`, `single`, `compilation`. |
| `label` | `STRING` | `NULLABLE` | Record label, imprint, or copyright owner. |
| `image_url` | `STRING` | `NULLABLE` | High-res album artwork URL (`https://i.scdn.co/image/...`). |
| `genres` | `STRING` | `NULLABLE` | Comma-separated list of artist genres extracted from Spotify catalog. |
| `canonical_album_key` | `STRING` | `NULLABLE` | Sibling normalization key format: `{artist}::{album_clean}`. |

---

#### 3. Table `album_enriched_metadata` (Universal Shared Catalog)
* **Storage Model:** Global, multi-tenant shared table keyed by `album_id`.
* **Primary Key:** `album_id`

| Column | Type | Mode | Constraints & Notes |
| :--- | :--- | :--- | :--- |
| `album_id` | `STRING` | **`REQUIRED`** | Unique Spotify album ID (Global Primary Key). |
| `album_name` | `STRING` | `NULLABLE` | Canonical album title. |
| `artist_name` | `STRING` | `NULLABLE` | Canonical artist title. |
| `album_description` | `STRING` | `NULLABLE` | Lead paragraph summary from Wikipedia. |
| `wikipedia_url` | `STRING` | `NULLABLE` | Desktop Wikipedia article URL. |
| `pitchfork_score` | `FLOAT64` | `NULLABLE` | Range: `[0.0, 10.0]`. Rating extracted from Wikipedia review box. |
| `metacritic_score` | `INT64` | `NULLABLE` | Range: `[0, 100]`. Normalized Metacritic rating. |
| `allmusic_score` | `FLOAT64` | `NULLABLE` | Range: `[0.0, 5.0]`. Star rating extracted from AllMusic reviews. |
| `discogs_rating` | `FLOAT64` | `NULLABLE` | Range: `[0.0, 5.0]`. Community rating from Discogs. |
| `discogs_votes` | `INT64` | `NULLABLE` | Range: $\ge 0$. Count of community ratings on Discogs. |
| `personnel` | `STRING` | `NULLABLE` | Bulleted liner notes formatted as `Musician (Role) • Producer (Role)`. |
| `discogs_url` | `STRING` | `NULLABLE` | Discogs release URL (`https://www.discogs.com/release/...`). |
| `styles` | `STRING` | `NULLABLE` | Comma-separated physical styles (e.g., `Shoegaze, Indie Rock, Lo-Fi`). |

---

#### 4. Table `user_albums_features_table` (Materialized Presentation Layer)
* **Storage Model:** Physical materialized table refreshed by `rematerialize_user_albums_features()`.
* **Clustering:** `CLUSTER BY user_id`
* **Presentation Invariants:**
  - Excludes standalone singles via `WHERE COALESCE(tracks_total, 0) > 2`.
  - Deduplicates edition variants via dynamic SQL regex partitioning on `(user_id, canonical_album_key)`.
  - Calculates normalized play counts: $\lfloor \text{track\_plays} / \text{tracks\_total} \rfloor$.

---

### Cloud Datastore Entities (NoSQL Cache & Auth Vault)

#### 1. Kind `User` (User Authentication & Permission Entity)
* **Key Format:** String Key = `spotify_id` (e.g., `Key('User', 'sergebou')`).

| Property | Datastore Type | Indexing | Allowed Values & Constraints |
| :--- | :--- | :--- | :--- |
| `spotify_id` | `String` | Indexed | Unique Spotify user ID. |
| `display_name` | `String` | Unindexed | User's public display name. |
| `email` | `String` | Unindexed | Spotify account email. |
| `avatar_url` | `String` | Unindexed | URL to active avatar (SVG preset or Spotify CDN image). |
| `spotify_avatar_url` | `String` | Unindexed | Original Spotify profile image URL. |
| `custom_avatar_id` | `String` | Unindexed | Allowed values: `""`, `spotify`, `david_bowie`, `miles_davis`, `daft_punk`, `nina_simone`, `kraftwerk`, `bjork`, `kate_bush`, `joy_division`, `aphex_twin`. |
| `is_approved` | `Boolean` | Indexed | `True` for approved beta access; `False` gates to `/pending`. |
| `role` | `String` | Indexed | Allowed values: `admin`, `user`. |
| `pals_opt_in` | `Boolean` | Indexed | `True` enables directory listing in SpinPals (`/pals`); `False` defaults private. |
| `sync_paused` | `Boolean` | Indexed | `True` causes background sync jobs to skip this user; `False` active. |
| `refresh_token` | `String` | Unindexed | Spotify OAuth 2.0 refresh token used for background ingestion. |
| `sync_status` | `String` | Indexed | Allowed values: `idle`, `pending`, `syncing`, `failed`. |
| `created_at` | `Timestamp` | Unindexed | UTC registration timestamp. |
| `last_login_at` | `Timestamp` | Unindexed | UTC last authentication timestamp. |

---

#### 2. Kind `UserCatalogCache` (Gzip Library Document Cache)
* **Key Format:** String Key = `user_id` (e.g., `Key('UserCatalogCache', 'sergebou')`).
* **TTL Policy:** 86,400 seconds (24 hours); invalidated on sync completion or `?clear_cache=1`.

| Property | Datastore Type | Indexing | Notes |
| :--- | :--- | :--- | :--- |
| `compressed_payload` | `Blob` (`bytes`) | **Unindexed** | Gzip-compressed UTF-8 JSON payload containing the complete list of albums. |
| `album_count` | `Integer` | Indexed | Count of albums in the cached catalog. |
| `uncompressed_kb` | `Float` | Unindexed | Payload size before gzip compression. |
| `compressed_kb` | `Float` | Unindexed | Payload size stored in Datastore (~7.5x compression ratio). |
| `updated_at` | `Timestamp` | Indexed | UTC cache write timestamp. |

---

#### 3. Kind `PalCompatibilityCache` (Gzip Social Matching Cache)
* **Key Format:** String Key = `{current_user_id}::{pal_id}::{horizon}` (e.g., `sergebou::sarahboosch::30d`).
* **TTL Policy:** 86,400 seconds (24 hours).

| Property | Datastore Type | Indexing | Notes |
| :--- | :--- | :--- | :--- |
| `compressed_payload` | `Blob` (`bytes`) | **Unindexed** | Gzip-compressed JSON payload (acoustic compatibility %, kinship badge, top 5 borrow recommendations, shared albums). |
| `updated_at` | `Timestamp` | Indexed | UTC cache write timestamp. |

---

#### 4. Kind `UserAnalyticsCache` (Gzip Telemetry Cache)
* **Key Format:** String Key = `{user_id}::{range_param}` (e.g., `sergebou::30d`).
* **TTL Policy:** 86,400 seconds (24 hours).

| Property | Datastore Type | Indexing | Notes |
| :--- | :--- | :--- | :--- |
| `compressed_payload` | `Blob` (`bytes`) | **Unindexed** | Gzip-compressed JSON payload (KPI cards, listening heatmap, repeat vs discovery, eras, top artists/albums/tracks). |
| `updated_at` | `Timestamp` | Indexed | UTC cache write timestamp. |

