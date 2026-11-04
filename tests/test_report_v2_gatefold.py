import os
import sys
import unittest
import jinja2

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import BETA_EXPLORER_HTML, BETA_RECOMMEND_HTML, BETA_PALS_HTML, ICON_GATEFOLD_SVG


class TestReportV2Gatefold(unittest.TestCase):

    def setUp(self):
        self.templates = {
            "explorer": BETA_EXPLORER_HTML,
            "recommend": BETA_RECOMMEND_HTML,
            "pals": BETA_PALS_HTML
        }

    def test_templates_jinja_compilation(self):
        for name, html in self.templates.items():
            with self.subTest(template=name):
                # Ensure Jinja2 can compile without errors
                template = jinja2.Template(html)
                self.assertIsNotNone(template)

    def test_mobile_compact_header_elements(self):
        mobile_tokens = [
            'id="modalCoverMobile"',
            'id="modalTitleMobile"',
            'id="modalArtistMobile"',
            'id="modalSpotifyLinkMobile"',
            'id="modalAppleMusicLinkMobile"',
            'class="md:hidden flex items-center'
        ]
        for name, html in self.templates.items():
            with self.subTest(template=name):
                for token in mobile_tokens:
                    self.assertIn(token, html, f"Missing mobile token '{token}' in {name}")

    def test_interactive_audio_scrubber_elements(self):
        scrubber_tokens = [
            'id="gatefoldAudioBar"',
            'id="gatefoldScrubber"',
            'id="gatefoldProgressBar"',
            'id="gatefoldAudioTime"',
            'seekGatefoldAudio',
            'updateModalProgress',
            'resetModalProgress'
        ]
        for name, html in self.templates.items():
            with self.subTest(template=name):
                for token in scrubber_tokens:
                    self.assertIn(token, html, f"Missing scrubber token '{token}' in {name}")

    def test_user_invariants_retained(self):
        invariants = [
            'SpinSleeve Verified',
            'bg-[#1DB954]'
        ]
        for name, html in self.templates.items():
            with self.subTest(template=name):
                for token in invariants:
                    self.assertIn(token, html, f"Missing user invariant '{token}' in {name}")

    def test_archival_deep_links_and_apple_music(self):
        links_tokens = [
            'https://music.apple.com/search?term=',
            'Pitchfork ${album.pitchfork_score}',
            'Discogs ${album.discogs_rating}',
            'Wikipedia',
            'Metacritic ${album.metacritic_score}'
        ]
        for name, html in self.templates.items():
            with self.subTest(template=name):
                for token in links_tokens:
                    self.assertIn(token, html, f"Missing archival/link token '{token}' in {name}")


if __name__ == "__main__":
    unittest.main()
