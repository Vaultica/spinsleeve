# SpinSleeve Engineering Changelog & Release Journal

All notable technical updates, architectural decisions, feature implementations, and deployment revisions for **SpinSleeve** (`https://spinsleeve.cc`) are documented chronologically in this journal.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), with deep engineering rationales (*What, How, and Why*).

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
