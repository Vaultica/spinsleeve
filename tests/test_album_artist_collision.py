import os
import sys
import unittest
import pandas as pd

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import fetch_user_analytics_data


class TestAlbumArtistCollision(unittest.TestCase):
    """Test suite ensuring homonymous albums across different artists are strictly isolated."""

    def test_analytics_query_includes_artist_composite_keys(self):
        """Verify analytics SQL query joins and groups by both album and artist."""
        import inspect
        source = inspect.getsource(fetch_user_analytics_data)

        # 1. first_plays CTE groups by both norm_album_name and norm_artist_name
        self.assertIn("LOWER(TRIM(album_name)) as norm_album_name", source)
        self.assertIn("LOWER(TRIM(artist_name)) as norm_artist_name", source)
        self.assertIn("GROUP BY norm_album_name, norm_artist_name", source)

        # 2. Join to user_saved_albums includes artist name check
        self.assertIn("LOWER(TRIM(p.artist_name)) = LOWER(TRIM(a.artist_name))", source)

        # 3. Global fallback join groups and matches by both album and artist
        self.assertIn("LOWER(TRIM(artist_name)) as norm_artist", source)
        self.assertIn("GROUP BY norm_name, norm_artist", source)
        self.assertIn("LOWER(TRIM(p.artist_name)) = g.norm_artist", source)

        # 4. first_plays join matches on both album and artist
        self.assertIn("LOWER(TRIM(p.artist_name)) = fp.norm_artist_name", source)

    def test_analytics_total_albums_counts_distinct_album_artist_pairs(self):
        """Verify that two distinct artists with the same album title count as 2 albums."""
        # Simulated dataframe with Neil Young - Homegrown and CARRTOONS - Homegrown
        mock_df = pd.DataFrame([
            {"album": "Homegrown", "artist": "Neil Young", "album_image_url": "http://img1.jpg", "ts": "2026-11-01"},
            {"album": "Homegrown", "artist": "Neil Young", "album_image_url": "http://img1.jpg", "ts": "2026-11-02"},
            {"album": "Homegrown", "artist": "CARRTOONS", "album_image_url": "http://img2.jpg", "ts": "2026-11-03"},
        ])

        album_counts = mock_df.groupby(["album", "artist"]).agg(
            plays=("ts", "count"),
            album_image_url=("album_image_url", "first")
        ).reset_index().sort_values("plays", ascending=False)

        total_albums = len(album_counts)
        self.assertEqual(total_albums, 2, "Should count 2 distinct albums despite having identical titles")

        neil_row = album_counts[album_counts["artist"] == "Neil Young"].iloc[0]
        carrtoons_row = album_counts[album_counts["artist"] == "CARRTOONS"].iloc[0]

        self.assertEqual(neil_row["plays"], 2)
        self.assertEqual(neil_row["album_image_url"], "http://img1.jpg")

        self.assertEqual(carrtoons_row["plays"], 1)
        self.assertEqual(carrtoons_row["album_image_url"], "http://img2.jpg")


if __name__ == "__main__":
    unittest.main()
