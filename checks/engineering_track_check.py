from html import unescape
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def cards():
    found = []
    for match in re.finditer(r'<div class="card" data-tracks="([^"]+)"([^>]*)>', HTML):
        title_match = re.search(r"<h3>(.*?)</h3>", HTML[match.end():])
        if not title_match:
            continue
        featured = re.search(r'data-featured-track="([^"]+)"', match.group(2))
        found.append({
            "tracks": match.group(1).split(),
            "featured_track": featured.group(1) if featured else None,
            "title": unescape(title_match.group(1).strip()),
        })
    return found


class EngineeringTrackCheck(unittest.TestCase):
    def test_engineering_query_shows_three_cards_with_txb_featured(self):
        query_track = parse_qs(urlsplit("/?track=engineering").query).get("track", [None])[0]
        self.assertIn('data-track-filter="engineering"', HTML)
        self.assertIn('const queryTrack = url.searchParams.get("track");', HTML)
        self.assertIn('data-feature-panel="engineering"', HTML)
        self.assertIn('const featureTrack = ["ai", "data", "operations", "m-and-a", "private-markets", "transformation", "engineering"].includes(track) ? track : "deal";', HTML)

        matching = [card for card in cards() if query_track in card["tracks"]]
        self.assertEqual(len(matching), 3)
        txb = next(card for card in matching if card["title"] == "Transaction readiness workbench")
        self.assertEqual(txb["featured_track"], "engineering")
        self.assertEqual(
            {card["title"] for card in matching if card["title"] != txb["title"]},
            {
                "Volatility forecasting lab: pre-registered study and data/AI platform",
                "Margin and financing lab",
            },
        )
        panel = re.search(
            r'<div class="feature-panel" data-feature-panel="engineering" hidden>(.*?)</div>\s*</div>\s*</div>',
            HTML,
            re.DOTALL,
        )
        self.assertIsNotNone(panel)
        self.assertIn("<h3>Transaction readiness workbench: does every concurrent update survive?</h3>", panel.group(1))
        self.assertIn('card.hidden = (track !== "all" && !tracks.includes(track)) || card.dataset.featuredTrack === track;', HTML)


if __name__ == "__main__":
    unittest.main()
