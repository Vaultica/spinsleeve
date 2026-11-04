# SpinSleeve: Architecture, Roadmap & Feature Specs

**Domain:** `https://spinsleeve.cc` (Production) • `https://spinsleeve.cc/beta` (Multi-Tenant V2)  
**Project ID:** `secret-compass-181513` | **Compute Region:** `europe-west2` (London) | **BigQuery Region:** `US`

---

## 1. Executive Summary & Implemented Phases

SpinSleeve transforms a personal Spotify library into a physical-style vinyl record crate, offering archival 12" gatefold liner notes (Wikipedia, Pitchfork, Discogs), deep listening telemetry, and friend-to-friend taste compatibility.

### ✅ Completed Implementation Phases

#### Phase 1: Multi-Tenant Data Foundation & User Vault
* **BigQuery `spotify_v2` Isolation:** Provisioned partitioned and clustered tables (`playback_history`, `user_saved_albums`) isolated strictly by `user_id`. Universal shared metadata table (`album_enriched_metadata`) prevents redundant scraping costs across tenants.
* **Cloud Datastore User Vault:** Created serverless `User` kind keyed by Spotify ID to store user credentials, display names, profile avatars, approval gates (`is_approved`), and offline OAuth refresh tokens.
* **User Management CLI (`manage_users.py`):** Administrative tool to list, whitelist, approve with roles (`admin` / `user`), and revoke user access directly in Datastore.

#### Phase 2: Spotify OAuth 2.0 PKCE & Beta Routing
* **Spotify OAuth PKCE:** Implemented multi-user authorization code flow with dynamic callback URI resolution (`https://spinsleeve.cc/beta/callback`) and account chooser enforcement (`show_dialog=True`).
* **Firebase CDN Reverse Proxy:** Configured `firebase.json` rewrites routing `/beta` and `/beta/**` to Cloud Run service `spotify-dashboard-beta`, keeping V1 production completely isolated.
* **Session Cookie Architecture:** Enforced Flask session cookie `__session` at `path="/"` to prevent CDN stripping by Firebase Hosting.
* **Onboarding & Invite Gate:** Added instant 50-track and 50-album background sync upon first approved login, with a clean holding room for pending invitees.

#### Phase 3: Feature Parity & Crate Digger
* **Audio Previews:** Integrated 30-second audio preview snippets on card hover and in gatefold modals with animated soundwave indicators.
* **Smart Crate Digger (`/beta/recommend`):** Algorithmic discovery engine supporting *Discover* (unplayed records) vs *Favorites* (heavy rotation), vibe filters (*Late Night/Chill, Energetic, Mellow, Vintage*), release eras, and subgenres.
* **Analytics with "This Year" Filter (`/beta/analytics`):** Dynamic time windows (24h, 7d, 30d, 60d, 90d, This Year, All Time, Custom Flatpickr date range) with listening clock heatmaps and taste velocity tracking.
* **Library Sort Options:** Added *Artist (A-Z), Albums (Year desc)* sorting alongside traditional play count and date-added sorts.

#### Phase 4: Automated Multi-Tenant Pipeline
* **Cloud Run Job (`spotify-v2-pipeline-job`):** Automated multi-tenant worker that iterates over all approved users in Datastore, refreshes their access tokens, syncs new plays and saved albums, and archives raw JSON to Cloud Storage.
* **Cloud Scheduler (`spotify-v2-sync-scheduler`):** Triggers the pipeline job automatically every 2 hours via OIDC service account authentication.

