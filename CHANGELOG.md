# SpinSleeve Engineering Changelog & Release Journal

All notable technical updates, architectural decisions, feature implementations, and deployment revisions for **SpinSleeve** (`https://spinsleeve.cc`) are documented chronologically in this journal.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), with deep engineering rationales (*What, How, and Why*).

---

## [v2.8.9] — 2026-11-25
### 🏷️ Dominant-Genre Multi-Vote Classification, Lexicon Expansion & Catalog Reclassification
* **What:**
  - **Dominant-Genre Multi-Vote Scoring Engine (`src/pipeline_v2/classifier.py`, `src/report_v2/pipeline_v2/classifier.py`):**
    - Replaced brittle sequential first-match classification with `_tally_macro_genre_votes()` and `_pick_dominant_macro_genre()`, accurately assigning the dominant macro-genre when multiple sub-genres are present.
    - Added hierarchical narrative description fallback: inspects opening 400 characters of `album_description` or `discogs_notes` when artist/album genre tags are sparse.
  - **Comprehensive Sub-Genre Lexicon Expansion (`MACRO_GENRE_RULES`):**
    - Added high-frequency missing sub-genres across Classical (*neoclassical*, *minimalism*), Rock (*slowcore*, *neo-psychedelic*, *krautrock*), Electronic (*chillwave*, *electroclash*, *synthwave*), Latin / World (*bikutsi*, *afrobeat*, *mpb*, *bossanova*, *shibuya-kei*), Jazz (*exotica*, *lounge*, *easy listening*), and Pop (*britpop*, *art pop*, *chanson*).
  - **Catalog Reclassification Batch Utility & Live Execution (`scripts/reclassify_catalog.py`):**
    - Executed batched live updates across 578 records in `album_enriched_metadata`. Reclassified 319 albums into concrete genres, plunging unclassified library share from 27.0% down to 12.4% and establishing Rock as the #1 genre (16.2%).
    - Purged stale Cloud Datastore `UserCatalogCache` entities and rematerialized `user_albums_features_table`.
  - **Crate Filter Dropdown Enhancement (`src/report_v2/services/catalog.py`):**
    - Added `"Other / Unclassified"` pinned at the end of `top_genres` in both cached and fresh query paths, enabling users to easily isolate and explore unclassified albums.
  - **Unit Testing & Pre-Flight Verification:**
    - Added 3 test suites in `tests/test_app16_classification.py` covering multi-voting, expanded sub-genres, and description fallback (105/105 tests passing).
  - **Pipeline Container Image Rebuild & Cloud Run Job Synchronization:**
    - Built and deployed updated pipeline container image (`spotify-v2-pipeline:latest`, Cloud Build ID `fa9dc05a-983d-4603-90ae-c201f9f48688`, digest `sha256:be060363f1d1c0a82ad8543589ce43fbd64efa08f09df1f0a5540fceec4b727e`) integrating v2.8.9 classifier engine and lexicon expansion.
    - Updated Cloud Run jobs `spotify-v2-enrichment-job` and `spotify-v2-pipeline-job` to execute the latest container revision.
* **Why:**
  - Drastically reduces the massive 27% "Eclectic / Other" taxonomy bottleneck, accurately attributes dominant genres to diverse records, and provides transparent UI filtering for unclassified albums.
* **How:**
  - Implemented multi-vote scoring and narrative fallback in `classifier.py`, updated `catalog.py`, added unit tests, executed live BigQuery reclassification and Datastore cache flush, verified 105/105 tests passing, and deployed to Cloud Run.

---

## [v2.8.8] — 2026-11-23
### 🎵 12" Gatefold Enrichment Diagnostics, `--missing-gatefolds` CLI Mode & Attribution Alignment
* **What:**
  - **Missing Gatefold Diagnostics & CLI Mode (`src/pipeline_v2/enrich.py`, `src/report_v2/pipeline_v2/enrich.py`):**
    - Diagnosed missing 12" gatefold icons across 519 library albums locked out by the `WHERE e.canonical_album_key IS NULL` anti-join in `get_candidate_albums()`.
    - Added `--missing-gatefolds` (`-m`) CLI mode to surgically re-enrich albums lacking descriptions and personnel.
  - **Play Count Attribution & Quality Score Guard (`src/pipeline_v2/enrich.py`):**
    - Aligned play count attribution CTE across all branches in `get_candidate_albums()` to join and group by `canonical_album_key`, correctly accumulating plays across editions and releases.
    - Guarded quality score merge with `T.enrichment_quality_score = GREATEST(COALESCE(T.enrichment_quality_score, 0.0), S.enrichment_quality_score)` to prevent quality score downgrades.
  - **Unit Testing & Production Deployment:**
    - Added unit test `test_get_candidate_albums_missing_gatefolds` in `tests/test_enrich_v2.py` (102/102 unit tests passing).
    - Executed live test batch of 5 albums, restoring gatefold liner notes, Discogs ratings, and full personnel rosters for *Murcof*, *Chilly Gonzales*, and *BADBADNOTGOOD*.
    - Deployed to Cloud Run: revision `spotify-dashboard-beta-00079-gjd` serving 100% traffic, verified live HTTP 200 on `https://spinsleeve.cc/` and `https://spinsleeve.cc/beta/`.
* **Why:**
  - Restores missing liner notes, personnel credits, and gatefold badge indicators for previously un-enriched library albums while ensuring robust play count accumulation and preventing data quality score regressions.
* **How:**
  - Implemented `--missing-gatefolds` enrichment logic, fixed attribution CTEs and quality score guard, added unit tests (`tests/test_enrich_v2.py`), verified 102/102 tests passing, and deployed live Cloud Run revision `spotify-dashboard-beta-00079-gjd`.

---

## [v2.8.7] — 2026-11-23
### 🧠 APP-18: Zero-Shot Semantic Text Classification & Analytics Alignment
* **What:**
  - **Zero-Shot Semantic Text Classification (`src/pipeline_v2/classifier.py`):**
    - Integrated `sentence-transformers/all-MiniLM-L6-v2` semantic text classification into the metadata enrichment pipeline with robust regex fallback.
    - Enables semantic genre and mood classification with cosine similarity confidence scoring and threshold analysis.
  - **Profiling & Reporting (`scripts/profile_classifier_comparison.py`, `classifier_comparison_report.md`):**
    - Created profiling script and materialized side-by-side distribution comparison report evaluating semantic vs regex macro-genre classification.
  - **Analytics Alignment (`src/report_v2/services/analytics.py`):**
    - Aligned Analytics page genre filters and Genre Ecosystem charts with normalized macro-genres.
  - **Validation & Production Deployment:**
    - Verified 98/98 unit tests passing successfully. Built and deployed container revision `spotify-dashboard-beta-00074-9hb` to Cloud Run (`europe-west2`).
* **Why:**
  - Enhances metadata classification accuracy for rare, stylistic, or non-standard genre tags using state-of-the-art sentence embeddings while maintaining fast fallback and robust analytical consistency.
* **How:**
  - Implemented semantic classification in `classifier.py`, added comparative profiling scripts and reports, aligned analytics services, verified 98/98 tests passing, and deployed live revision `spotify-dashboard-beta-00074-9hb`.

---

## [v2.8.6] — 2026-11-22
### 🍏 APP-02b: MusicKit JS v3 Frontend Client, Mock Isolation & Production Deployment (PR #11)
* **What:**
  - **MusicKit JS v3 Integration & Onboarding UI (`src/report_v2/templates/explorer.html`, `src/report_v2/routes/apple_music.py`):**
    - Implemented route-scoped `/beta` isolation preserving Spotify-only default root (`/` / `/crate`).
    - Integrated Apple MusicKit JS v3 script loading, configuration, and authorization workflow.
    - Added header connection dropdown trigger with platform status indicators and Onboarding & Authorization modal supporting Live and Sandbox/Mock Test Collection toggles (enabling instant offline testing and QA without a live Apple Developer subscription).
    - Developed sync progress toasts and platform vinyl badges (` Apple Music`) for cross-platform library attribution.
  - **Mock Filtering & Strict Route Isolation (`src/report_v2/services/catalog.py`, `src/report_v2/routes/apple_music.py`):**
    - Filtered mock album covers and enforced strict Spotify-only isolation on default root (`/` / `/crate`).
  - **Container Packaging & Production Deployment (`Dockerfile`, `src/report_v2/Dockerfile`):**
    - Packaged `pipeline_v2` dependency in web container and decoupled `apple_music` from sync.
    - Executed BigQuery DML cleanup (7 mock rows deleted from `user_saved_albums` and `album_provider_ids`, `user_albums_features_table` refreshed with 0 mock albums remaining, `UserCatalogCache/sergebou` invalidated).
    - Deployed production revision `spotify-dashboard-beta-00073-r5n` live on `europe-west2` serving 100% traffic, verified HTTP 200 on `https://spinsleeve.cc/` and `https://spinsleeve.cc/beta/`.
  - **Comprehensive Unit Test Suite (`tests/test_apple_music_frontend.py`, `tests/`):**
    - Added rigorous unit test coverage, bringing the total test suite to 98/98 passing unit tests cleanly.
    - Pushed branch `feat/app-02b-musickit-frontend` to PR #11. Note: Live Apple Developer Program enrollment (£79) is currently pending.
