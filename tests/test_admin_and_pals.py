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
    ICON_A_SVG
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

    def test_admin_sees_switcher(self):
        """When rendered for an administrator (is_admin=True, is_impersonating=False),
        the admin link and switchers must be visible."""
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
                self.assertIn("👩 Sarah", rendered, f"Switcher missing for admin in {name}")

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

    def test_admin_control_deck_features(self):
        """Verify Admin Control Deck has Assume View, SpinPals column, and toggle buttons."""
        self.assertIn("👤 Assume View", ADMIN_HTML_TEMPLATE)
        self.assertIn("/beta/admin/assume/", ADMIN_HTML_TEMPLATE)
        self.assertIn("/beta/admin/toggle-pals/", ADMIN_HTML_TEMPLATE)
        self.assertIn("SpinPals Social", ADMIN_HTML_TEMPLATE)

    def test_pals_locked_template(self):
        """Verify PALS_LOCKED_HTML renders cleanly with lock icon and return to library link."""
        t = jinja2.Template(PALS_LOCKED_HTML)
        rendered = t.render(user={"display_name": "NewUser"}, brand_icon=ICON_A_SVG)
        self.assertIn("SpinPals: Members Only", rendered)
        self.assertIn("Return to Library Explorer", rendered)


if __name__ == "__main__":
    unittest.main()
