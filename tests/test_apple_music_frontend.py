"""
Unit test suite for Apple MusicKit JS v3 Frontend Client & Onboarding UI (APP-02b).
Verifies:
1. Route scoping & isolation: /beta injects is_beta=True and renders Apple Music connection points;
   default root route (/) strictly preserves the Spotify-only experience with zero Apple Music UI.
2. Mock Apple Music collection generation (get_mock_apple_music_albums) with rich metadata.
3. Backend mock sync execution via POST /beta/api/apple-music/sync (mock_mode=True).
4. Catalog presentation layer platform preservation ('apple_music' vs 'spotify') and deep link formatting.
5. Invalidation of Datastore caches and table isolation with QA suffixes.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pipeline_v2.apple_music import (
    get_mock_apple_music_albums,
    sync_apple_music_saved_albums,
    parse_apple_music_library
)
from report_v2.app import app
from report_v2.services.catalog import fetch_user_album_data


class TestAppleMusicFrontendAndMockSync(unittest.TestCase):

    def test_get_mock_apple_music_albums(self):
        """Verifies the mock Apple Music catalog generates valid, realistic album objects."""
        mock_albums = get_mock_apple_music_albums()
        self.assertGreaterEqual(len(mock_albums), 5)
        for item in mock_albums:
            self.assertTrue(item["id"].startswith("am_mock_"))
            self.assertEqual(item["type"], "library-albums")
            attrs = item["attributes"]
            self.assertIn("name", attrs)
            self.assertIn("artistName", attrs)
            self.assertIn("artwork", attrs)
            self.assertIn("url", attrs["artwork"])

        df = parse_apple_music_library(mock_albums, user_id="test_user")
        self.assertEqual(len(df), len(mock_albums))
        self.assertTrue((df["platform"] == "apple_music").all())
        self.assertTrue((df["user_id"] == "test_user").all())

    @patch("pipeline_v2.apple_music.invalidate_user_datastore_caches")
    @patch("pipeline_v2.apple_music.bigquery.Client")
    def test_mock_sync_execution(self, mock_bq_cls, mock_invalidate):
        """Verifies sync_apple_music_saved_albums executes smoothly with mock_mode=True."""
        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq

        # Mock existing albums check to return empty DataFrame (all mock albums are new)
        mock_query_job = MagicMock()
        mock_query_job.to_dataframe.return_value = MagicMock(empty=True)
        mock_bq.query.return_value = mock_query_job

        # Mock load job
        mock_load_job = MagicMock()
        mock_load_job.result.return_value = None
        mock_bq.load_table_from_dataframe.return_value = mock_load_job

        result = sync_apple_music_saved_albums(
            user_id="test_mock_user",
            music_user_token="mock_apple_music_token",
            bq_client=mock_bq,
            table_suffix="_app_02b",
            mock_mode=True
        )

        self.assertEqual(result["status"], "success")
        self.assertGreater(result["new_albums"], 0)
        self.assertEqual(result["total_synced"], result["new_albums"])

        # Verifies BigQuery load called
        self.assertTrue(mock_bq.load_table_from_dataframe.called)
        # Verifies Datastore cache invalidation was triggered
        self.assertTrue(mock_invalidate.called)

    def test_route_scoping_beta_vs_default_root(self):
        """
        Verifies /beta renders Apple Music onboarding UI elements,
        while the default / route strictly preserves the Spotify-only experience.
        """
        app.config["TESTING"] = True
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "user_beta_tester"
                sess["display_name"] = "Beta Tester"

            # Mock catalog data to return a sample album
            sample_catalog = {
                "albums": [
                    {
                        "album_id": "alb_spot_1",
                        "album_name": "In Rainbows",
                        "album_artist_name": "Radiohead",
                        "album_image_url": "https://example.com/art.jpg",
                        "release_year": "2007",
                        "added_at": "2024-01-01",
                        "album_genres": "Alternative",
                        "album_track_plays": 10,
                        "album_plays": 1.0,
                        "album_track_plays_30d": 5,
                        "album_plays_30d": 0.5,
                        "album_tracks_total": 10,
                        "album_description": "",
                        "personnel": [],
                        "pitchfork_score": "",
                        "discogs_rating": 0.0,
                        "enriched_styles": "",
                        "macro_genre": "Alternative",
                        "derived_moods": [],
                        "descriptive_tags": [],
                        "enrichment_quality_score": 0.0,
                        "album_url": "https://open.spotify.com/album/alb_spot_1",
                        "platform": "spotify",
                        "has_gatefold": False,
                        "total_plays": 10,
                        "play_count_30d": 5
                    },
                    {
                        "album_id": "am_1440857781",
                        "album_name": "OK Computer",
                        "album_artist_name": "Radiohead",
                        "album_image_url": "https://example.com/art2.jpg",
                        "release_year": "1997",
                        "added_at": "2024-01-02",
                        "album_genres": "Rock",
                        "album_track_plays": 0,
                        "album_plays": 0.0,
                        "album_track_plays_30d": 0,
                        "album_plays_30d": 0.0,
                        "album_tracks_total": 12,
                        "album_description": "",
                        "personnel": [],
                        "pitchfork_score": "",
                        "discogs_rating": 0.0,
                        "enriched_styles": "",
                        "macro_genre": "Rock",
                        "derived_moods": [],
                        "descriptive_tags": [],
                        "enrichment_quality_score": 0.0,
                        "album_url": "https://music.apple.com/album/1440857781",
                        "platform": "apple_music",
                        "has_gatefold": False,
                        "total_plays": 0,
                        "play_count_30d": 0
                    },
                    {
                        "album_id": "am_mock_1440879161",
                        "album_name": "Discovery Mock",
                        "album_artist_name": "Daft Punk",
                        "album_image_url": "https://example.com/art3.jpg",
                        "release_year": "2001",
                        "added_at": "2024-01-03",
                        "album_genres": "Electronic",
                        "album_track_plays": 0,
                        "album_plays": 0.0,
                        "album_track_plays_30d": 0,
                        "album_plays_30d": 0.0,
                        "album_tracks_total": 14,
                        "album_description": "",
                        "personnel": [],
                        "pitchfork_score": "",
                        "discogs_rating": 0.0,
                        "enriched_styles": "",
                        "macro_genre": "Electronic",
                        "derived_moods": [],
                        "descriptive_tags": [],
                        "enrichment_quality_score": 0.0,
                        "album_url": "https://music.apple.com/album/1440879161",
                        "platform": "apple_music",
                        "is_mock": True,
                        "has_gatefold": False,
                        "total_plays": 0,
                        "play_count_30d": 0
                    }
                ],
                "top_genres": ["Alternative", "Rock"],
                "kpis": {}
            }

            with patch("services.catalog.fetch_user_album_data", return_value=sample_catalog), \
                 patch("services.catalog.fetch_unowned_album_data", return_value=[]):

                # 1. Accessing /beta route: is_beta is True
                res_beta = client.get("/beta")
                self.assertEqual(res_beta.status_code, 200)
                html_beta = res_beta.get_data(as_text=True)

                self.assertIn("musickit/v3/musickit.js", html_beta)
                self.assertIn("Connect Apple Music", html_beta)
                self.assertIn("appleMusicModal", html_beta)
                self.assertIn("appleMusicSyncToast", html_beta)
                self.assertIn("OK Computer", html_beta)
                # Mock albums are purged from /beta view as well
                self.assertNotIn("Discovery Mock", html_beta)

                # 2. Accessing default root / route: is_beta is False
                res_root = client.get("/")
                self.assertEqual(res_root.status_code, 200)
                html_root = res_root.get_data(as_text=True)

                self.assertNotIn("musickit/v3/musickit.js", html_root)
                self.assertNotIn("Connect Apple Music", html_root)
                self.assertNotIn("appleMusicModal", html_root)
                self.assertNotIn("appleMusicSyncToast", html_root)
                # Apple Music albums and mock albums are filtered out on default root route
                self.assertNotIn("OK Computer", html_root)
                self.assertNotIn("Discovery Mock", html_root)
                self.assertIn("In Rainbows", html_root)

    @patch("services.catalog.get_catalog_from_datastore")
    def test_mock_albums_filtered_from_catalog_cache(self, mock_get_ds):
        """Verifies fetch_user_album_data actively purges mock albums from Datastore cache."""
        from services.catalog import fetch_user_album_data, _user_album_cache
        _user_album_cache.clear()

        cached_payload = {
            "albums": [
                {
                    "album_id": "spot_1",
                    "album_name": "In Rainbows",
                    "artist_name": "Radiohead",
                    "added_at": "2024-01-01",
                    "macro_genre": "Alternative",
                    "total_plays": 10,
                    "play_count_30d": 5
                },
                {
                    "album_id": "am_mock_1440857781",
                    "album_name": "OK Computer",
                    "artist_name": "Radiohead",
                    "added_at": "2026-11-22",
                    "macro_genre": "Rock",
                    "total_plays": 0,
                    "play_count_30d": 0,
                    "is_mock": True
                }
            ],
            "top_genres": ["Alternative", "Rock"],
            "kpis": {"total_albums": 2}
        }
        mock_get_ds.return_value = cached_payload

        res = fetch_user_album_data("test_user_purge")
        album_ids = [a["album_id"] for a in res["albums"]]
        self.assertIn("spot_1", album_ids)
        self.assertNotIn("am_mock_1440857781", album_ids)
        self.assertEqual(len(res["albums"]), 1)

    @patch("routes.apple_music.sync_apple_music_library")
    def test_route_mock_sync_post(self, mock_sync):
        """Verifies POST /beta/api/apple-music/sync with mock_mode=True routes to service with mock_mode."""
        mock_sync.return_value = {
            "status": "success",
            "new_albums": 7,
            "total_synced": 7
        }

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "user_am_mock_test"

            res = client.post(
                "/beta/api/apple-music/sync",
                json={"mock_mode": True}
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["new_albums"], 7)

            mock_sync.assert_called_once_with(
                user_id="user_am_mock_test",
                music_user_token="mock_apple_music_token",
                table_suffix="",
                mock_mode=True
            )


if __name__ == "__main__":
    unittest.main()
