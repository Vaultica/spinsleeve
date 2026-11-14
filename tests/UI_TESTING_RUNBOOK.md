# SpinSleeve V2: Manual UI Testing Runbook

This runbook defines the structured manual verification checklist for testing SpinSleeve V2 locally (or in beta staging environments) after code refactoring, modularisation (`OPS-04`), or feature delivery.

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

## 2. Comprehensive UI Validation Checklist

### 🚪 Auth & Landing (`/login`)
- [ ] **Rotating Vinyl Platter:** Verify the original 33⅓ RPM spinning vinyl platter SVG (`ICON_A_SVG`) spins smoothly on the landing page.
- [ ] **Spotify OAuth Flow:** Click **"Connect with Spotify"**, authorize via OAuth PKCE callback (`/callback`), and confirm successful redirection to the main library explorer.

### 🏛️ Library Explorer (`/` & `/beta/`)
- [ ] **Virtual Record Crate:** Confirm album sleeves load in grid view with normalized play count badges (`🔥 X Plays`).
- [ ] **Sorting Controls:** Test all options in the **Sort dropdown** (*Artist A-Z*, *Albums Year desc*, *Heavy Rotation 30D*).
- [ ] **30-Second Audio Previews:** Hover over album cards to verify needle-drop audio preview snippets play correctly.
- [ ] **12" Gatefold Archival Reader:** Click any album sleeve to open the gatefold modal. Check that archival liner notes (Wikipedia summary, Pitchfork/Discogs scores) and tracklists appear correctly. Test the interactive audio scrubber and pause controls.

### 🎛️ Crate Digger (`/recommend`)
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
