# SpinSleeve V2: Manual UI & Integration Testing Runbook

This runbook defines the structured manual verification checklist for testing SpinSleeve V2 locally (or in beta staging environments) after code refactoring, bug fixes, or feature delivery.

---

## 1. Test Environment Setup
1. Start the local Flask development server against your GCP project credentials:
   ```bash
   cd src/report_v2
   export GCP_PROJECT=secret-compass-181513
   export FLASK_DEBUG=1
   python3 app.py
   ```
2. Open your browser at `http://localhost:8080`.

---

## 2. Comprehensive UI & Integration Validation Checklist

### 🚪 Auth & Landing (`/login`)
- [ ] **Rotating Vinyl Platter:** Verify the original 33⅓ RPM spinning vinyl platter SVG (`ICON_A_SVG`) spins smoothly on the landing page.
- [ ] **Spotify OAuth Flow:** Click **"Connect with Spotify"**, authorize via OAuth PKCE callback (`/callback`), and confirm successful redirection to the main library explorer.

### 🏛️ Library Explorer (`/` & `/beta/`) & Logo Home Navigation
- [ ] **Logo Home Button:** Click the **SpinSleeve logo / title block** on the top left from any view (Analytics, SpinPals, or Crate Digger). Verify it acts as a home button, instantly navigating back to the main Library view.
- [ ] **Virtual Record Crate:** Confirm album sleeves load in grid view with normalized play count badges (`🔥 X Plays`).
- [ ] **Sorting Controls:** Test all options in the **Sort dropdown** (*Artist A-Z*, *Albums Year desc*, *Heavy Rotation 30D*).
- [ ] **30-Second Audio Previews:** Hover over album cards to verify needle-drop audio preview snippets play correctly.
- [ ] **12" Gatefold Archival Reader & Zero-Flash Tracklist:** 
  - Click any album sleeve to open the gatefold modal. Verify that archival liner notes, scores, and tracklists appear.
  - **Zero Track Flashing:** Switch rapidly between different albums. Confirm that opening a new gatefold instantly clears the previous album's tracklist and displays the loading pulse placeholder (`"Loading physical vinyl tracklist..."`) with zero visual lingering of old tracks.
  - **In-Memory & Datastore Caching:** Click the same album multiple times. Verify subsequent opens load instantly (<50ms) via in-memory and Cloud Datastore cache (`exclude_from_indexes`, zero 1500-byte property size warnings).

### 🎛️ Crate Digger (`/recommend` & Workspace Switcher)
- [ ] **Unified Workspace Navigation:** Confirm Crate Digger is integrated as a sub-tab / mode inside the Library workspace (`Saved Vinyl` | `Crate Digger` | `Streamed / Unowned`), with no redundant top-level Crate Digger tab in the header.
- [ ] **Full Library Scope:** Switch to Crate Digger mode while the library is sorted by heavy rotation. Verify that recommendations evaluate against the **full library collection** rather than being restricted to the 30-day subset.
- [ ] **Vibe & Era Filters:** Test discovery vibe pills (*Chill, Energetic, Mellow, Vintage*).
- [ ] **Time Horizon Switcher:** Toggle between *🔥 Heavy Rotation (Last 30 Days)* and *🏛️ All-Time Collection*, verifying recommendation weights and pool updates.
- [ ] **Spin Again:** Click **"Spin Again"** to verify recommendation shuffling.

### 📊 Telemetry & Analytics (`/analytics`)
- [ ] **Listening Clock Heatmap:** Confirm the listening clock heatmap renders correctly.
- [ ] **Timeframes:** Switch between dynamic date ranges (7d, 30d, This Year, All-Time) and verify listening telemetry updates.

### 🤝 SpinPals CrateMates (`/pals`)
- [ ] **Listening Lounge:** Verify the member directory loads active friend avatars and record counts.
- [ ] **Compatibility Gauge:** Check the hybrid acoustic chemistry gauge and Top 5 borrow recommendations.

### 👑 Admin Control Deck (`/admin`)
- [ ] **Pre-Approvals & Toggles:** Verify whitelist pre-approvals table and SpinPals opt-in toggles.
- [ ] **Admin Impersonation:** Click **"Assume View"** on a test user. Verify the persistent `↩ Revert` escape banner appears in the header. Click `↩ Revert` to return safely to admin mode.

### ⚙️ User Settings & Avatar Picker (`APP-04` & `APP-12`)
- [ ] **Header Profile Dropdown:** Click your avatar in the header to open the dropdown menu.
- [ ] **Music Legend Persona Picker:** Open the avatar picker modal, select a legend (e.g., *Chet Baker* or *David Bowie*), and save. Verify the avatar updates instantly across the header.
- [ ] **Privacy Toggles:** Test the **SpinPals Opt-In/Out** and **Scrobble Sync Pause** toggle switches.
