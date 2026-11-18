import os
import sys
import unittest

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pipeline_v2.sync import compute_canonical_album_key


class TestCanonicalDedup(unittest.TestCase):
    """Test suite for canonical sibling album normalization and deduplication."""

    def test_compute_canonical_album_key_standardizes_variants(self):
        """Verify that Deluxe, Remastered, and Standard editions map to the exact same canonical key."""
        artist = "Marika Hackman"
        
        standard = compute_canonical_album_key(artist, "I'm Not Your Man")
        deluxe = compute_canonical_album_key(artist, "I'm Not Your Man (Deluxe)")
        remastered = compute_canonical_album_key(artist, "I'm Not Your Man [Remastered Edition]")
        
        expected = "marika hackman::i'm not your man"
        
        self.assertEqual(standard, expected)
        self.assertEqual(deluxe, expected)
        self.assertEqual(remastered, expected)

    def test_compute_canonical_album_key_different_albums(self):
        """Verify that truly different albums produce distinct canonical keys."""
        artist = "Radiohead"
        
        kid_a = compute_canonical_album_key(artist, "Kid A")
        ok_computer = compute_canonical_album_key(artist, "OK Computer")
        
        self.assertNotEqual(kid_a, ok_computer)
        self.assertEqual(kid_a, "radiohead::kid a")
        self.assertEqual(ok_computer, "radiohead::ok computer")


if __name__ == "__main__":
    unittest.main()
