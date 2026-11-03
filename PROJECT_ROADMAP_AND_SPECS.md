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
  Phase 5b: Pre-Production UI Polish  ──►  Phase 6: Production Cutover  ──►  LIVE
  (Mobile gatefolds, scrubbers, links)      (spinsleeve.cc zero-downtime)
```

### ⏳ Phase 5b: Pre-Production Gatefold Polish
* **Mobile-Compact Header:** Optimize the 12" gatefold header on screens `<768px` to ensure album title, artist, and play buttons occupy `<110px` without vertical scrolling.
* **Interactive Audio Progress Scrubber:** Add a visual 30-second seek-bar allowing users to drag or click to scrub through audio snippets in the gatefold modal.
* **Archival Deep Links:** Add external badge links directly to original Pitchfork reviews, Discogs release pages, and Wikipedia articles inside the gatefold reader.
* **Direct Apple Music Redirector:** Provide one-click deep links to open albums directly in the Apple Music native app.

### ⏳ Phase 6: Production Cutover & Retirement of V1
* **Zero-Downtime Routing Flip:** Update `firebase.json` rewrites so that root domain `https://spinsleeve.cc` points directly to `spotify-dashboard-beta` (renamed to `spotify-dashboard-service`).
* **Deprecate V1 Resources:** Decommission legacy single-user pipeline job (`spotify-pipeline-job`) and legacy scheduler (`spotify-daily-sync`).
* **BigQuery V1 Archival:** Archive legacy dataset tables (`spotify_prod`) into long-term backup storage.

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
