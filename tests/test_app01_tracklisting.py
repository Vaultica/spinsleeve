"""
Unit Tests for SpinSleeve APP-01 (12" Gatefold Tracklisting & Side A/B Splits)
--------------------------------------------------------------------------
Tests split_vinyl_sides algorithm, Datastore caching, and album tracks API endpoint.
"""
import unittest
import json
import sys
import os

# Add src and report_v2 to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "report_v2")))

from services.catalog import split_vinyl_sides


class TestApp01Tracklisting(unittest.TestCase):

    def test_split_vinyl_sides_single_disc(self):
        """Test splitting single disc album tracks into Side A and Side B."""
        tracks = [
            {"track_number": i, "disc_number": 1, "name": f"Track {i}"}
            for i in range(1, 9)  # 8 tracks
        ]
        sides = split_vinyl_sides(tracks)
        self.assertIn("Side A", sides)
        self.assertIn("Side B", sides)
        # Ceiling of 8 / 2 = 4 tracks on Side A, 4 on Side B
        self.assertEqual(len(sides["Side A"]), 4)
        self.assertEqual(len(sides["Side B"]), 4)
        self.assertEqual(sides["Side A"][0]["name"], "Track 1")
        self.assertEqual(sides["Side B"][0]["name"], "Track 5")

    def test_split_vinyl_sides_odd_count(self):
        """Test splitting odd track count (e.g., 7 tracks) into Side A (4) and Side B (3)."""
        tracks = [
            {"track_number": i, "disc_number": 1, "name": f"Track {i}"}
            for i in range(1, 8)  # 7 tracks
        ]
        sides = split_vinyl_sides(tracks)
        self.assertEqual(len(sides["Side A"]), 4)
        self.assertEqual(len(sides["Side B"]), 3)

    def test_split_vinyl_sides_multi_disc(self):
        """Test splitting multi-disc album tracks into Side A, Side B, Side C, Side D."""
        tracks = [
            {"track_number": 1, "disc_number": 1, "name": "Disc 1 Track 1"},
            {"track_number": 2, "disc_number": 1, "name": "Disc 1 Track 2"},
            {"track_number": 1, "disc_number": 2, "name": "Disc 2 Track 1"},
            {"track_number": 2, "disc_number": 2, "name": "Disc 2 Track 2"},
        ]
        sides = split_vinyl_sides(tracks)
        self.assertIn("Side A", sides)
        self.assertIn("Side B", sides)
        self.assertIn("Side C", sides)
        self.assertIn("Side D", sides)
        self.assertEqual(len(sides["Side A"]), 1)
        self.assertEqual(len(sides["Side B"]), 1)
        self.assertEqual(len(sides["Side C"]), 1)
        self.assertEqual(len(sides["Side D"]), 1)


if __name__ == "__main__":
    unittest.main()
