import os
import sys
import unittest
import jinja2

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import (
    BETA_RECOMMEND_HTML,
    ICON_A_SVG,
    ICON_GATEFOLD_SVG
)


class TestCrateDiggerPolish(unittest.TestCase):
    """Test suite for POLISH-01: Crate Digger UX streamlining and vibe harmonisation."""

    def test_recommend_template_jinja_compilation(self):
        """Verify BETA_RECOMMEND_HTML compiles and renders cleanly with mock KPIs and albums."""
        template = jinja2.Template(BETA_RECOMMEND_HTML)
        mock_kpis = {
            "total_albums": 120,
            "played_albums": 80,
            "played_albums_30d": 25,
            "unplayed_albums": 40,
            "pct_explored": 66.7,
            "total_plays": 540,
            "total_plays_30d": 110,
            "top_album": "OK Computer",
            "top_album_plays": 35
        }
        mock_user = {
            "user_id": "test_collector",
            "display_name": "Test Collector",
            "pals_opt_in": True
        }
        rendered = template.render(
            albums=[],
            top_genres=["indie rock", "ambient", "jazz"],
            kpis=mock_kpis,
            user=mock_user,
            brand_icon=ICON_A_SVG,
            gatefold_icon=ICON_GATEFOLD_SVG,
            is_admin=False,
            is_impersonating=False
        )
        self.assertIn("1. Crate Target:", rendered)
        self.assertIn("Heavy Rotation (30D: 25)", rendered)
        self.assertIn("Unplayed Gems (40)", rendered)
        self.assertIn("Cold Shelf (55)", rendered)
        self.assertIn("All-Time Favorites (80)", rendered)
        self.assertIn("Full Crate (120)", rendered)

    def test_streamlined_target_buttons_present(self):
        """Verify the 5 single-dimension crate target focus buttons are present in the HTML."""
        self.assertIn("setTarget('heavy_30d')", BETA_RECOMMEND_HTML)
        self.assertIn("setTarget('unplayed')", BETA_RECOMMEND_HTML)
        self.assertIn("setTarget('cold')", BETA_RECOMMEND_HTML)
        self.assertIn("setTarget('classics')", BETA_RECOMMEND_HTML)
        self.assertIn("setTarget('all')", BETA_RECOMMEND_HTML)

    def test_backward_compatibility_ids_and_functions(self):
        """Verify legacy button IDs and helper functions exist for test and API compatibility."""
        self.assertIn('id="horizonBtn-30d"', BETA_RECOMMEND_HTML)
        self.assertIn('id="horizonBtn-all"', BETA_RECOMMEND_HTML)
        self.assertIn('id="modeBtn-discover"', BETA_RECOMMEND_HTML)
        self.assertIn('function setHorizon(', BETA_RECOMMEND_HTML)
        self.assertIn('function setMode(', BETA_RECOMMEND_HTML)

    def test_balanced_vibes_definitions(self):
        """Verify the VIBES JavaScript dictionary has balanced, enriched genre keywords."""
        self.assertIn("'shoegaze'", BETA_RECOMMEND_HTML)
        self.assertIn("'trip hop'", BETA_RECOMMEND_HTML)
        self.assertIn("'chamber pop'", BETA_RECOMMEND_HTML)
        self.assertIn("'classic soul'", BETA_RECOMMEND_HTML)
        self.assertIn("'motown'", BETA_RECOMMEND_HTML)
        self.assertIn("'garage rock'", BETA_RECOMMEND_HTML)
        # Verify broad 'rock' alone is not in energetic keywords to prevent skewed distribution
        self.assertNotIn("'rock',", BETA_RECOMMEND_HTML)

    def test_vintage_release_year_fallback(self):
        """Verify that vintage vibe considers albums released prior to 1985 as vintage."""
        self.assertIn("y < 1985", BETA_RECOMMEND_HTML)

    def test_spin_again_button_deduplication(self):
        """Verify POLISH-07: exactly one Spin Again button exists on the Control Deck console."""
        spin_count = BETA_RECOMMEND_HTML.count('onclick="spinAgain()"')
        self.assertEqual(spin_count, 1, "Should have exactly one Spin Again button (de-duplicated from header)")
        self.assertIn('<span>🎲</span> Spin Again', BETA_RECOMMEND_HTML)

    def test_recommend_route_renders_without_key_error(self):
        """Verify that visiting /recommend via Flask test client succeeds (200 OK) with valid kpis payload."""
        from report_v2.app import app
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "test_user"
                sess["display_name"] = "Test User"
            res = client.get("/recommend", follow_redirects=True)
            self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