#### Phase 5a: Multi-User Social Superpowers (SpinPals: CrateMates Edition)
* **The Listening Lounge Directory:** Horizontal club directory showing active members (Serge, Sarah, GuineaPig) with avatars and saved record counts.
* **Hybrid Acoustic Chemistry Gauge:** Calculates compatibility score combining 50% artist/stream overlap + 50% exact album overlap, with dynamic kinship badges (*Vinyl Soulmates, Acoustic Kin, Crate Companions, Curious Explorers, Fresh Discoveries*).
* **Top 5 Meaningful Borrow Recommendations:** Algorithmic curation highlighting records on a friend's shelf you don't own, weighted by the friend's heavy rotation, taste affinity, and Pitchfork/Discogs ratings.
* **Virtual Crate Digging:** Interactive grid allowing you to browse a friend's entire library, preview audio, read gatefold liner notes, and see `🤝 Both Own` tags.
* **1-Click Fast Switcher:** Header switcher enabling 1-click perspective switching between Serge, Sarah, and GuineaPig during testing.

---

## 2. Upcoming Phases Before Production Go-Live

```text
  Phase 5b: Pre-Production UI Polish  ──►  Phase 6: Production Cutover  ──►  Phase 7: Apple Music Onboarding
  (Mobile gatefolds, scrubbers, links)      (spinsleeve.cc zero-downtime)     (Cross-platform crate & SpinPals)
```

### ✅ Phase 5b: Pre-Production Gatefold Polish (COMPLETED)
* **Mobile-Compact Header:** Optimized the 12" gatefold header on screens `<768px` to ensure album thumbnail (64x64px), title, artist, Spotify/Apple Music buttons, and close button occupy `<110px` without vertical scrolling.
* **Interactive Audio Progress Scrubber:** Added a visual 30-second seek-bar allowing users to click, tap, or scrub through audio snippets in the gatefold modal with live timestamp display (`0:00 / 0:30`).
* **Archival Deep Links:** Added external badge links directly to original Pitchfork reviews, Discogs release pages with vote counts, Wikipedia articles, and Metacritic inside the gatefold reader.
* **Direct Apple Music Redirector:** Provided one-click deep links (`https://music.apple.com/search?term=...`) to open albums directly in the Apple Music native app or web player.
* **Retained Invariants:** Preserved the Spotify green play button (`#1DB954`) and the "SpinSleeve Verified" badge at the sleeve footer.

### ✅ Phase 6: Production Cutover & Retirement of V1 (COMPLETED)
* **Zero-Downtime Routing Flip:** Updated `firebase.json` rewrites so that root domain `https://spinsleeve.cc` points directly to the multi-tenant V2 service (`spotify-dashboard-beta`).
* **Symmetric Routing:** Enabled root paths (`/`, `/recommend`, `/analytics`, `/pals`, `/admin`, `/login`, `/logout`) while preserving `/beta/*` backwards compatibility.
* **Deprecate V1 Resources:** Paused legacy single-user Cloud Scheduler (`spotify-daily-sync`) in favor of automated multi-tenant pipeline (`spotify-v2-sync-scheduler`).

### ⏳ Phase 7: Cross-Platform Streaming: Apple Music Library Collection Onboarding
* **MusicKit JS Client Integration:** Integrate Apple MusicKit JS v3 for client-side user authentication (`music.authorize()`), enabling friends on Apple Music to onboard their record collections without Spotify allowlist restrictions.
* **Backend Apple Developer Token Minting:** Implement automated ES256 Developer JWT signing using Apple Music Private Key (`.p8`) stored in GCP Secret Manager.
* **Apple Music Library Collection Ingestion (`sync.py` & Initial Ingestion):** Ingest user saved library albums via `GET /v1/me/library/albums?include=catalog` with pagination, mapping album artwork, release dates, track counts, and catalog UPCs.
* **Provider-Agnostic User Vault & BigQuery Architecture:** Extend Datastore `User` entity to support `provider: "apple_music"`, store 6-month Media User Tokens (`Music-User-Token`), and update BigQuery `user_albums_features` to join archival liner notes across both platforms via normalized `(artist, album)` and UPC.
* **Cross-Platform SpinPals & Shared Vinyl:** Update acoustic chemistry and `🤝 Both Own` crate comparison to resolve shared albums across Spotify and Apple Music users seamlessly.
* **Effort & Complexity:**
  - **Estimated Effort:** ~16–24 hours (2 to 3 days)
  - **Technical Complexity:** **Medium** (Dual authentication management, browser popup handling, 6-month token lifecycle, and cross-catalog metadata normalization)

