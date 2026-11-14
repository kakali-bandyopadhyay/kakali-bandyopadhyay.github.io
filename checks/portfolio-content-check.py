from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
ALL_SUB = "Applied ML and GenAI for investment and markets users: time-based evaluation, failure analysis, controls built in."
AI_SUB = "Applied ML and GenAI: retrieval, evaluation and controls."
DEAL_TITLE = "Deal intelligence: from screening to an evidence-backed IC memo"
LIFE_AI_TITLE = "Life and protection AI: which use cases go forward, under what controls"
AI_PAGE_TITLE = "Kakali Bandyopadhyay · Applied AI: use-case assessment, evaluation and controls"
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
            self.current_card = {
                "tracks": attrs["data-tracks"].split(),
                "featured_track": attrs.get("data-featured-track"),
                "title": "",
                "links": [],
            }
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
        self.assertIn(f'ai: ["{AI_SUB}", "", "{AI_PAGE_TITLE}"]', HTML)
        self.assertIn('if (track === "ai") {\n        sub.textContent = copy[0];', HTML)
        self.assertIn('document.title = copy[2];', HTML)

    def test_featured_titles(self):
        self.assertEqual(PAGE.panels["deal"]["title"], DEAL_TITLE)
        self.assertEqual(PAGE.panels["ai"]["title"], LIFE_AI_TITLE)
        self.assertEqual(PAGE.panels["private-markets"]["title"], PE_TITLE)
        self.assertIn('const featureTrack = ["ai", "data", "operations", "m-and-a", "private-markets", "transformation"].includes(track) ? track : "deal";', HTML)
        self.assertIn('const queryTrack = url.searchParams.get("track");', HTML)

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
        ai_feature_links = [
            "https://kakali-bandyopadhyay.github.io/life-ai-value-chain/case-study/",
            "https://kakali-bandyopadhyay.github.io/life-ai-value-chain/",
            "https://github.com/kakali-bandyopadhyay/life-ai-value-chain",
        ]
        life_ai_links = [
            "https://kakali-bandyopadhyay.github.io/life-ai-value-chain/case-study/",
            "https://kakali-bandyopadhyay.github.io/life-ai-value-chain/",
            "https://github.com/kakali-bandyopadhyay/life-ai-value-chain",
        ]
        pe_links = [
            "https://github.com/kakali-bandyopadhyay/pe-value-creation-model",
            "https://github.com/kakali-bandyopadhyay/pe-value-creation-model/blob/main/docs/CASE_STUDY.md",
            "assets/pe-value-creation-model-summary.pdf",
        ]
        self.assertEqual(PAGE.panels["deal"]["links"], deal_links)
        self.assertEqual(PAGE.panels["ai"]["links"], ai_feature_links)
        self.assertEqual(PAGE.panels["private-markets"]["links"], pe_links)
        private_deal = next(c for c in PAGE.cards if c["tracks"] == ["private-markets"] and c["title"] == DEAL_TITLE)
        self.assertEqual(private_deal["links"], deal_links)
        life_ai = next(c for c in PAGE.cards if c["title"] == LIFE_AI_TITLE)
        self.assertEqual(life_ai["links"], life_ai_links)
        self.assertEqual(life_ai["featured_track"], "ai")
        self.assertIn('card.hidden = (track !== "all" && !tracks.includes(track)) || card.dataset.featuredTrack === track;', HTML)
        self.assertEqual(sum(panel["title"] == LIFE_AI_TITLE for panel in PAGE.panels.values()), 1)
        for href in deal_links + ai_feature_links + life_ai_links + pe_links:
            if "github.com" in href:
                self.assertTrue(re.match(r"^https://github\.com/kakali-bandyopadhyay/[^/]+(?:/blob/main/.+)?$", href), href)



    def test_transformation_track_card_panel_short_link_and_case_study(self):
        canonical = "https://kakali-bandyopadhyay.github.io/?track=transformation"
        self.assertIn('data-track-filter="operations" aria-pressed="false">Operations</button>\n  <button type="button" class="filter-chip" data-track-filter="transformation" aria-pressed="false">Transformation</button>', HTML)
        self.assertIn('transformation: ["Enterprise transformation and delivery", "Portfolio, capacity, vendor and commercial decisions, with every figure traced to its source.", "Transformation and delivery builds – Portfolio"]', HTML)
        self.assertIn('<div class="feature-panel" data-feature-panel="transformation" hidden>', HTML)
        self.assertIn('const featureTrack = ["ai", "data", "operations", "m-and-a", "private-markets", "transformation"].includes(track) ? track : "deal";', HTML)
        grid = next(c for c in PAGE.cards if c["title"] == "Enterprise transformation delivery review")
        self.assertEqual(grid["tracks"], ["transformation", "operations"])
        self.assertEqual(grid["featured_track"], "transformation")
        expected_links = [
            "case-studies/transformation-delivery-review.html",
            "assets/transformation-delivery-review.pdf",
            "https://github.com/kakali-bandyopadhyay/transformation-delivery-review/raw/main/out/delivery_review_model.xlsx",
            "https://github.com/kakali-bandyopadhyay/transformation-delivery-review",
            "https://github.com/kakali-bandyopadhyay/transformation-delivery-review/blob/main/FINDINGS.md",
        ]
        self.assertEqual(grid["links"], expected_links)
        self.assertEqual(PAGE.panels["transformation"]["links"], expected_links)

        short_path = ROOT / "transformation" / "index.html"
        self.assertTrue(short_path.is_file())
        short = short_path.read_text(encoding="utf-8")
        meta = re.search(r'<meta http-equiv="refresh" content="0; url=([^"]+)">', short)
        script = re.search(r'window\.location\.replace\("([^"]+)"\)', short)
        fallback = re.search(r'<a href="([^"]+)">Continue to Transformation and delivery builds</a>', short)
        self.assertIsNotNone(meta)
        self.assertIsNotNone(script)
        self.assertIsNotNone(fallback)
        self.assertEqual([meta.group(1), script.group(1), fallback.group(1)], [canonical] * 3)

        case_path = ROOT / "case-studies" / "transformation-delivery-review.html"
        self.assertTrue(case_path.is_file())
        case = case_path.read_text(encoding="utf-8")
        self.assertIn("<h1>Enterprise transformation delivery review</h1>", case)
        self.assertIn("<p class=\"sub\">Delivery case study – personal prototype</p>", case)
        self.assertIn("Simulated data – not observed results. The firm, people and vendors are generic and unnamed. Decisions D1–D5 are the decisions the pack forces, presented as such; figures marked forecast are projections.", case)
        self.assertIn('href="../?track=transformation"', case)
        for img in ["tdr-e12-roadmap.png", "tdr-e31-capacity.png", "tdr-decision-log.png"]:
            self.assertIn(img, case)

        class HrefParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.hrefs = []
            def handle_starttag(self, tag, attrs):
                if tag == "a":
                    href = dict(attrs).get("href")
                    if href:
                        self.hrefs.append(href)

        def assert_relative_links_resolve(test, hrefs, source_file):
            for href in hrefs:
                if urlsplit(href).scheme or href.startswith("#"):
                    continue
                target = urlsplit(href).path
                resolved = (source_file.parent / target).resolve()
                if not target or resolved.is_dir():
                    resolved = resolved / "index.html"
                test.assertTrue(resolved.is_file(), f"{href} from {source_file.relative_to(ROOT)}")

        assert_relative_links_resolve(self, grid["links"], ROOT / "index.html")
        anchors = HrefParser()
        anchors.feed(case)
        assert_relative_links_resolve(self, anchors.hrefs, case_path)

if __name__ == "__main__":
    unittest.main(verbosity=2)
