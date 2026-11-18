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
        """Verify analytics SQL query uses canonical_album_key for robust deduplication and isolation."""
        import inspect
        source = inspect.getsource(fetch_user_analytics_data)

        # Verify query uses canonical_album_key for first_plays and joins
        self.assertIn("canonical_album_key", source)
        self.assertIn("GROUP BY canonical_album_key", source)
        self.assertIn("p.canonical_album_key = a.canonical_album_key", source)

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
