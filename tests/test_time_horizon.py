import os
import sys
import unittest
import jinja2

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import (
    compute_normalized_album_plays,
    BETA_EXPLORER_HTML,
    BETA_RECOMMEND_HTML,
    BETA_PALS_HTML,
    ICON_A_SVG,
    ICON_GATEFOLD_SVG
)


class TestTimeHorizonRecommendations(unittest.TestCase):

    def test_compute_normalized_album_plays_30d(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(
            track_plays=24, tracks_total=12, is_30d=True
        )
        self.assertEqual(norm_plays, 2)
        self.assertEqual(display_badge, "🔥 2 Plays (30D)")
        self.assertIn("in last 30 days", tooltip)
        self.assertIn("24 track plays across 12 tracks", tooltip)

    def test_compute_normalized_album_plays_30d_singular(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(
            track_plays=10, tracks_total=10, is_30d=True
        )
        self.assertEqual(norm_plays, 1)
        self.assertEqual(display_badge, "🔥 1 Play (30D)")
        self.assertIn("in last 30 days", tooltip)

    def test_compute_normalized_album_plays_30d_zero_tracks_fallback(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(
            track_plays=5, tracks_total=0, is_30d=True
        )
        self.assertEqual(norm_plays, 5)
        self.assertEqual(display_badge, "🔥 5 Plays (30D)")
        self.assertIn("30-day track plays: 5", tooltip)

    def test_recommend_template_contains_horizon_controls(self):
        self.assertIn("setHorizon", BETA_RECOMMEND_HTML)
        self.assertIn("horizonBtn-30d", BETA_RECOMMEND_HTML)
        self.assertIn("horizonBtn-all", BETA_RECOMMEND_HTML)
        self.assertIn("selectedHorizon = '30d'", BETA_RECOMMEND_HTML)
        self.assertIn("album_track_plays_30d", BETA_RECOMMEND_HTML)

    def test_explorer_template_contains_30d_sort_option(self):
        self.assertIn('value="plays_30d_desc"', BETA_EXPLORER_HTML)
        self.assertIn("Heavy Rotation (Last 30 Days)", BETA_EXPLORER_HTML)
        self.assertIn('sort === "plays_30d_desc"', BETA_EXPLORER_HTML)

    def test_pals_template_renders_horizon_switcher_and_reasons(self):
        template = jinja2.Template(BETA_PALS_HTML)
        mock_pal = {
            "spotify_id": "pal_dj",
            "display_name": "Vinyl Junkie",
            "avatar_url": "",
            "album_count": 8
        }
        mock_top_borrow = [{
            "album_id": "alb1",
            "album_name": "Selected Ambient Works",
            "album_artist_name": "Aphex Twin",
            "release_year": "1992",
            "album_image_url": "https://example.com/saw.jpg",
            "album_url": "https://open.spotify.com/album/alb1",
            "borrow_reason": "Vinyl Junkie's Current Obsession (3 spins this month) • Pitchfork 10/10",
            "album_tracks_total": 13,
            "album_track_plays": 52,
            "album_plays": 4.0,
            "album_track_plays_30d": 39,
            "album_plays_30d": 3.0,
            "active_track_plays": 39,
            "active_plays_display": "🔥 3 Plays (30D)",
            "active_plays_tooltip": "Estimated complete album spins in last 30 days based on 39 track plays across 13 tracks",
            "current_user_owns": False,
            "has_gatefold": True
        }]

        context = {
            "brand_icon": ICON_A_SVG,
            "gatefold_icon": ICON_GATEFOLD_SVG,
            "user": {"display_name": "Tester", "user_id": "test_user", "avatar_url": "", "pals_opt_in": True},
            "pals": [mock_pal],
            "selected_pal": mock_pal,
            "compatibility": {
                "match_pct": 85,
                "kinship": {
                    "tier": "Vinyl Soulmates",
                    "badge": "🔥 Vinyl Soulmates",
                    "color": "text-rose-400 bg-rose-500/10 border-rose-500/30",
                    "desc": "Uncanny acoustic connection!"
                },
                "artist_score": 85,
                "album_score": 85,
                "shared_artists_count": 4,
                "shared_albums_count": 2,
                "borrow_count": 1,
                "shared_artists": ["Aphex Twin"]
            },
            "top_borrow": mock_top_borrow,
            "shared_albums": [],
            "pal_crate": [],
            "horizon": "30d",
            "is_admin": False,
            "is_impersonating": False
        }

        rendered = template.render(**context)
        self.assertIn("?horizon=30d", rendered)
        self.assertIn("?horizon=all_time", rendered)
        self.assertIn("Current Obsession (3 spins this month)", rendered)
        self.assertIn("🔥 3 Plays (30D)", rendered)
        self.assertIn("Estimated complete album spins in last 30 days based on 39 track plays across 13 tracks", rendered)


if __name__ == "__main__":
    unittest.main()
