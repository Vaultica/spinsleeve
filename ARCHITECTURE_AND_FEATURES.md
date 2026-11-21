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