---

## 3. Future Feature Specifications & Product Ideas

### 🎨 Feature 1: Iconic Music Legend Avatar Picker
* **Problem:** Some users do not have custom Spotify profile pictures, or prefer a stylized artistic persona inside the vinyl club.
* **Solution:** An avatar selector offering illustrated avatars of legendary music figures:
  - ⚡ **David Bowie** (*Aladdin Sane lightning bolt*)
  - 🕶️ **The Beatles** (*Abbey Road / Sgt. Pepper silhouettes*)
  - 🎹 **Wolfgang Amadeus Mozart** (*Classical wig & quill*)
  - 🐝 **Beyoncé** (*Renaissance disco hat*)
  - 🧤 **Michael Jackson** (*Fedora & silver glove*)
  - 🎸 **Elvis Presley** (*Pompadour & sunglasses*)
  - 🕶️ **Miles Davis** (*Trumpet silhouette*)
  - 🎤 **Amy Winehouse** (*Beehive & eyeliner*)
* **Implementation:**
  - Store vector SVG illustrations in `/static/avatars/`.
  - Add an "Avatar Settings" modal in the top navigation.
  - Store `custom_avatar_id` in the Datastore `User` entity, falling back to Spotify's profile picture if unselected.
* **Effort & Complexity:**
  - **Estimated Effort:** ~4–5 hours (0.5 day)
  - **Technical Complexity:** **Low** (Vector SVG curation, adding `custom_avatar_id` to Datastore, and updating frontend avatar rendering)

---

### 🛡️ Feature 2: Social Privacy & Data Sharing Opt-In Gate
* **Problem:** Users should have explicit control over whether their listening history and record collection are visible to other club members.
* **Solution:** A first-login consent screen and ongoing privacy toggle:
  - **On First Login:** Users are presented with a clear consent card:
    > *"Would you like to join the Listening Lounge? By opting in, friends in the club can see your saved albums, calculate taste compatibility, and crate dig through your collection."*
  - **If Declined:**
    - Their profile is hidden from the Listening Lounge directory.
    - The `SpinPals` tab is disabled or displays a private state.
    - Their albums and plays are excluded from friend compatibility calculations.
  - **Privacy Settings:** A toggle in their profile menu allows them to enable or disable social sharing at any time.
* **Implementation:**
  - Add `social_opt_in` (Boolean, default `False` until accepted) to the Datastore `User` entity.
  - Modify `fetch_pals_directory` to filter for `social_opt_in == True`.
* **Effort & Complexity:**
  - **Estimated Effort:** ~4–6 hours (0.5 to 1 day)
  - **Technical Complexity:** **Low** (First-login modal prompt, Datastore boolean flag, and filtering queries in `fetch_pals_directory`)

---

### 🔔 Feature 3: Real-Time Admin Notification for New Join Requests
* **Problem:** When an uninvited friend logs in for the first time, their account sits in `PENDING` state until the admin happens to check the Admin Control Deck.
* **Solution:** Immediate push or email alerts to Serge whenever a new Spotify user logs in:
  - **Notification Channels:**
    1. **Telegram / Discord Bot Webhook:** Instant ping with user name, email, and one-click `[Approve]` link.
    2. **SendGrid / Postmark Email Alert:** Formatted email notification sent directly to `serge.bouschet@gmail.com`.
    3. **Google Cloud Pub/Sub & Cloud Functions:** Triggered automatically upon Datastore `User` creation where `is_approved == False`.
* **Example Alert Message:**
  ```text
  📢 New SpinSleeve Join Request!
  • Name: Charlie Watts
  • Spotify ID: charliewatts123
  • Email: charlie@rollingstones.com
  👉 Click here to approve: https://spinsleeve.cc/beta/admin
  ```
