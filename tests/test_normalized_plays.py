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


class TestNormalizedAlbumPlays(unittest.TestCase):

    def test_standard_multi_spin(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(track_plays=24, tracks_total=12)
        self.assertEqual(norm_plays, 2)
        self.assertEqual(display_badge, "🔥 2 Plays")
        self.assertEqual(
            tooltip,
            "Estimated complete album spins based on 24 track plays across 12 tracks"
        )

    def test_singular_spin(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(track_plays=10, tracks_total=10)
        self.assertEqual(norm_plays, 1)
        self.assertEqual(display_badge, "🔥 1 Play")
        self.assertEqual(
            tooltip,
            "Estimated complete album spins based on 10 track plays across 10 tracks"
        )

    def test_partial_spin_less_than_one_album(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(track_plays=7, tracks_total=12)
        self.assertEqual(norm_plays, 0.6)
        self.assertEqual(display_badge, "🔥 0.6 Plays")
        self.assertEqual(
            tooltip,
            "Estimated complete album spins based on 7 track plays across 12 tracks"
        )

    def test_zero_track_plays(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(track_plays=0, tracks_total=10)
        self.assertEqual(norm_plays, 0.0)
        self.assertEqual(display_badge, "💤 Never Played")
        self.assertEqual(
            tooltip,
            "Never played (0 plays)"
        )

    def test_fallback_zero_tracks_total(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(track_plays=5, tracks_total=0)
        self.assertEqual(norm_plays, 5.0)
        self.assertEqual(display_badge, "🔥 5 Plays")
        self.assertEqual(tooltip, "Total track plays: 5 (track count unavailable)")

    def test_fallback_singular_track_total_zero(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(track_plays=1, tracks_total=0)
        self.assertEqual(norm_plays, 1.0)
        self.assertEqual(display_badge, "🔥 1 Play")
        self.assertEqual(tooltip, "Total track plays: 1 (track count unavailable)")

    def test_none_and_nan_resilience(self):
        norm_plays, display_badge, tooltip = compute_normalized_album_plays(track_plays=None, tracks_total=None)
        self.assertEqual(norm_plays, 0.0)
        self.assertEqual(display_badge, "💤 Never Played")
        self.assertEqual(tooltip, "Never played (0 plays)")

    def test_explorer_template_script_tokens(self):
        self.assertIn("function getAlbumPlayBadge(a)", BETA_EXPLORER_HTML)
        self.assertIn("Estimated complete album spins based on", BETA_EXPLORER_HTML)
        self.assertIn("${getAlbumPlayBadge(a)}", BETA_EXPLORER_HTML)

    def test_recommend_template_script_tokens(self):
        self.assertIn("function getAlbumPlayBadge(a)", BETA_RECOMMEND_HTML)
        self.assertIn("Estimated complete album spins based on", BETA_RECOMMEND_HTML)
        self.assertIn("${getAlbumPlayBadge(a)}", BETA_RECOMMEND_HTML)

    def test_pals_template_rendered_badges(self):
        template = jinja2.Template(BETA_PALS_HTML)
        mock_pal = {
            "spotify_id": "pal1",
            "display_name": "Acoustic Buddy",
            "avatar_url": "",
            "album_count": 5
        }
        mock_top_borrow = [{
            "album_id": "borrow1",
            "album_name": "OK Computer",
            "album_artist_name": "Radiohead",
            "release_year": "1997",
            "album_image_url": "https://example.com/cover.jpg",
            "album_url": "https://open.spotify.com/album/borrow1",
            "borrow_reason": "Heavy Rotation (4 spins)",
            "album_tracks_total": 12,
            "album_track_plays": 48,
            "album_normalized_plays": 4,
            "album_plays_display": "🔥 4 Plays",
            "album_plays_tooltip": "Estimated complete album spins based on 48 track plays across 12 tracks",
            "has_gatefold": True
        }]
        mock_pal_crate = [{
            "album_id": "crate1",
            "album_name": "In Rainbows",
            "album_artist_name": "Radiohead",
            "release_year": "2007",
            "album_image_url": "https://example.com/ir.jpg",
            "album_url": "https://open.spotify.com/album/crate1",
            "album_tracks_total": 10,
            "album_track_plays": 10,
            "album_normalized_plays": 1,
            "album_plays_display": "🔥 1 Play",
            "album_plays_tooltip": "Estimated complete album spins based on 10 track plays across 10 tracks",
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
                "match_pct": 90,
                "kinship": {
                    "tier": "Vinyl Soulmates",
                    "badge": "✨ Vinyl Soulmates",
                    "color": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
                    "desc": "Acoustic twins"
                },
                "artist_score": 90,
                "album_score": 90,
                "shared_artists_count": 5,
                "shared_albums_count": 3,
                "borrow_count": 1,
                "shared_artists": ["Radiohead"]
            },
            "top_borrow": mock_top_borrow,
            "shared_albums": [],
            "pal_crate": mock_pal_crate,
            "is_admin": False,
            "is_impersonating": False
        }

        rendered = template.render(**context)
        self.assertIn("🔥 4 Plays", rendered)
        self.assertIn("Estimated complete album spins based on 48 track plays across 12 tracks", rendered)
        self.assertIn("🔥 1 Play", rendered)
        self.assertIn("Estimated complete album spins based on 10 track plays across 10 tracks", rendered)


if __name__ == "__main__":
    unittest.main()
