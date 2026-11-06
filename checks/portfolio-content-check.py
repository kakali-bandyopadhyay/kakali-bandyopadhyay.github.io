from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
ALL_SUB = "Applied ML and GenAI for investment and markets users: time-based evaluation, failure analysis, controls built in."
AI_SUB = "Applied ML and GenAI: retrieval, evaluation and controls."
DEAL_TITLE = "Deal intelligence: from screening to an evidence-backed IC memo"
PE_TITLE = "PE value-creation and returns model"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.panels = {}
        self.cards = []
        self.current_panel = None
        self.current_card = None
        self.capture = None
        self.icon_tags = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") in ("icon", "apple-touch-icon"):
            self.icon_tags.append((attrs.get("rel"), attrs.get("href")))
        if attrs.get("data-feature-panel"):
            self.current_panel = attrs["data-feature-panel"]
            self.panels[self.current_panel] = {"title": "", "links": []}
        if self.current_panel and tag == "h3":
            self.capture = ("panel-title", self.current_panel)
        if tag == "div" and "card" in attrs.get("class", "").split() and attrs.get("data-tracks"):
            self.current_card = {"tracks": attrs["data-tracks"].split(), "title": "", "links": []}
            self.cards.append(self.current_card)
        if self.current_panel and tag == "a":
            self.panels[self.current_panel]["links"].append(attrs.get("href"))
        if self.current_card and tag == "a":
            self.current_card["links"].append(attrs.get("href"))
        if self.current_card and tag == "h3":
            self.capture = ("grid-title", self.current_card)

    def handle_endtag(self, tag):
        if tag == "h3":
            self.capture = None
        if tag == "div" and self.current_card:
            self.current_card = None
        if tag == "div" and self.current_panel:
            # The panel closes after its featured card; retain the parsed content.
            self.current_panel = None

    def handle_data(self, data):
        if not self.capture:
            return
        kind, target = self.capture
        if kind == "panel-title":
            self.panels[target]["title"] += data
        else:
            target["title"] += data


PAGE = PageParser()
PAGE.feed(HTML)


class PortfolioContentChecks(unittest.TestCase):
    def test_default_and_track_hero_copy(self):
        self.assertIn(f'<p class="sub" id="hero-sub">{ALL_SUB}</p>', HTML)
        self.assertIn(f'ai: ["{AI_SUB}", "", "Enterprise AI architecture – Portfolio"]', HTML)
        self.assertIn('if (track === "ai") {\n        sub.textContent = copy[0];', HTML)

    def test_featured_titles(self):
        self.assertEqual(PAGE.panels["deal"]["title"], DEAL_TITLE)
        self.assertEqual(PAGE.panels["ai"]["title"], DEAL_TITLE)
        self.assertEqual(PAGE.panels["private-markets"]["title"], PE_TITLE)
        self.assertIn('"private-markets"].includes(track)', HTML)

    def test_insurance_card_remains_in_ai_grid(self):
        self.assertIn('<h3>Enterprise AI architecture for a simulated reinsurer</h3>', HTML)
        self.assertIn('data-tracks="ai data"', HTML)

    def test_favicon_tags(self):
        self.assertIn(('icon', 'assets/favicon-32x32.png'), PAGE.icon_tags)
        self.assertIn(('apple-touch-icon', 'assets/apple-touch-icon.png'), PAGE.icon_tags)

    def test_changed_card_links_preserved_and_repo_file_urls_absolute(self):
        deal_links = [
            "case-studies/deal-intelligence.html",
            "https://kakali-bandyopadhyay.github.io/private-markets-deal-intelligence/",
            "https://github.com/kakali-bandyopadhyay/private-markets-deal-intelligence",
            "assets/deal-intelligence-case-study.pdf",
        ]
        pe_links = [
            "https://github.com/kakali-bandyopadhyay/pe-value-creation-model",
            "https://github.com/kakali-bandyopadhyay/pe-value-creation-model/blob/main/docs/CASE_STUDY.md",
            "assets/pe-value-creation-model-summary.pdf",
        ]
        self.assertEqual(PAGE.panels["deal"]["links"], deal_links)
        self.assertEqual(PAGE.panels["ai"]["links"], deal_links)
        self.assertEqual(PAGE.panels["private-markets"]["links"], pe_links)
        private_deal = next(c for c in PAGE.cards if c["tracks"] == ["private-markets"] and c["title"] == DEAL_TITLE)
        self.assertEqual(private_deal["links"], deal_links)
        for href in deal_links + pe_links:
            if "github.com" in href:
                self.assertTrue(re.match(r"^https://github\.com/kakali-bandyopadhyay/[^/]+(?:/blob/main/.+)?$", href), href)


if __name__ == "__main__":
    unittest.main(verbosity=2)