* **Effort & Complexity:**
  - **Estimated Effort:** ~3–4 hours (0.5 day)
  - **Technical Complexity:** **Low** (Webhook POST to Telegram Bot API or transactional email via SendGrid when `is_approved == False`)

---

### 💡 Feature 4: In-App Feedback & Feature Wishlist Collector
* **Problem:** Friends testing the private beta need an easy, frictionless way to report bugs, suggest records for liner notes enrichment, or request new features without leaving the app.
* **Solution:** A lightweight, built-in feedback drawer:
  - **UI Trigger:** A subtle floating button or navigation link: `💬 Feedback`.
  - **Modal Form:**
    - Category: `🐛 Bug Report`, `✨ Feature Request`, `💿 Album Enrichment Request`, `❤️ General Love`.
    - Note input: Multi-line text field.
    - Context auto-attached: Current user ID, browser OS, active route, timestamp.
  - **Storage:** Feedback stored in Datastore under a new `Feedback` kind, viewable in the `/beta/admin` panel with status pills (`New`, `In Progress`, `Implemented`).
* **Effort & Complexity:**
  - **Estimated Effort:** ~5–7 hours (1 day)
  - **Technical Complexity:** **Low–Medium** (Modal UI drawer, Datastore `Feedback` kind, and `/beta/admin` triage dashboard)

---

### 🍏 Feature 5: Cross-Platform Streaming: Apple Music Library Collection Onboarding
* **Problem:**
  1. Many music lovers and vinyl collectors stream primarily through Apple Music rather than Spotify.
  2. Spotify enforces strict developer allowlists (hard-capped at 5–25 users in Development Mode with no programmatic API to add them) and requires 250k MAU + business registration for Quota Extension.
  3. SpinSleeve is currently locked to Spotify OAuth for user onboarding, artificially restricting the vinyl club's reach.
* **Solution:**
  Allow users to authenticate and onboard their entire saved album collection from **Apple Music** into SpinSleeve's virtual vinyl crate, enjoy full 12" gatefold archival liner notes, preview audio, and crate dig with friends via SpinPals.
* **API Feasibility & Data Availability:**
  - **Library Endpoint:** `GET https://api.music.apple.com/v1/me/library/albums?include=catalog` (supports pagination up to 100 items per request).
  - **Data Acquired:** Local & catalog album titles, artist names, artwork URLs (`600x600`), release dates, track counts, dates added to library, genre names, record labels, and universal catalog barcodes (UPC).
  - **Audio Previews:** Apple Music catalog provides 30-second AAC audio snippets (`previewUrl`), and SpinSleeve already has an active iTunes Search API preview engine in `app.py`.
  - **Archival Metadata Enrichment:** Existing Wikipedia liner notes, Pitchfork reviews, and Discogs ratings map automatically to Apple Music albums by joining on `LOWER(TRIM(artist_name))` and `LOWER(TRIM(album_name))` or catalog UPC.
