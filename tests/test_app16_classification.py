"""
Unit tests for APP-16 semantic liner-note & metadata classification.
"""

import os
import sys
import unittest

# Add src/pipeline_v2 to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "pipeline_v2")))

import classifier


class TestAPP16Classification(unittest.TestCase):

    def test_classify_macro_genre(self):
        self.assertEqual(classifier.classify_macro_genre("electronic, ambient", "", ""), "Ambient")
        self.assertEqual(classifier.classify_macro_genre("heavy metal, thrash", "", ""), "Metal")
        self.assertEqual(classifier.classify_macro_genre("hip hop, rap", "", ""), "Hip-Hop")
        self.assertEqual(classifier.classify_macro_genre("modal jazz, bebop", "", ""), "Jazz")
        self.assertEqual(classifier.classify_macro_genre("synthpop, techno", "House", ""), "Electronic")
        self.assertEqual(classifier.classify_macro_genre("post-punk", "Indie Rock", ""), "Punk / Alternative")
        self.assertEqual(classifier.classify_macro_genre("neo-soul, funk", "", ""), "R&B / Soul")
        self.assertEqual(classifier.classify_macro_genre("chamber music, symphony", "", ""), "Classical")
        self.assertEqual(classifier.classify_macro_genre("bluegrass, folk", "", ""), "Folk / Country")
        self.assertEqual(classifier.classify_macro_genre("roots reggae, dub", "", ""), "Reggae / Dub")
        self.assertEqual(classifier.classify_macro_genre("chicago blues", "", ""), "Blues")
        self.assertEqual(classifier.classify_macro_genre("psychedelic rock, indie rock", "", ""), "Rock")
        self.assertEqual(classifier.classify_macro_genre("dance-pop, electropop", "", ""), "Pop")
        self.assertEqual(classifier.classify_macro_genre("afrobeat, bossa nova", "", ""), "Latin / World")
        self.assertEqual(classifier.classify_macro_genre("", "", ""), "Eclectic / Other")

    def test_extract_derived_moods(self):
        summary = "A dark late night nocturnal album recorded at 3am with moody, smoky atmospheres."
        moods = classifier.extract_derived_moods(summary=summary)
        self.assertIn("Late Night", moods)

        calm_summary = "A soothing, serene, and peaceful collection of acoustic pieces to unwind."
        moods_calm = classifier.extract_derived_moods(summary=calm_summary)
        self.assertIn("Chill", moods_calm)

        psychedelic_summary = "A trippy and psychedelic journey filled with surreal and mind-bending sounds."
        moods_psych = classifier.extract_derived_moods(summary=psychedelic_summary)
        self.assertIn("Psychedelic", moods_psych)

        empty_moods = classifier.extract_derived_moods()
        self.assertEqual(empty_moods, ["Chill"])

    def test_extract_descriptive_tags(self):
        summary = "An ambitious concept album featuring moog modular synthesizers and orchestral string quartet arrangements."
        tags = classifier.extract_descriptive_tags(summary=summary)
        self.assertIn("Synthesizers", tags)
        self.assertIn("Concept Album", tags)
        self.assertIn("Orchestral Strings", tags)

    def test_compute_enrichment_quality_score(self):
        # All present: 0.35 + 0.25 + 0.25 + 0.15 = 1.00
        score_full = classifier.compute_enrichment_quality_score(True, True, True, True)
        self.assertEqual(score_full, 1.0)

        # Only summary: 0.35
        score_sum = classifier.compute_enrichment_quality_score(True, False, False, False)
        self.assertEqual(score_sum, 0.35)

        # None present: 0.0
        score_empty = classifier.compute_enrichment_quality_score(False, False, False, False)
        self.assertEqual(score_empty, 0.0)

    def test_classify_album_metadata(self):
        record = {
            "genres": "art rock, experimental rock",
            "discogs_styles": "Alternative Rock",
            "album_description": "OK Computer is the third studio album by English rock band Radiohead, exploring dystopian late night themes.",
            "pitchfork_score": "10/10",
            "personnel": "Nigel Godrich (Producer)",
            "discogs_rating": 4.85
        }
        res = classifier.classify_album_metadata(record)
        self.assertEqual(res["macro_genre"], "Rock")
        self.assertIn("Late Night", res["derived_moods"])
        self.assertEqual(res["enrichment_quality_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