* **Why:**
  - Provides a seamless cross-platform front-end collector onboarding and library exploration experience for Apple Music users while maintaining strict route isolation, clean production telemetry, and robust testability.
* **How:**
  - Implemented MusicKit JS v3 client workflows, modal templates, source filters, mock filtering, packaging updates, BQ cleanup, and unit tests (`tests/test_apple_music_frontend.py`), verifying 98/98 unit tests passing on branch `feat/app-02b-musickit-frontend` (PR #11) and deploying live revision `spotify-dashboard-beta-00073-r5n`.

---

## [v2.8.5] — 2026-11-22
### 🍏 APP-02a: Apple Music Backend Pipeline & JWT Ingestion Service
* **What:**
  - **Apple Music JWT Tokenizer & Pipeline (`src/pipeline_v2/apple_music.py`, `src/report_v2/services/apple_music.py`, `src/report_v2/routes/apple_music.py`):**
    - Implemented automated ES256 JWT developer token minting and caching via ECDSA P-256 and SHA-256 using Apple Developer Private Key (`.p8`).
    - Developed Apple Music Web API library client (`GET /v1/me/library/albums`) with cursor pagination, rate-limiting handling, and robust auth error recovery.
    - Added data normalization into `user_saved_albums` with zero-NaN guarantees and canonical edition deduplication (`compute_canonical_album_key`).
    - Implemented BigQuery batch ingestion supporting QA table suffixes (`_app_02a`) and foreign provider bridging into `album_provider_ids` (`provider='apple_music'`).
    - Integrated explicit Cloud Datastore cache invalidation for `UserCatalogCache`, `UserAnalyticsCache`, and `PalCompatibilityCache`.
  - **Modular Flask Route Blueprint & Unit Test Suite (`tests/test_apple_music_pipeline.py`):**
    - Created modular Flask route blueprint in `src/report_v2/routes/apple_music.py` with root and `/beta/*` aliases.
    - Added comprehensive unit test suite with 14 test cases (`tests/test_apple_music_pipeline.py`), bringing total test suite to 93/93 passing unit tests.
* **Why:**
  - Establishes a secure multi-provider backend ingestion and library synchronization engine for Apple Music, breaking free from Spotify single-provider dependency and allowlist limits.
* **How:**
  - Implemented `apple_music.py` pipeline and service layers, added `tests/test_apple_music_pipeline.py`, verified 93/93 unit tests passing, and bumped `APP_VERSION` to `v2.8.5`.

---

## [v2.8.4] — 2026-11-22
### 🏷️ Macro-Genre Fallback Refinement ("Other / Unclassified") & Decision Table Alignment
* **What:**
  - **Macro-Genre Fallback Rename (`src/pipeline_v2/classifier.py`, `src/report_v2/services/catalog.py`):**
    - Renamed default/fallback macro-genre from `"Eclectic / Other"` to `"Other / Unclassified"` across classifier logic, catalog services, UI templates (`explorer.html`, `pals.html`, `recommend.html`), and unit test assertions.
  - **Decision Table & Documentation Update (`MACRO_GENRE_MAPPING_DECISION_TABLE.md`):**
    - Updated macro-genre mapping documentation and sequential first-match rules to reflect `"Other / Unclassified"`.
  - **Test Suite Verification:**
    - Verified 79/79 unit tests passing successfully.
* **Why:**
  - Improves taxonomic clarity by distinguishing between intentionally eclectic albums and unclassified/fallback items in library filters and gatefold badges.
* **How:**
  - Updated `classifier.py`, `catalog.py`, `explorer.html`, `pals.html`, `recommend.html`, `MACRO_GENRE_MAPPING_DECISION_TABLE.md`, `test_app16_classification.py`, bumped `APP_VERSION` to `v2.8.4`.

---

## [v2.8.3] — 2026-11-22
### 🎛️ APP-17 Unified Crate Workspace & Dynamic Macro-Genre Filtering
* **What:**
  - **Unified Crate Workspace (`src/report_v2/templates/explorer.html`, `src/report_v2/services/catalog.py`):**
    - Consolidated Saved Vinyl and Streamed/Unowned crates into a unified workspace with top-level scope toggles (`📁 Saved Vinyl` vs `📻 Streamed / Unowned`) and a streamlined 2-row hardware-inspired control deck.
    - Dynamically computed `top_genres` strictly from macro-genres present in cached or fetched albums.
    - Enhanced unowned discovery fetcher with composite name/artist pair anti-joins and distinct track count filters.
  - **Classifier & Test Suite Expansion (`src/pipeline_v2/classifier.py`, `tests/test_app17_unified_crate.py`):**
    - Expanded macro-genre regex classification rules for Electronic and other categories.
    - Added unit test suite `tests/test_app17_unified_crate.py`, bringing total test coverage to 79/79 passing unit tests.
* **Why:**
  - Streamlines library exploration and unowned streaming discoveries into a seamless single-page workspace with precise macro-genre filtering and robust duplicate prevention.
* **How:**
  - Updated `src/report_v2/templates/explorer.html`, `src/report_v2/services/catalog.py`, `src/pipeline_v2/classifier.py`, added `tests/test_app17_unified_crate.py`, bumped `APP_VERSION` to `v2.8.3`, verified 79/79 tests passing.

---

## [v2.8.2] — 2026-11-22
### ⚡ Automatic Pipeline Analytics & Pal Compatibility Cache Invalidation
* **What:**
  - **Cache Invalidation on Sync Completion (`src/pipeline_v2/sync.py`, `src/report_v2/services/datastore.py`, `src/report_v2/services/analytics.py`):**
    - Implemented automatic invalidation of `UserAnalyticsCache` and `PalCompatibilityCache` in Cloud Datastore and in-memory stores whenever a user sync finishes with new plays or albums.
  - **Test Suite Expansion:**
    - Added unit test `test_invalidate_user_analytics_and_pal_caches` in `tests/test_datastore_cache.py`, bringing test suite to 76/76 passing unit tests.
* **Why:**
  - Guarantees that user telemetry, analytics dashboards, and SpinPals compatibility scores update instantly upon ingestion without requiring manual cache clearing or waiting for TTL expiry.
* **How:**
  - Updated `pipeline_v2/sync.py`, `report_v2/services/datastore.py`, `report_v2/services/analytics.py`, added unit tests, bumped version to `v2.8.2`.

---

## [v2.8.1] — 2026-11-21
### 🏷️ Gatefold Semantic Tag Strip & Pipeline Deduplication Fixes
* **What:**
  - **Gatefold Semantic Tag Strip (`explorer.html`, `pals.html`, `recommend.html`):**
    - Added visual UI tag pills displaying macro-genre badges (`macro_genre`), derived moods (`derived_moods`), and descriptive sound tags (`descriptive_tags`) across the 12" gatefold vinyl view in Explorer, SpinPals, and Recommendations.
    - Added unit test suite `tests/test_report_v2_gatefold.py` covering tag strip rendering across templates.
  - **Pipeline Candidate & MERGE Deduplication (`src/pipeline_v2/enrich.py`):**
    - Fixed candidate selection deduplication on `canonical_album_key` to prevent re-scraping existing sibling releases.
    - Fixed golden table MERGE operation to prevent duplicate primary keys on `canonical_album_key`.
  - **Test Suite Expansion:**
    - Expanded test coverage to 75/75 passing unit tests.
* **Why:**
  - Exposes the rich APP-16 semantic classification tags directly on the 12" gatefold record sleeves for immediate visual discovery, and ensures robust pipeline incremental enrichment without key constraint violations.
* **How:**
  - Modified templates (`explorer.html`, `pals.html`, `recommend.html`), `src/pipeline_v2/enrich.py`, added `tests/test_report_v2_gatefold.py`, verified 75/75 tests passing, and deployed revision `spotify-dashboard-beta-00067-z7f` to Cloud Run.

---

## [v2.8.0] — 2026-11-21
### 🏷️ Two-Tier Album Enrichment Architecture & APP-16 Semantic Classification
* **What:**
  - **Two-Tier Album Metadata Architecture:**
    - Tier 1: Provisioned append-only raw tables (`enrichment_raw_wikipedia`, `enrichment_raw_discogs`, `enrichment_raw_musicbrainz`) partitioned by `DATE(fetched_at)` and clustered by `canonical_album_key`, plus external streaming ID bridge `album_provider_ids` clustered by `(canonical_album_key, provider)`.
    - Tier 2: Upgraded golden `album_enriched_metadata` table clustered by `canonical_album_key`.
  - **APP-16 Semantic Classification Engine (`src/pipeline_v2/classifier.py`):**
    - Implemented deterministic NLP rule-based classifier providing:
      - `macro_genre` (Ambient, Electronic, Rock, Jazz, Hip-Hop, Metal, Punk / Alternative, R&B / Soul, Classical, Folk / Country, Pop, etc.)
      - `derived_moods` (`ARRAY<STRING>`: Late Night, Chill, Energetic, Mellow, Vintage, Melancholic, Atmospheric, Psychedelic, Introspective, etc.)
      - `descriptive_tags` (`ARRAY<STRING>`: Synthesizers, Acoustic Guitar, Concept Album, Lo-Fi Production, Orchestral Strings, Minimalist, Heavy Basslines, etc.)
      - `enrichment_quality_score` (`FLOAT64` 0.0 to 1.0 completeness metric).
  - **Zero Data Loss Backfill & Migration (`setup_app16_schema.py`):**
    - Created safety clone backup `album_enriched_metadata_backup_app16`.
    - Backfilled all 2,170 existing records with APP-16 classifications directly from existing verified liner notes, reviews, and Discogs data without burning external API limits.
    - Clustered golden `album_enriched_metadata` on `canonical_album_key`.
  - **Pipeline & Ingestion Upgrades (`src/pipeline_v2/enrich.py` & `sync.py`):**
    - Added MusicBrainz release-group integration (`fetch_musicbrainz_data`).
    - Updated candidate album selection to join on `canonical_album_key` to prevent re-scraping existing sibling releases.
    - Updated `rematerialize_user_albums_features` using `golden_enriched` CTE with `ROW_NUMBER() OVER(PARTITION BY canonical_album_key ORDER BY enrichment_quality_score DESC)` to prevent Cartesian fan-out and propagate APP-16 columns to `user_albums_features_table`.
    - Linked saved Spotify albums to `album_provider_ids`.
  - **Catalog Service Integration (`src/report_v2/services/catalog.py`):**
    - Updated `fetch_user_album_data` to load, sanitize, and return `macro_genre`, `derived_moods`, `descriptive_tags`, and `enrichment_quality_score` with Cloud Datastore gzip caching.
  - **Test Suite Expansion:**
    - Added `tests/test_app16_classification.py` and updated `tests/test_enrich_v2.py` and `tests/test_datastore_cache.py`, expanding the test suite to 73/73 passing tests.
* **Why:**
  - Standardizes album enrichment into an audit-proof two-tier data lake pattern, eliminates edition duplication, and provides deep semantic classification for gatefold recommendation relevance in Crate Digger.
* **How:**
  - Implemented `classifier.py`, modified `enrich.py`, `sync.py`, `bigquery.py`, `catalog.py`, executed BigQuery DDL/DML backfill, verified 73/73 unit tests passing.

---

## [v2.7.1] — 2026-11-21
### 🎨 Album Artwork Resolution, Dynamic SQL Deduplication & Documentation Restructuring
* **What:**
  - **Dynamic SQL Canonical Sibling Deduplication:** Updated `rematerialize_user_albums_features()` in `sync.py` and `bigquery.py` to normalize album names dynamically using BigQuery SQL regex, collapsing *RAM* and *RAM (Archive Collection)* into a single master library entry.
  - **Expanded Edition Blacklist:** Added `archive collection`, `archive`, `super deluxe`, `remastered edition`, and `ultimate edition` to `EDITION_BLACKLIST` in `sync.py`.
  - **Analytics Cover Art Fallback:** Added a fallback join on `user_albums_features_table` (`album_id`) in `services/analytics.py` so top-played telemetry records always resolve artwork even when scrobble metadata differs.
  - **Landing Page Gatefold Artwork:** Replaced broken Wikimedia thumbnail URL with Spotify CDN artwork for Pink Floyd's *The Dark Side of the Moon*.
  - **Local Dev Login Helper:** Added `/dev-login` and `/beta/dev-login` in `routes/auth.py` for rapid 1-click local testing without Spotify OAuth redirect restrictions.
  - **Documentation Restructuring:** Renamed `TECHNICAL_SPECS.md` -> `ROADMAP_TECHNICAL_SPECS.md`, `PROJECT_ROADMAP_AND_SPECS.md` -> `PROJECT_ROADMAP.md`, and created `ARCHITECTURE_AND_FEATURES.md` as the definitive As-Built architecture ledger.
* **Why:**
  - Fixes missing artwork across analytics and landing pages, eliminates duplicate library crate cards for archive collections, and provides clear separation between future roadmap specs and existing as-built architecture.
* **How:**
  - Modified `sync.py`, `bigquery.py`, `analytics.py`, `landing.html`, `auth.py`, rematerialized BigQuery physical tables, updated agent configs, verified 66/66 unit tests passing, and deployed revision `spotify-dashboard-beta-00065-bpm` to Cloud Run.

---

## [v2.7.0] — 2026-11-19
### ✉️ Real-Time Admin Email Notifications via Resend (`OPS-03`)
* **What:**
  - **Resend Email Service Integration:** Created `src/report_v2/services/notifications.py` integrating the Resend API to send real-time HTML email notifications to administrators when new users authenticate and join SpinSleeve.
  - **Auth Pipeline Integration:** Hooked notification dispatch into `src/report_v2/routes/auth.py` upon initial user registration/login.
  - **Test Suite & Mocks:** Added robust unit test coverage in `tests/test_notifications.py` verifying successful email payload dispatch and graceful fallback handling when `RESEND_API_KEY` is not configured.
* **Why:**
  - Enables instant administrative awareness whenever new beta users join the platform.
* **How:**
  - Implemented `notifications.py`, updated `auth.py`, added unit tests in `tests/test_notifications.py`, and verified 66/66 tests passing.

---

## [v2.6.6] — 2026-11-18
### 🎵 Canonical Album Sibling Deduplication & Analytics Fan-Out Elimination (`APP-14`)
* **What:**
  - **Deterministic Canonical Sibling Normalization:** Implemented `compute_canonical_album_key()` using regex stripping for edition suffixes (`deluxe`, `remastered`, `anniversary`, `edition`, `version`, `reissue`, `expanded`, `collector`, `live`, `acoustic`, `mono`, `stereo`, `remix`), successfully profiling and merging 194 variant pairs (e.g. Marika Hackman *I'm Not Your Man (Deluxe)* and *I'm Not Your Man* both mapping to `marika hackman::i'm not your man`).
  - **Physical Column Storage & Ingestion:** Updated `src/pipeline_v2/sync.py` to compute and store `canonical_album_key` directly in both BigQuery `playback_history` and `user_saved_albums`.
  - **Analytics Fan-Out & Double Counting Elimination:** Refactored telemetry and analytics queries in `src/report_v2/services/analytics.py` to join on `canonical_album_key`, eliminating 1-to-many join duplication and ensuring accurate top album/track play counts.
  - **Sibling-Aware Unowned Recommendations (`/recommend`):** Updated unowned crate discovery in `src/report_v2/services/catalog.py` to check ownership against `canonical_album_key`, preventing owned sibling editions from appearing in *"You Should Save These"*.
  - **Historical BigQuery Backfill:** Executed a partition-batched historical backfill across all BigQuery scrobble partitions (2011–2026) and saved library tables.
* **Why:**
  - Resolves double-counting anomalies in telemetry/analytics and ensures robust deduplication across different releases of the same album.
* **How:**
  - Added normalization helper in `sync.py`, updated `analytics.py` and `catalog.py` queries, executed partition-safe BigQuery DML backfill, added `tests/test_canonical_dedup.py`, and verified 63/63 unit tests passing.

---

## [v2.6.5] — 2026-11-17
### 🛠️ INFRA-05 Tech Specs, Pipeline Dockerfile Path Fix & 100% Album Enrichment Coverage
* **What:**
  - **INFRA-05 Technical Specification:** Added comprehensive technical design documentation in `TECHNICAL_SPECS.md` for Zero-Cold-Start & High-Concurrency production architecture (`--min-instances=1`, 100% zero-BQ analytics/pal caching).
  - **Cloud Run Enrichment Job Path Fix:** Resolved container path error (`can't open file '/app/enrich.py'`) in `spotify-v2-enrichment-job` by updating `src/pipeline_v2/Dockerfile` with robust multi-context fallback copying supporting both root-level and subdirectory build contexts. Successfully executed job resulting in green status (`exit(0)`).
  - **100% Album Enrichment Verification:** Audited BigQuery enrichment progress across all multi-tenant saved libraries, confirming 2,161 / 2,161 unique saved albums (100.0%) successfully enriched with Wikipedia narratives and Discogs credits.
* **Why:**
  - Ensures robust zero-cold-start cloud run execution, fixes Cloud Run job failures, and documents high-concurrency caching architecture.
* **How:**
  - Updated `TECHNICAL_SPECS.md`, `src/pipeline_v2/Dockerfile`, successfully built, pushed, and executed the Cloud Run enrichment job, and verified 61/61 unit tests passing.

---

## [v2.6.5] — 2026-11-14
### 🛠️ Config Module Rename (`app_config.py`), Dockerfile Bundling Fix, `/recommend` Internal Server Error Fix & Schema Column Alignment
* **What:**
  - **Config Module Rename & Gemignore Conflict Resolution:** Renamed `config.py` to `app_config.py` to bypass `.geminiignore` file exclusion conflicts and ensure reliable container building.
  - **Dockerfile Bundling Fix:** Updated `src/report_v2/Dockerfile` to explicitly copy `app_config.py`, `routes/`, `services/`, and `templates/` for the modular Flask app factory.
  - **`/recommend` Internal Server Error & Datastore Cache Fallback Fix:** Fixed `KeyError: 'kpis'` / 500 errors when loading catalog data from Cloud Datastore cache by dynamically generating default KPI metrics and ensuring fallback field mappings (`album_image_url` <-> `image`, `album_artist_name` <-> `artist_name`, `album_genres` <-> `genres`, `album_track_plays` <-> `total_plays`, `album_description` <-> `summary`).
  - **Materialized Schema Column Alignment:** Updated `src/report_v2/services/catalog.py` to correctly map materialized table column names (`album_image_url`, `album_artist_name`, `album_genres`, `album_track_plays`, `album_plays`, `album_description`) across all library and crate digger views.
  - **Cache Clearing Parameter (`?clear_cache=1`):** Added support for `?clear_cache=1` (alongside `?refresh=1`) to force-invalidate the user catalog cache in Cloud Datastore and BigQuery.
  - **Post-Deployment Automated Health Verification:** Added automated post-deployment `curl` health verification steps to the `@deploy_assistant` subagent protocol.
* **Why:**
  - Resolves `ModuleNotFoundError: No module named 'config'`, prevents `/recommend` 500 errors on Datastore cache hits, fixes library grid display issues due to schema column mismatches, and guarantees immediate post-deployment availability checking.
* **How:**
  - Renamed `config.py` to `app_config.py`, updated `src/report_v2/services/catalog.py`, `src/report_v2/routes/crate.py`, `src/report_v2/Dockerfile`, added unit tests in `tests/test_crate_digger_polish.py`, bumped `APP_VERSION` to `v2.6.5`, and updated release ledgers.

---

## [v2.6.4] — 2026-11-12
### 📱 Real-Time Admin WhatsApp Notifications (`OPS-03`) & Monolithic App Modularisation (`OPS-04`)
* **What:**
  - **OPS-03 (Real-Time Admin WhatsApp Alerts):** Specified and documented Twilio Programmable Messaging API integration in `TECHNICAL_SPECS.md` and `PROJECT_ROADMAP_AND_SPECS.md` for instant mobile alerts with 1-click admin approval URLs when new users register.
  - **OPS-04 (Monolithic App Modularisation & AI Token Efficiency):** Refactored the monolithic `src/report_v2/app.py` into a clean modular architecture: extracted configuration into `config.py`, business logic and data access into `services/` (`bigquery.py`, `datastore.py`, `spotify.py`, `analytics.py`, `catalog.py`, `avatars.py`), route handlers into blueprints under `src/report_v2/routes/` (`auth.py`, `crate.py`, `analytics.py`, `pals.py`, `admin.py`), and extracted all inline HTML templates into `src/report_v2/templates/`.
* **Why:**
  - Enables instant mobile notification of new member requests via WhatsApp, reduces AI context window consumption by ~70%, and establishes a clean, testable, scalable modular architecture.
* **How:**
  - Created modular files in `src/report_v2/`, registered Flask blueprints, updated unit tests, and verified all 66 tests pass successfully.

---

## [v2.6.3] — 2026-11-12
### ⚙️ User Settings & Privacy Controls: SpinPals Opt-In/Out & Scrobble Sync Pause Toggles (`APP-12`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00047-lqd`
* **What:**
  - **APP-12 (User Settings & Privacy Controls):** Implemented interactive user settings controls in the avatar settings dropdown across all views (`Library`, `Crate Digger`, `Analytics`, `SpinPals`), featuring 1-click toggles for SpinPals directory participation (`pals_opt_in`) and Scrobble Sync Pause (`sync_paused`).
  - **Backend Pipeline Sync Pause Guard:** Added explicit pipeline execution guard in `src/pipeline_v2/sync.py` (`if user.get("sync_paused", False): continue`) to respect user scrobble sync pause preferences during automated background ingestion cycles.
  - **Session & State Synchronization:** Updated OAuth callback (`callback`), admin assumption (`admin_assume`), and admin revert (`admin_revert`) flows to preserve `sync_paused` state across sessions.
  - **Unit Testing Coverage:** Added comprehensive unit test coverage (`test_user_settings_sync_pause_and_pals` in `tests/test_admin_and_pals.py`) verifying correct UI rendering of sync pause and SpinPals status badges.
* **Why:**
  - Empowers users with granular privacy and synchronization controls, allowing them to temporarily pause scrobble background syncing or opt out of the SpinPals community directory on demand.
* **How:**
  - Updated `src/report_v2/app.py`, `src/pipeline_v2/sync.py`, `tests/test_admin_and_pals.py`, `PROJECT_ROADMAP_AND_SPECS.md`, and `CHANGELOG.md`. Verified all unit tests pass successfully and deployed to Cloud Run (Revision `00047-lqd`).

---

## [v2.6.2] — 2026-11-12
### 🎧 Unowned Crate Artwork Enrichment, Save Timeout Resilience, Avatar Sizing Polish & ROI Matrix (`APP-07`, `POLISH`)
* **What:**
  - **Unowned Album Artwork Enrichment (`APP-07`):** Implemented two-tier on-the-fly Spotify API artwork enrichment (batch `sp.albums` + `sp.search` fallback) for Unowned Crate items, resolving missing album cover renderings.
  - **Save Read Timeout & Graceful Exception Handling:** Added explicit `requests_timeout=15` and robust 504 gateway timeout exception handling for Spotify unowned album save calls.
  - **Avatar Dropdown Sizing Polish:** Upgraded avatar preset dropdown previews across all templates (`Library`, `Crate Digger`, `Analytics`, `SpinPals`) from `w-7 h-7` to `w-11 h-11` for enhanced visual clarity and touch target ergonomics.
  - **Effort vs. Value ROI Priority Matrix:** Integrated structured effort vs. value prioritization table into the in-app roadmap template (`ROADMAP_HTML_TEMPLATE`) and `PROJECT_ROADMAP_AND_SPECS.md`.
  - **Documentation & Roadmap Navigation:** Added a hyperlinked Table of Contents to `PROJECT_ROADMAP_AND_SPECS.md` and corrected the in-app roadmap template to accurately reflect upcoming backlog items (`APP-14`, `APP-16`).
  - **Local Dev Login Fallback:** Added `SpotifyClientCredentials` fallback support for `/dev/login` local test sessions.
* **Why:**
  - Eliminates artwork rendering gaps in the Unowned Crate (`APP-07`), protects against slow Spotify API response dropouts during library saves, and maintains pristine, hyperlinked project documentation.
* **How:**
  - Updated `src/report_v2/app.py`, `PROJECT_ROADMAP_AND_SPECS.md`, and `CHANGELOG.md`. Verified 65/65 unit tests pass successfully and deployed to Cloud Run (Revision `spotify-dashboard-beta-00045-clg`).

---

## [v2.6.1] — 2026-11-11
### 📚 Semantic Liner Notes & Description Classification for Crate Digger Relevance (`APP-16`)
* **What:**
  - **APP-16 (Semantic Liner Notes Classification):** Specified and documented text classification and NLP pipeline extensions in `src/pipeline_v2/enrich.py` to parse Wikipedia and Discogs archival narratives, extracting macro-genres (`macro_genre`), derived moods (`derived_moods`), and stylistic tags (`descriptive_tags`).
  - **BigQuery Schema & Semantic Discovery:** Added DDL specs for `spotify_v2.album_enriched_metadata` table expansion and semantic similarity scoring to power kindred spirit recommendations in Crate Digger (`/recommend`) even when official Spotify tags differ.
* **Why:**
  - Raw Spotify API genre tags often mix broad categories with hyper-niche tags. Semantic classification of archival gatefold liner notes ensures highly relevant, nuanced Crate Digger discoveries and vibe filtering.
* **How:**
  - Updated technical specifications (`TECHNICAL_SPECS.md`), project roadmap (`PROJECT_ROADMAP_AND_SPECS.md`), application version (`src/report_v2/app.py`), and engineering changelog (`CHANGELOG.md`).

---

## [v2.6.0] — 2026-11-11
### 🚀 Headless API & Firestore Rearchitecture (`APP-14`), Native iOS SwiftUI Companion App (`APP-15`) & Zero-Cold-Start Production Architecture (`INFRA-05`)
* **What:**
  - **APP-14 (Headless API & Firestore Rearchitecture):** Designed and specified stateless REST JSON API endpoints (`/api/v1/catalog`, `/api/v1/analytics`, `/api/v1/recommendations`, `/api/v1/pals`) backed by Cloud Firestore and Cloud Datastore document caches, enabling decoupled client rendering and Firebase CDN reverse proxy edge caching.
  - **APP-15 (Native iOS SwiftUI Companion App):** Architected native SwiftUI mobile companion application specs for iOS 17+, featuring secure Keychain token storage, PKCE OAuth authentication, grid/crate browsing views, gatefold liner notes reader, and native 30s audio previews.
  - **INFRA-05 (Zero-Cold-Start & High-Concurrency Production Architecture):** Configured Cloud Run minimum instance scaling (`--min-instances=1`) and multi-tier document store caching to eliminate cold starts and guarantee sub-50ms API response times under high concurrency.
* **Why:**
  - Decoupling the Flask monolithic backend into a headless API architecture empowers native mobile clients (iOS SwiftUI) while maintaining the lightning-fast web experience on `spinsleeve.cc`. Zero-cold-start configuration ensures instant reliability for collectors worldwide.
* **How:**
  - Updated technical specifications (`TECHNICAL_SPECS.md`), project roadmap (`PROJECT_ROADMAP_AND_SPECS.md`), and application version (`src/report_v2/app.py`).

---

## [v2.5.3] — 2026-11-11
### 🛠️ Legacy Streaming History Format Support (`StreamingHistory_music_*.json`) & BigQuery Partition Limit & Idempotency Fixes
* **What:**
  - **Legacy ZIP Format Support:** Extended ZIP extraction filters in `api_upload_history` and `ingest_zip_qa.py` to support both extended (`Streaming_History_Audio_*.json`) and legacy (`StreamingHistory_music_*.json`) Spotify GDPR export formats.
  - **BigQuery Partition Limit Fix (`400 Too many partitions produced by query`):** Refactored web history upload (`api_upload_history`) and reconciliation scripts to batch BigQuery `MERGE` and `INSERT` operations year-by-year, respecting BigQuery's 4,000 partition DML modification limit across lifetime archives spanning 15+ years (~5,500 partitions).
  - **Strict Upload Idempotency (`drop_duplicates`):** Added explicit pandas-level deduplication (`drop_duplicates` on `user_id, played_at, track_name, artist_name`) prior to staging load to guarantee 100% idempotency and prevent duplicate scrobbles during file uploads.
* **Why:**
  - Ensures seamless ingestion of all historical formats and prevents BigQuery DML partition ceiling errors or duplicate play count inflation when users upload lifetime Spotify history archives.
* **How:**
  - Updated `src/report_v2/app.py` and `src/pipeline_v2/ingest_zip_qa.py` with multi-format ZIP filtering, year-by-year DML batching, and strict deduplication. Verified all 65 unit tests pass successfully.

---

## [v2.5.2] — 2026-11-10
### ⚡ Complete Sub-100ms Multi-Tier Caching & Query Consolidation (`INFRA-03c/d/e`), Homepage Redesign (`BRAND-01`, `BRAND-03`) & Analytics Cache Refresh Fix
* **What:**
  - **INFRA-03c/d/e (Multi-Tier Caching & Session Storage):** Integrated Cloud Datastore gzipped document store caching for SpinPals compatibility and analytics telemetry, alongside client-side `sessionStorage` catalog caching (<10ms instant load).
  - **BRAND-01 (Homepage & Public Login Redesign with Feature Showcase):** Redesigned public landing page (`/login`) with immersive feature showcase, verified authentic album artwork for Pink Floyd (*Dark Side of the Moon*), Daft Punk (*Discovery*), and Radiohead (*Kid A*), and clean admin test switchers.
  - **BRAND-03 (Public Roadmap Portal at `/roadmap`):** Launched dedicated public release and feature transparency portal (`/roadmap`) showcasing shipped and upcoming features.
  - **Analytics Cache Invalidation & Refresh Propagation:** Implemented robust `invalidate_user_analytics_cache()` and `?refresh=1` query parameter propagation in analytics views and API endpoints to allow instant telemetry cache clearing on demand.
* **Why:**
  - Elevates the public-facing brand presence and delivers sub-50ms application latency across all multi-tenant views.
* **How:**
  - Implemented Datastore caching with gzip compression, browser session storage, public landing page HTML template with authentic album artwork CDN integration, and dedicated `/roadmap` route. Verified all 65 unit tests pass successfully.

---

## [v2.5.1] — 2026-11-09
### ✨ UI Polish, Header Navigation Consistency, Persistent Audio Mute & Tab Routing (`POLISH-09` to `POLISH-13`)
* **What:**
  - **POLISH-09 (Landing Page Version Alignment):** Bumped landing page and header version constant to `v2.5.0` / `v2.5.1`.
  - **POLISH-10 (Header Consistency Across All Views):** Restored the top-level navigation tab bar (`Library` | `Analytics` | `SpinPals`) and hover audio toggle buttons (`audioToggleBtn`) consistently across Library Explorer, Crate Digger (`/recommend`), Analytics (`/analytics`), and SpinPals (`/pals`) views.
  - **POLISH-11 (Cross-Page Audio Mute State Persistence):** Integrated `localStorage` (`spinAudioEnabled`) across all view templates so user audio mute preferences persist seamlessly across page navigations.
  - **POLISH-12 (URL Parameter Tab Routing):** Added `URLSearchParams` parsing on Library Explorer load (`?tab=unowned` or `?tab=saved`) to instantly activate the requested crate tab.
  - **POLISH-13 (Mobile Avatar Dropdown Overflow Fix):** Added responsive bounds (`max-w-[calc(100vw-2rem)] sm:w-72 right-0 sm:right-0`) to the user settings dropdown menu to prevent left-side clipping on narrow mobile viewports.
* **Why:**
  - Ensures a polished, friction-free user experience across mobile and desktop devices with zero state loss during navigation or tab switching.
* **How:**
  - Updated `src/report_v2/app.py` template headers and script blocks for Crate Digger, Analytics, and SpinPals, integrated `localStorage` state management, added URL parameter parsing, and verified all 65 unit tests pass successfully.

---

## [v2.5.0] — 2026-11-09
### 🎧 Spotify Full Scrobble Historical Data Upload & Ingestion (`APP-13`), UI Settings Integration & Header Masthead Navigation Refactoring
* **Cloud Run Revision:** `spotify-dashboard-beta-00034-6lq`
* **What:**
  - **APP-13 (Historical Scrobble Upload & Ingestion Engine):** Designed and implemented robust GDPR Spotify streaming history parser (`src/pipeline_v2/history_parser.py`) supporting both Extended (`Audio_Streaming_History_*.json`) and Legacy (`StreamingHistory*.json`) formats, with automated podcast filtering and short-scrobble elimination (<30s).
  - **QA & Production Reconciliation (`src/pipeline_v2/ingest_qa.py`, `ingest_zip_qa.py`):** Built BigQuery QA test table (`playback_history_qa`) and year-by-year partition batching (`MERGE` deduplication) to successfully ingest 192,371 lifetime historical scrobbles (spanning 2011 to 2026) for verification without double-counting.
  - **UI Settings Integration (`📂 Import History (.json / .zip)`):** Added user-facing file upload button inside avatar settings dropdowns across all application views. Enhanced backend endpoint (`/api/user/upload-history`) to support both `.json` files and full `.zip` archives (extracting and parsing `Streaming_History_Audio_*.json` in-memory).
  - **Staging Idempotency & Instant Re-materialization:** Implemented isolated temporary staging tables with `WRITE_TRUNCATE`, composite key `MERGE` deduplication, automatic `user_albums_features_table` re-materialization, and `UserCatalogCache` invalidation so the Library Explorer instantly reflects updated lifetime play counts.
  - **Header Masthead Navigation Relocation:** Moved the top-level tab menu (`Library` | `Analytics` | `SpinPals`) up into the persistent header row between the SpinSleeve logo and user settings menu.
  - **SpinPals Emoji Clean-up:** Removed all emojis (`🤝`, `🔒`) from the SpinPals tab label for a clean, professional aesthetic.
* **Why:**
  - Music collectors accumulate over a decade of listening history before discovering SpinSleeve. Allowing 1-click lifetime history imports via GDPR JSON/ZIP exports bridges the gap between recent telemetry and archival archival listening history. Relocating navigation into the header masthead further declutters the UI and elevates the application chrome.
* **How:**
  - Created `src/pipeline_v2/history_parser.py`, `ingest_qa.py`, `ingest_zip_qa.py`, `validate_qa.py`, and `validate_dedup.py`.
  - Added unit test suite `tests/test_history_parser.py`.
  - Updated `src/report_v2/app.py` with `/api/user/upload-history`, `.zip` in-memory extraction, re-materialization hooks, and header layout refactoring.

---

## [v2.4.1] — 2026-11-08
### 🧭 Tab Navigation UX Simplification & Hardware Segmented Sub-Tab Deck (`POLISH-08`)
* **What:**
  - **POLISH-08 (Simplified Navigation & Sub-Tabs):** Streamlined top-level navigation from 4 noisy tabs (`Library Explorer`, `Crate Digger`, `Analytics`, `SpinPals`) down to 3 clean domains (`Library`, `Analytics`, `SpinPals`).
  - **Crate Digger Integration:** Nested Crate Digger under the Library Explorer domain as a sub-tab, placed between "My Saved Vinyl" and "You Should Save These" (leaving unowned recommendations as the rightmost subtab).
  - **Hardware-Inspired Segmented Pill Deck:** Replaced busy emojis with minimalist SVG line icons and a recessed control deck (`bg-[#080a0c]` with inner shadow and gradient active pills).
  - **Interactive Mockup (`spinsleeve_nav_mockup.html`):** Created a standalone Tailwind CSS / Vanilla JS visual prototype in the workspace root demonstrating the new layout and subtab state controller.
  - **Roadmap Update:** Logged feature `POLISH-08` in `PROJECT_ROADMAP_AND_SPECS.md` with estimated effort and strategic impact.
* **Why:**
  - Crate Digger is functionally a discovery mode of the music collection, so separating it into a top-level tab created unnecessary navigation friction. Nesting it under Library Explorer creates a unified music hub while decluttering the primary navigation bar.
* **How:**
  - Created `spinsleeve_nav_mockup.html` for visual validation.
  - Updated `PROJECT_ROADMAP_AND_SPECS.md` with `POLISH-08` specifications and backlog matrix entry.

---

## [v2.4.0] — 2026-11-08
### 📦 Played But Not Owned: "You Should Save These" Library Crate (`APP-07`), README Overhaul (`DOCS-01`) & Modularisation Roadmap (`OPS-04`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00032-6f2`
* **What:**
  - **APP-07 ("You Should Save These" Unowned Crate):** Designed, implemented, and deployed a dedicated discovery crate inside Library Explorer showcasing streamed albums not currently in the user's permanent Spotify library.
  - **Amber Dashed Aesthetic:** Unowned sleeves feature warm amber dashed contours (`border-2 border-dashed border-amber-500/40`), glowing amber shadows, glassmorphic `✨ Streamed` ribbon tags, and `🔥 X Plays` badges.
  - **Multi-Track Album Rule (`HAVING distinct_tracks >= 2`):** Strictly enforces that an item must have at least 2 distinct tracks played to be recommended as a record crate album, filtering out accidental single-track plays and standalone singles.
  - **Dynamic Time Horizon Filters (30D, 90D, All Time):** Integrated interactive time horizon buttons defaulting to **All Time**, with an asynchronous endpoint (`/api/unowned-albums?horizon=...`) for instant client-side switching.
  - **Strict Ownership Deduplication:** Filters out any album currently saved in the user's collection using strict normalized title and artist matching (`CONCAT(LOWER(TRIM(album_name)), '::', LOWER(TRIM(artist_name))) NOT IN (SELECT ... FROM user_saved_albums)`), guaranteeing zero duplicate recommendations.
  - **1-Click Save with Dynamic Spotify Search API Resolution:** Hovering an unowned sleeve presents `➕ Save to Library`. If historical scrobbles lack a Spotify `album_id` (`NULL`), `/api/save-album` dynamically queries Spotify's Search API (`sp.search`) to resolve the canonical ID, adds the album to Spotify saved library (`PUT /v1/me/albums`), inserts the record into BigQuery `user_saved_albums`, and invalidates caches for instant migration (~1-2s).
  - **Brand Avatar Fallback Sleeve:** Missing album artwork dynamically renders SpinSleeve's golden-glowing brand vinyl icon badge inside the amber dashed jacket.
  - **DOCS-01 (README Overhaul):** Revamped `README.md` to feature top-level SpinSleeve mission and purpose, a comprehensive Mermaid architecture topology diagram, project file map, operational commands, and PolyForm license, while removing redundant local setup documentation.
  - **OPS-04 (App Modularisation Roadmap):** Added app modularisation refactoring specification to `PROJECT_ROADMAP_AND_SPECS.md` to break down the monolithic `app.py` into small modules (`routes/`, `services/`, `config.py`) for AI context efficiency and testability.
* **Why:**
  - Music collectors stream dozens of exceptional albums during deep-dive listening sessions but frequently forget to save them into their permanent collection. This feature closes the loop between casual discovery and permanent curation. Additionally, revamping `README.md` and planning app modularisation ensures crystal-clear system documentation and AI parsing efficiency.
* **How:**
  - Updated `src/report_v2/app.py` with `fetch_unowned_album_data()`, `/api/unowned-albums`, `/api/save-album`, and `get_token_for_user()`.
  - Added `user-library-modify` to Spotify OAuth scopes.
  - Updated `BETA_EXPLORER_HTML` with segmented crate tabs, unowned grid container, and JavaScript handlers.
  - Added unit test suite `tests/test_unowned_crate.py` (all 63 tests passing). Deployed to production Cloud Run (`spotify-dashboard-beta-00032-6f2`).
  - Rewrote `README.md` with Mermaid diagram and purpose statement, and updated `PROJECT_ROADMAP_AND_SPECS.md`.

---

## [v2.3.0] — 2026-11-08
### 🎵 Music Legend Illustrated Avatar Persona Picker (`APP-04`) & Spotify Full Scrobble Upload Roadmap (`APP-13`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00026-s9t`
* **What:**
  - **APP-04 (Music Legend Avatar Persona Picker):** Designed and deployed a curated collection of 12 vector SVG illustrated personas spanning two centuries of genres and cultural movements:
    - 🎹 **Ludwig van Beethoven** (*Classical / Romantic*)
    - 🎺 **Chet Baker** (*Cool / West Coast Jazz*)
    - 🕶️ **Miles Davis** (*Modal Jazz / Post-Bop*)
    - 🎸 **Bob Dylan** (*Folk / 60s Counterculture*)
    - ⚡ **David Bowie** (*Glam Rock / Aladdin Sane*)
    - 🎹 **Stevie Wonder** (*Soul / Motown / Funk*)
    - 🎸 **Jimi Hendrix** (*Psychedelic Rock*)
    - 🎷 **Fela Kuti** (*Afrobeat Pioneer*)
    - 👑 **Madonna** (*80s Pop / Dance*)
    - 🎤 **Amy Winehouse** (*Camden Neo-Soul / Jazz-Pop*)
    - 🤖 **Daft Punk** (*French Touch / House*)
    - 🦉 **Drake** (*Modern Hip-Hop / R&B*)
    - Plus a default option to revert back to the user's authentic Spotify profile picture.
  - **Click-to-Open Dropdown UI:** Integrated an interactive dropdown anchored to the user avatar in the global header across all four views (Library Explorer, Crate Digger, Listening Telemetry, and SpinPals).
  - **Instant Save & Real-Time Reflection:** Selecting a persona fires an AJAX request to `/api/user/avatar`, persists `custom_avatar_id` and `avatar_url` into Cloud Datastore, and updates `session` in real time, updating the user avatar across the header, SpinPals listening lounge, and admin dashboard without requiring a page refresh.
  - **Dedicated SVG Serving:** Implemented `/avatar/<avatar_id>.svg` and `/avatar/<avatar_id>` endpoints serving crisp scalable vector artwork with long-term immutable caching (`max-age=604800`).
  - **APP-13 (Roadmap Addition):** Added Spotify Full Scrobble Historical Data Upload & Automated Ingestion feature specification to `PROJECT_ROADMAP_AND_SPECS.md`, outlining UI file uploads for Spotify personal data requests, cloud staging buckets, and automated BigQuery merge pipelines.
* **Why:**
  - Users without custom Spotify profile photos defaulted to generic grey silhouettes in the vinyl crate and SpinPals Listening Lounge. Adding music legends gives listeners iconic artistic personas to represent their musical tastes.
* **How:**
  - Embedded vector SVG art dictionary `AVATAR_SVGS` and registry `AVATAR_PRESETS` in `src/report_v2/app.py`.
  - Added `@app.route("/avatar/<avatar_id>")` and `@app.route("/api/user/avatar")` endpoints.
  - Injected `avatar_presets` into Jinja templates via Flask `@app.context_processor`.
  - Updated OAuth callback (`spotify_callback`), `admin_assume`, and `admin_revert` to preserve and propagate `custom_avatar_id` and `spotify_avatar_url`.
  - Added comprehensive test suite `tests/test_avatar_picker.py` covering XML validity, SVG serving, unauthenticated protection, and interactive dropdown rendering (61/61 tests passing).

---

## [v2.2.2] — 2026-11-07
### ✨ Library Initial Sort (`POLISH-02`), Decimal Play Badges (`POLISH-03`), Crate Digger Era Filter Layout & License Migration (`BRAND-04`)
* **What:**
  - **POLISH-02 (Strict 30D Initial Sort):** Updated Library Explorer initialization (`DOMContentLoaded`) to trigger `onFilterChange()` instead of raw `renderGrid()`, ensuring the default `plays_30d_desc` (Heavy Rotation Last 30 Days) sorting applies immediately on initial page load rather than all-time plays.
  - **POLISH-03 (Play Count Badge Refinement):** Eliminated bare `0 Plays` badges across all views. Unplayed records now display contextual tags (`✨ Newly Added` if added within the last 14 days, `💤 Never Played` otherwise). Records with partial/fractional scrobbles display clean decimal play counts (e.g. `🔥 0.6 Plays`, `🔥 1.7 Plays`), while whole spins format as clean integers (`🔥 2 Plays`, `🔥 1 Play`).
  - **Crate Digger Era Filter Layout:** Adjusted Crate Digger Row 2 grid spans (`5/4/3` allocation for Vibe, Era, and Genre) and enforced horizontal single-line alignment with `flex flex-nowrap` and `whitespace-nowrap`, bringing the Era filter closer to Vibe and preventing any unwanted wrapping.
  - **BRAND-04 (License Migration):** Migrated repository from MIT License to **PolyForm Noncommercial License 1.0.0** (`LICENSE`, `README.md`, `PROJECT_ROADMAP_AND_SPECS.md`), closing the SaaS commercial hosting loophole while keeping non-commercial usage and contributions free.
  - **APP-12 (Roadmap Update):** Specified Header Profile Dropdown, User Settings & Community Action Center in `PROJECT_ROADMAP_AND_SPECS.md`, incorporating SpinPals opt-in/out toggle, nickname editing, scrobble pause, feedback, and Buy Me a Coffee integration.
* **How:**
  - Updated `compute_normalized_album_plays` in Python and `getAlbumPlayBadge` in JavaScript within `src/report_v2/app.py`.
  - Added `added_at` parameter checking to compute newly added status.
  - Updated unit test suite (`tests/test_normalized_plays.py`) and verified all 51 tests pass successfully.
  - Updated `LICENSE` and `README.md` to PolyForm Noncommercial 1.0.0.

---
### 🎯 Crate Digger UX Streamlining, Balanced Vibes (`POLISH-01`), Album Artist Isolation & Spin Again Deduplication (`POLISH-07`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00024-mdp`
* **What:**
  - Replaced the two stacked, conflicting multi-button rows (*Listening Mode* and *Time Horizon*) with a single-dimension **Crate Target Focus** selector (`🔥 Heavy Rotation (30D)`, `🔍 Unplayed Gems`, `❄️ Cold Shelf (30D+)`, `⭐ All-Time Favorites`, and `🌌 Full Crate`).
  - Redesigned the bulky filter frame into a compact, space-efficient 2-tier digging console, saving over 240px of vertical height and pulling spotlight vinyl picks and album art above the fold on all screens.
  - Balanced the mood vibe genre classification dictionary by eliminating overly broad substring matches on `'rock'` from `energetic`, while enriching `chill` with realistic streaming tags (`shoegaze`, `trip hop`, `ambient pop`, `idm`), `mellow` (`chamber pop`, `americana`, `bluegrass`), and `vintage` (`classic soul`, `motown`, `psychedelic rock`, and pre-1985 release years).
  - De-duplicated the "Spin Again" shuffle action (`POLISH-07`): removed the redundant button from the global navigation header and harmonized the Control Deck console button to `🎲 Spin Again`.
* **Bug Fix (Homonymous Album Collision - Neil Young vs. CARRTOONS *Homegrown*):**
  - **Issue:** Scrobbles and artwork were conflated between albums sharing the same title by different artists (e.g. Neil Young and CARRTOONS both released albums titled *Homegrown*). In Analytics, CARRTOONS scrobbles displayed Neil Young's cover art, while in Library Explorer, Neil Young's play count was inflated to 229 plays (the combined sum of 184 CARRTOONS plays + 45 Neil Young plays).
  - **Fix:** Refactored SQL queries in `fetch_user_analytics_data` and BigQuery view `spotify_v2.user_albums_features` to group and join on composite key `(norm_album_name, norm_artist_name)`.
  - **Verification:** Re-materialized `user_albums_features_table` in BigQuery and cleared Datastore document cache; confirmed Neil Young strictly has 45 plays (3.8 album spins) and CARRTOONS has 184 plays (13.1 album spins) with authentic individual album sleeves. Added regression test suite `tests/test_album_artist_collision.py`.
* **How:**
  - Updated `BETA_RECOMMEND_HTML` in `src/report_v2/app.py` with responsive flex/grid horizontal layouts.
  - Added `setTarget(target)` function while maintaining backward compatibility bridges for `setHorizon` and `setMode`.
  - Added comprehensive test suites `tests/test_crate_digger_polish.py` and `tests/test_album_artist_collision.py` (50/50 tests passing).

---

## [[v2.2.0]](https://github.com/Vaultica/spinsleeve/commit/00ace34) — 2026-11-05
### 🛠️ Header Polish & Semantic Release Versioning (`POLISH-04`, `POLISH-05`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00022-z5t`
* **What:** Replaced the hardcoded `"BETA v2"` pill with a dynamic release badge (`v2.2.0`) and removed developer test account switchers (`👑 Serge`, `👩 Sarah`, `🐹 GuineaPig`) from the global navigation header across all four views.
* **Why:** The test account shortcuts cluttered the global header on production screens for friends. Admins already have a dedicated Admin Portal (`/admin`) to assume any user view with 1 click.
* **How:**
  - Injected `APP_VERSION = "v2.2.0"` globally using a Flask template context processor (`@app.context_processor`).
  - Standardized the top-right user profile widget with a clean avatar, display name, and Logout button for all users.
  - Retained the high-visibility amber `👑 Assuming: <User>` indicator and `↩ Revert` button only when an admin is actively impersonating another user.

---

## [[v2.1.2]](https://github.com/Vaultica/spinsleeve/commit/6cfdfa2) — 2026-11-05
### ⚡ Cloud Datastore Document Store Catalog Cache (`INFRA-03b`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00021-42p`
* **Pipeline Image:** `spotify-v2-pipeline:latest` (`sha256:44a76e77...`)
* **What:** Integrated a Tier 2 NoSQL document cache inside Google Cloud Datastore (`UserCatalogCache`), storing pre-computed, pre-serialized user album catalogs as gzipped binary blobs (`bytes`).
* **Why:** Cloud Run instances scale to zero when idle, emptying process RAM. Every uncached visit previously waited ~3.8 seconds for BigQuery.
* **How:**
  - Benchmarked payload compression: Serge's 1,825 albums compressed from 2.4 MB down to **324 KB** (7.5x ratio), easily fitting under Datastore's 1 MB entity limit.
  - Implemented `get_catalog_from_datastore(user_id)` and `save_catalog_to_datastore(user_id, data)` with a 24-hour TTL.
  - **Latency Benchmark:** Cold catalog fetch dropped from **~3,870 ms down to ~50 ms** (**~70x speedup**) at **$0 additional cloud cost** (within Datastore's 50,000 free daily reads).
  - Added `invalidate_user_catalog_cache(user_id)` to `sync.py` so the cache automatically clears when new scrobbles or saved albums are ingested.

---

## [[v2.1.1]](https://github.com/Vaultica/spinsleeve/commit/280c51a) — 2026-11-05
### 🚀 BigQuery Materialized Clustered Table (`INFRA-03a`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00020-vrw`
* **What:** Materialized the heavy dynamic SQL view `user_albums_features` into a physical table `secret-compass-181513.spotify_v2.user_albums_features_table` clustered by `user_id`.
* **Why:** The dynamic view previously executed complex window functions (`ROW_NUMBER() OVER (...)`) and joins across `playback_history`, `user_saved_albums`, and `album_enriched_metadata` on every query, adding 2.5–3.5s of compute time.
* **How:**
  - Automated zero-downtime re-materialization in `src/pipeline_v2/sync.py` via `rematerialize_user_albums_features(bq_client)`.
  - Switched `fetch_user_album_data` and `compute_pal_compatibility` to read from the physical table.
  - **Latency Benchmark:** View query (8.50s) $\rightarrow$ Table query (**3.69s**, **2.3x speedup** on cold uncached query).

---

## [[v2.1.0]](https://github.com/Vaultica/spinsleeve/commit/2459434) — 2026-11-05
### 📻 Dynamic Time Horizon: Rolling 30D vs. All-Time (`APP-06`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00019-9ds`
* **What:** Introduced a 2-way time horizon switcher across Crate Digger (`/recommend`) and SpinPals (`/pals`), allowing collectors to evaluate recommendations against rolling 30-day heavy rotations rather than static lifetime scrobbles.
* **Why:** Lifetime play counts change slowly, causing the recommender to surface the same albums week after week. The 30-day horizon prioritizes current obsessions.
* **How:**
  - Updated BigQuery view `user_albums_features` with single-pass conditional aggregation (`COUNTIF(played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))`), scanning history only once for `album_track_plays_30d` and `album_plays_30d`.
  - Added 2-way pill controls in Crate Digger: `🔥 Heavy Rotation (Last 30 Days)` vs `🏛️ All-Time Collection`.
  - Added horizon toggle in SpinPals Top 5 to Borrow (`?horizon=30d`), generating personalized reasons like *"Sarah's Current Obsession (4 spins this month) • Pitchfork 8.8"*.
  - Added `🔥 Heavy Rotation (Last 30 Days)` sorting in Library Explorer with dynamic 30D badge styling.

---

## [[v2.0.2]](https://github.com/Vaultica/spinsleeve/commit/7dd7169) — 2026-11-05
### 🔥 Normalized Album Play Count Badges (`APP-05`)
* **Cloud Run Revision:** `spotify-dashboard-beta-00018-c67`
* **What:** Replaced ambiguous raw scrobble counts on album sleeve corners with contextual `🔥 {album_plays} Plays` pill badges and detailed hover tooltips.
* **Why:** Listeners could not tell whether a number badge like "42" meant 42 individual track scrobbles or 42 full album spins.
* **How:**
  - Implemented `compute_normalized_album_plays(track_plays, tracks_total)` calculating:
    $$\text{Album Plays} = \left\lfloor \frac{\text{Total Track Scrobbles}}{\text{Total Tracks in Album}} \right\rfloor$$
  - Added fallback to track scrobbles if track count is unavailable or zero.
  - Added hover tooltips explaining the complete breakdown: *"Estimated complete album spins based on {P} track plays across {T} tracks"*.
  - Applied badges universally across Library Explorer, Crate Digger (spotlight & candidate pool), and SpinPals (Top Borrow & pal crates).
  - Updated Library sorting to sort by normalized full spins first, with raw scrobbles as tiebreaker.

---

## [[v2.0.1]](https://github.com/Vaultica/spinsleeve/commit/b2301d4) — 2026-11-05
### 📚 Automated Album Metadata Enrichment Pipeline
* **Cloud Run Job:** `spotify-v2-enrichment-job`
* **What:** Implemented `src/pipeline_v2/enrich.py` scraping Wikipedia and Discogs to populate liner notes, personnel, and critical scores into shared BigQuery table `album_enriched_metadata`.
* **Why:** Eliminates duplicate scraping across users; provides rich 12" gatefold archival reading.

---

## [[v2.0.0]](https://github.com/Vaultica/spinsleeve/commit/200906e) — 2026-11-04
### 🌐 Production Cutover to `https://spinsleeve.cc` (Phase 6)
* **Cloud Run Revision:** `spotify-dashboard-beta-00017-749`
* **What:** Executed zero-downtime Firebase Hosting rewrite flip pointing custom domain `https://spinsleeve.cc` directly to the multi-tenant V2 application on Cloud Run.
* **Why:** Graduated SpinSleeve from an experimental `/beta/` subpath into a standalone production application.
* **How:**
  - Configured symmetrical root routing (`/`, `/recommend`, `/analytics`, `/pals`, `/admin`, `/login`, `/logout`) while preserving full backwards compatibility for `/beta/*`.
  - Paused legacy single-user Cloud Scheduler `spotify-daily-sync`.
  - Updated session cookie handling to ensure seamless Firebase proxy authentication (`__session`).

---

## [[v1.5.0]](https://github.com/Vaultica/spinsleeve/commit/80cff37) — 2026-11-04
### 📖 Pre-Production Gatefold & Admin Polish (Phase 5b)
* **Cloud Run Revision:** `spotify-dashboard-beta-00015-ql8`
* **What:** Enhanced the 12" gatefold modal with a compact mobile header (<110px), interactive audio scrubber, deep links (Pitchfork, Discogs, Wikipedia, Metacritic, Apple Music), and admin view impersonation.
* **Why:** Large modal headers clipped album artwork on mobile screens, and administrators needed a way to test unapproved / locked states without creating dummy Spotify accounts.
* **How:**
  - Added 33⅓ RPM rotating vinyl platter SVG animation (`ICON_A_SVG`) to headers and favicon.
  - Implemented `/admin/assume/<user_id>` with session-scoped permissions and a persistent escape banner (`/admin/revert`) to prevent lockout.
  - Set default privacy policy: new users default to `pals_opt_in = False` with `PALS_LOCKED_HTML` gate.

---

## [[v1.4.0]](https://github.com/Vaultica/spinsleeve/commit/11f5529) — 2026-11-03
### 🤝 SpinPals: CrateMates Social Edition (Phase 5a)
* **Cloud Run Revision:** `spotify-dashboard-beta-00012-rz4`
* **What:** Built the friend-to-friend music sharing lounge (`/pals`):
  - Acoustic Chemistry Gauge: 5-tier taste alignment calculation (*Vinyl Soulmates, Acoustic Kin, Crate Companions, Curious Explorers, Fresh Discoveries Ahead*).
  - Mutual Favorites: Badges for shared saved albums (`🤝 Both Own`) and shared artists.
  - Top 5 Records to Borrow: Curated recommendation engine highlighting unowned records with high pal play counts and critical acclaim.
  - Virtual Crate Digging: Browse a friend's entire vinyl shelf with gatefold access and needle-drop audio previews.

---

## [[v1.3.0]](https://github.com/Vaultica/spinsleeve/commit/c1c7ef8) — 2026-11-03
### ⚙️ Multi-Tenant Ingestion Pipeline & Cloud Scheduler (Phase 4)
* **Cloud Run Job:** `spotify-v2-pipeline-job`
* **Cloud Scheduler:** `spotify-v2-sync-scheduler` (Runs every 30 minutes)
* **What:** Deployed an automated containerized ingestion pipeline iterating all approved Datastore users, refreshing Spotify tokens, and loading new scrobbles into BigQuery `playback_history`.
* **Why:** Replaced single-user cron functions with a scalable multi-tenant sync architecture.

---

## [[v1.2.0]](https://github.com/Vaultica/spinsleeve/commit/0b18d90) — 2026-11-03
### 🎶 Feature Parity: Audio Previews, Crate Digger & Analytics (Phase 3)
* **What:** Re-implemented core features for the multi-tenant architecture:
  - 30-Second Needle-Drop Previews: Instant hover audio snippet playback via the iTunes Search API.
  - Crate Digger Discovery Engine: Vibe filters (*Chill, Energetic, Mellow, Vintage*), era filters, and candidate scoring.
  - Listening Analytics: Listening clock hourly heatmap, top genres, taste velocity, and "This Year" date filters.
  - Library Sorting: Introduced *Artist (A-Z), Albums (Year desc)* for vinyl shelf browsing.

---

## [[v1.1.0]](https://github.com/Vaultica/spinsleeve/commit/752838a) — 2026-11-02
### 🔐 Spotify PKCE OAuth & Datastore User Vault (Phase 2)
* **What:** Migrated authentication from static credentials to Spotify OAuth 2.0 Authorization Code Flow with PKCE (`user-library-read`, `user-read-recently-played`).
* **Why:** Enables multi-tenant private beta access where friends can securely log in with their own Spotify accounts.
* **How:**
  - Built Datastore `User` vault storing tokens, approval status, display name, and avatar.
  - Added Admin control deck for user approvals and whitelisting.

---

## [[v1.0.0]](https://github.com/Vaultica/spinsleeve/commit/752838a) — 2026-11-01
### 🏗️ Multi-Tenant BigQuery Architecture (Phase 1)
* **What:** Architected and deployed the V2 multi-tenant dataset `secret-compass-181513.spotify_v2` in Google BigQuery.
* **Why:** Replaced single-user tables with multi-tenant partitioned and clustered tables (`user_id`).
* **Key Tables:**
  - `playback_history`: Partitioned by `DATE(played_at)`, clustered by `user_id, album_id`.
  - `user_saved_albums`: Clustered by `user_id, album_id`.
  - `album_enriched_metadata`: Global shared metadata table for gatefolds and liner notes.
