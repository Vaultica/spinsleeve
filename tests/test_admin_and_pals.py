import os
import sys
import unittest
import jinja2

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import (
    BETA_EXPLORER_HTML,
    BETA_RECOMMEND_HTML,
    BETA_ANALYTICS_HTML,
    BETA_PALS_HTML,
    ADMIN_HTML_TEMPLATE,
    PALS_LOCKED_HTML,
    ICON_A_SVG,
    APP_VERSION
)


class TestAdminAndPalsFeatures(unittest.TestCase):

    def setUp(self):
        self.templates = {
            "explorer": BETA_EXPLORER_HTML,
            "recommend": BETA_RECOMMEND_HTML,
            "analytics": BETA_ANALYTICS_HTML,
            "pals": BETA_PALS_HTML
        }
        self.dummy_context = {
            "brand_icon": ICON_A_SVG,
            "albums": [],
            "top_genres": [],
            "kpis": {"total_albums": 0, "unplayed_albums": 0, "played_albums": 0},
            "gatefold_icon": "",
            "pals": [],
            "selected_pal": {"display_name": "Buddy", "spotify_id": "buddy1", "avatar_url": "", "album_count": 10},
            "compatibility": {
                "match_pct": 85,
                "kinship": {
                    "tier": "Vinyl Soulmates",
                    "badge": "✨ Vinyl Soulmates",
                    "color": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
                    "desc": "Acoustic twins"
                },
                "artist_score": 80,
                "album_score": 90,
                "shared_artists_count": 5,
                "shared_albums_count": 3,
                "borrow_count": 4,
                "shared_artists": ["Radiohead", "Pink Floyd"]
            },
            "top_borrow": [],
            "shared_albums": [],
            "pal_crate": []
        }

    def test_original_spinning_turntable_icon(self):
        self.assertIn("@keyframes spin33", ICON_A_SVG)
        self.assertIn("spin-record", ICON_A_SVG)
        self.assertIn("#1DB954", ICON_A_SVG)

    def test_normal_user_does_not_see_switcher(self):
        """When rendered for a normal user (is_admin=False, is_impersonating=False),
        the fast test account switchers must not be present."""
        context = {
            **self.dummy_context,
            "user": {"display_name": "NormalUser", "user_id": "normal_user", "avatar_url": "", "pals_opt_in": False},
            "is_admin": False,
            "is_impersonating": False
        }
        for name, html in self.templates.items():
            with self.subTest(template=name):
                t = jinja2.Template(html)
                rendered = t.render(**context)
                self.assertNotIn("👑 Serge", rendered, f"Dev switcher leaked to normal user in {name}")
                self.assertNotIn("👩 Sarah", rendered, f"Dev switcher leaked to normal user in {name}")
                self.assertNotIn("🐹 GuineaPig", rendered, f"Dev switcher leaked to normal user in {name}")
                self.assertNotIn("⚙️ Admin", rendered, f"Admin deck link leaked to normal user in {name}")

    def test_admin_sees_admin_link_and_clean_header(self):
        """When rendered for an administrator (is_admin=True, is_impersonating=False),
        the admin link must be visible, but header switchers must be absent (POLISH-05)."""
        context = {
            **self.dummy_context,
            "user": {"display_name": "Serge", "user_id": "sergebou", "avatar_url": "", "pals_opt_in": True},
            "is_admin": True,
            "is_impersonating": False
        }
        for name, html in self.templates.items():
            with self.subTest(template=name):
                t = jinja2.Template(html)
                rendered = t.render(**context)
                self.assertIn("⚙️ Admin", rendered, f"Admin link missing for admin in {name}")
                self.assertNotIn("👑 Serge", rendered, f"Dev switcher should be removed from header in {name}")
                self.assertNotIn("👩 Sarah", rendered, f"Dev switcher should be removed from header in {name}")
                self.assertNotIn("🐹 GuineaPig", rendered, f"Dev switcher should be removed from header in {name}")

    def test_semantic_versioning_polish_04(self):
        """BETA v2 must be removed from the explorer header and replaced with dynamic APP_VERSION (POLISH-04)."""
        self.assertNotIn("BETA v2", BETA_EXPLORER_HTML)
        t = jinja2.Template(BETA_EXPLORER_HTML)
        context = {
            **self.dummy_context,
            "user": {"display_name": "Serge", "user_id": "sergebou", "avatar_url": "", "pals_opt_in": True},
            "app_version": APP_VERSION
        }
        rendered = t.render(**context)
        self.assertIn(APP_VERSION, rendered)

    def test_admin_impersonating_sees_revert(self):
        """When an admin is impersonating another user, the revert button must be visible."""
        context = {
            **self.dummy_context,
            "user": {"display_name": "Sarah", "user_id": "sarahboosch", "avatar_url": "", "pals_opt_in": True},
            "is_admin": True,
            "is_impersonating": True
        }
        for name, html in self.templates.items():
            with self.subTest(template=name):
                t = jinja2.Template(html)
                rendered = t.render(**context)
                self.assertIn("Assuming: Sarah", rendered)
                self.assertIn("↩ Revert", rendered)

    def test_impersonating_non_opted_in_shows_lock_tab_and_escape_banner(self):
        """When an admin impersonates a user who has NOT opted into SpinPals:
        1. The navigation tab should show the lock icon (🔒 SpinPals).
        2. The PALS_LOCKED_HTML template must have the impersonation banner,
           Admin Deck link, and Revert button to guarantee the admin never gets locked out."""
        context = {
            **self.dummy_context,
            "user": {"display_name": "Sarah", "user_id": "sarahboosch", "avatar_url": "", "pals_opt_in": False},
            "is_admin": True,
            "is_impersonating": True
        }
        # In explorer, recommend, analytics:
        for name in ["explorer", "recommend", "analytics"]:
            t = jinja2.Template(self.templates[name])
            rendered = t.render(**context)
            self.assertIn("SpinPals", rendered, f"Expected SpinPals tab in {name}")

        # In PALS_LOCKED_HTML:
        t_locked = jinja2.Template(PALS_LOCKED_HTML)
        rendered_locked = t_locked.render(session={"display_name": "Sarah"}, is_impersonating=True, is_admin=True, brand_icon=ICON_A_SVG)
        self.assertIn("↩ Revert to Admin", rendered_locked)
        self.assertIn("⚙️ Admin Deck", rendered_locked)
        self.assertIn("SpinPals: Members Only", rendered_locked)

    def test_admin_control_deck_features(self):
        """Verify Admin Control Deck has Assume View, SpinPals column, and toggle buttons.
        Also verify that sergebou is rendered as ACTIVE even if pals_opt_in was False/None in DB."""
        self.assertIn("👤 Assume View", ADMIN_HTML_TEMPLATE)
        self.assertIn("/beta/admin/assume/", ADMIN_HTML_TEMPLATE)
        self.assertIn("/beta/admin/toggle-pals/", ADMIN_HTML_TEMPLATE)
        self.assertIn("SpinPals Social", ADMIN_HTML_TEMPLATE)

        # Test rendering admin user row with pals_opt_in=False
        t = jinja2.Template(ADMIN_HTML_TEMPLATE)
        dummy_users = [
            {"spotify_id": "sergebou", "display_name": "Serge", "role": "admin", "pals_opt_in": False, "is_approved": True},
            {"spotify_id": "sarahboosch", "display_name": "Sarah", "role": "user", "pals_opt_in": False, "is_approved": True}
        ]
        rendered = t.render(users=dummy_users, brand_icon=ICON_A_SVG, is_impersonating=False)
        self.assertIn("ACTIVE", rendered)
        self.assertIn("DISABLED", rendered)

    def test_user_settings_sync_pause_and_pals(self):
        """Verify that user settings dropdown includes SpinPals opt-in and Scrobble Sync Pause controls."""
        context = {
            **self.dummy_context,
            "user": {"display_name": "Serge", "user_id": "sergebou", "avatar_url": "", "pals_opt_in": True, "sync_paused": False},
            "is_admin": True,
            "is_impersonating": False
        }
        t = jinja2.Template(BETA_EXPLORER_HTML)
        rendered = t.render(**context)
        self.assertIn("palsOptInStatusBadge", rendered)
        self.assertIn("syncPauseStatusBadge", rendered)
        self.assertIn("toggleUserSyncPause", rendered)
        self.assertIn("toggleUserPalsOptIn", rendered)


if __name__ == "__main__":
    unittest.main()
