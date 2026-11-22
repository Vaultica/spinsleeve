"""
Unit tests for APP-17 Unified Crate Workspace Architecture and UI integration.
"""
import os
import sys
import unittest
import jinja2

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import (
    BETA_EXPLORER_HTML,
    ICON_A_SVG,
    ICON_GATEFOLD_SVG
)


class TestApp17UnifiedCrate(unittest.TestCase):
    """Test suite for APP-17 Unified Crate Workspace Architecture."""

    def test_unified_control_deck_elements_present(self):
        """Verify APP-17 control deck buttons and functions exist in explorer.html template."""
        self.assertIn("btnSaved", BETA_EXPLORER_HTML)
        self.assertIn("btnUnowned", BETA_EXPLORER_HTML)
        self.assertIn("btnDigger", BETA_EXPLORER_HTML)
        self.assertIn("setScope", BETA_EXPLORER_HTML)
        self.assertIn("toggleDiggerMode", BETA_EXPLORER_HTML)
        self.assertIn("diggerModeToggleContainer", BETA_EXPLORER_HTML)

    def test_template_rendering_cleanly(self):
        """Verify explorer.html compiles and renders cleanly with mock user, albums, and unowned albums."""
        template = jinja2.Template(BETA_EXPLORER_HTML)
        mock_albums = [{
            "album_id": "test_1",
            "album_name": "Kid A",
            "album_artist_name": "Radiohead",
            "album_image_url": "https://example.com/cover.jpg",
            "release_year": "2000",
            "album_track_plays": 15,
            "album_track_plays_30d": 3,
            "has_gatefold": True
        }]
        mock_unowned = [{
            "album_id": "test_2",
            "album_name": "Untrue",
            "album_artist_name": "Burial",
            "album_image_url": "https://example.com/unowned.jpg",
            "play_count": 8
        }]
        mock_user = {
            "user_id": "test_collector",
            "display_name": "Test Collector",
            "pals_opt_in": True
        }
        mock_kpis = {
            "total_albums": 1,
            "played_albums": 1,
            "played_albums_30d": 1,
            "unplayed_albums": 0,
            "pct_explored": 100.0
        }

        rendered = template.render(
            albums=mock_albums,
            unowned_albums=mock_unowned,
            top_genres=["electronic", "ambient"],
            kpis=mock_kpis,
            user=mock_user,
            brand_icon=ICON_A_SVG,
            gatefold_icon=ICON_GATEFOLD_SVG,
            is_admin=False,
            is_impersonating=False
        )
        self.assertIn("Saved Vinyl", rendered)
        self.assertIn("Streamed / Unowned", rendered)
        self.assertIn("Crate Digger Mode", rendered)
        self.assertIn("Kid A", rendered)
        self.assertIn("Burial", rendered)

    def test_crate_digger_mode_three_column_spotlight_design(self):
        """Verify that spotlight curated picks container specifies 3 columns (grid-cols-1 md:grid-cols-3)."""
        self.assertIn("grid-cols-1 md:grid-cols-3", BETA_EXPLORER_HTML)


if __name__ == "__main__":
    unittest.main()