* **Detailed Technical Architecture:**
  1. **Apple Developer Configuration:**
     - Provision MusicKit Private Key (`.p8`), Key ID, and Team ID in Apple Developer Portal ($99/yr program).
     - Store private key securely in GCP Secret Manager (`apple-musickit-p8-key`).
  2. **Authentication Flow (MusicKit JS v3):**
     - Cloud Run backend exposes `GET /beta/api/musickit-token` to serve short-lived signed ES256 Developer JWTs.
     - Login page `/beta/login` provides `🍏 Connect with Apple Music` alongside `🟢 Connect with Spotify`.
     - Frontend invokes `MusicKit.getInstance().authorize()`, triggering Apple's native authentication popup.
     - On approval, the client receives a **Media User Token (`Music-User-Token`)** and POSTs it to `/beta/auth/apple`.
     - Display name is resolved via user's personal radio station (`GET /v1/catalog/{storefront}/stations?filter[identity]=personal`) or user input prompt.
  3. **User Vault & Token Lifecycle:**
     - Datastore `User` entity gains:
       - `provider`: `"apple_music"`
       - `apple_user_token`: Encrypted `Music-User-Token`
       - `storefront`: User's regional storefront (e.g., `"us"`, `"gb"`)
       - `token_issued_at` / `token_expires_at`: 6-month validity window (prompting re-auth once per 180 days).
  4. **Multi-Tenant Ingestion Pipeline (`src/pipeline_v2/sync.py`):**
     - Add `sync_apple_music_user_saved_albums()` supporting `limit=100` and `offset` pagination.
     - Normalizes artwork URLs by replacing `{w}x{h}` with `600x600`.
     - Ingests into BigQuery `spotify_v2.user_saved_albums` with `provider: 'apple'` and `album_id: 'am_<catalog_id>'`.
  5. **Cross-Platform SpinPals & Shared Vinyl:**
     - Update `current_user_owns` join in `compute_pals_compatibility()` from exact `album_id` to normalized `(artist_name, album_name)` and UPC.
     - Allows Spotify users and Apple Music users to dig through each other's crates, calculate acoustic kinship, and display `🤝 Both Own` badges across different platforms.
* **Effort & Complexity:**
  - **Estimated Effort:** ~16–24 hours (2 to 3 days)
  - **Technical Complexity:** **Medium** (Dual auth providers, MusicKit JS popup flows, 6-month token expiration handling, and cross-catalog metadata normalization)

---

## 4. Pipeline Effort & Complexity Evaluation Matrix

| Milestone / Feature | Scope & Focus | Estimated Effort | Complexity | Key Tech Stack & Dependencies | Strategic Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 5b: Gatefold Polish** | Mobile <110px header, audio progress scrubber, Pitchfork/Discogs links | **4–6 hours** (0.5–1 day) | **Low** | Tailwind CSS, Vanilla JS Audio API, HTML5 | Polishes core listening experience for mobile beta testers before launch. |
| **Phase 6: Production Cutover** | Zero-downtime Firebase rewrite flip to `spinsleeve.cc`, V1 retirement | **2–3 hours** (0.5 day) | **Low** | Firebase Hosting, Cloud Run, Cloud Scheduler | Launches multi-tenant V2 to the public domain and reduces legacy cloud costs. |
| **Feature 1: Legend Avatar Picker** | Stylized SVG musician avatars (Bowie, Beatles, Mozart, etc.) | **4–5 hours** (0.5 day) | **Low** | SVG Assets, Cloud Datastore, Tailwind CSS | High aesthetic delight; gives users iconic club personas without Spotify profile photos. |
| **Feature 2: Social Privacy Opt-In** | First-login consent prompt and toggle to hide profile from Lounge | **4–6 hours** (0.5–1 day) | **Low** | Datastore `User`, BigQuery query filters | Ensures GDPR/privacy compliance and lets cautious users keep their crates private. |
| **Feature 3: Real-Time Admin Alerts** | Telegram Bot webhook or SendGrid email on new pending join requests | **3–4 hours** (0.5 day) | **Low** | Telegram Bot API / SendGrid, Secret Manager | Instant mobile notification for Serge to approve friends in 1 click without checking dashboard. |
| **Feature 4: In-App Feedback Drawer** | Floating feedback widget with categorization and admin triage deck | **5–7 hours** (1 day) | **Low–Medium** | Cloud Datastore (`Feedback`), Flask, Admin UI | Frictionless bug reporting and liner notes suggestions directly from beta testers. |
| **Phase 7 / Feature 5: Apple Music Onboarding** | Full library ingestion from Apple Music via MusicKit JS and BigQuery sync | **16–24 hours** (2–3 days) | **Medium** | MusicKit JS v3, Apple Developer Key (.p8), BigQuery, Cloud Run Job | **Massive:** Bypasses Spotify allowlist limits and expands SpinSleeve to all Apple Music friends. |
