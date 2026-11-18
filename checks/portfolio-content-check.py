from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
ALL_SUB = "Applied ML and GenAI for investment and markets users: time-based evaluation, failure analysis, controls built in."
AI_SUB = "Applied ML and GenAI"
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
        self.assertIn('data: ["Data platforms and governance", "Event-driven pipelines, entity mastering, lineage and AI-ready warehouses.", "Data platforms and governance – Portfolio"],', HTML)
        self.assertIn('quant: ["Quant research and treasury models", "Pre-registered studies, margin and financing optimisation, forecasting.", "Quant research and treasury models – Portfolio"],', HTML)
        self.assertIn(f'ai: ["{AI_SUB}", "Forecasting, retrieval, evaluation and controls.", "{AI_PAGE_TITLE}"],', HTML)
        self.assertNotIn('if (track === "ai") {', HTML)
        self.assertIn('strong.textContent = copy[0] + ". ";', HTML)
        self.assertIn('sub.append(strong, copy[1]);', HTML)
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
        self.assertEqual(grid["links"], [expected_links[0], expected_links[1], expected_links[3]])
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
        self.assertIn("<h1>Enterprise transformation: what to fund, fix and stop when demand outruns capacity</h1>", case)
        self.assertIn("simulated scenario · synthetic data", case)
        self.assertNotIn("prototype", case)
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


class MarginFinancingLabChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_path = ROOT / "case-studies" / "margin-and-financing-lab.html"
        cls.case = cls.case_path.read_text(encoding="utf-8")
        cls.lab = ROOT.parent / "margin-and-financing-lab"
        cls.results = (cls.lab / "RESULTS.md").read_text(encoding="utf-8")
        cls.model = (cls.lab / "docs" / "MODEL_DOC.md").read_text(encoding="utf-8")
        cls.sources = (cls.lab / "data" / "SOURCES.md").read_text(encoding="utf-8")
        cls.source_text = "\n".join((cls.results, cls.model, cls.sources))

    def test_case_sections_and_numbering(self):
        self.assertTrue(self.case_path.is_file())
        headings = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', self.case, re.S)
        self.assertEqual([item[0] for item in headings], ["problem", "approach", "design", "results", "model", "checks", "limits"])
        self.assertEqual([re.sub(r"<[^>]+>", "", item[1]).split(". ", 1)[0] for item in headings[2:]], ["1", "2", "3", "4", "5"])

    def test_case_favicons_and_versioned_stylesheet(self):
        self.assertEqual(self.case.count('<link rel="icon" href="/assets/favicon-32x32.png" sizes="32x32">'), 1)
        self.assertEqual(self.case.count('<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">'), 1)
        self.assertRegex(self.case, r'<link rel="stylesheet" href="\.\./assets/style\.css\?v=[^" ]+">')

    def test_repo_links_resolve_and_no_reports_links(self):
        self.assertTrue(self.lab.is_dir(), f"Missing source repository: {self.lab}")
        documents = (self.case, HTML)
        for document in documents:
            urls = re.findall(r'https://github\.com/kakali-bandyopadhyay/margin-and-financing-lab/blob/main/([^"?#]+)', document)
            for relative in urls:
                self.assertTrue((self.lab / Path(*relative.split("/"))).is_file(), relative)
            hrefs = re.findall(r'<a\b[^>]*\bhref="([^"]+)"', document)
            self.assertFalse(any("reports/" in href for href in hrefs))
            for href in hrefs:
                if urlsplit(href).scheme or href.startswith(("/", "#")):
                    continue
                self.assertFalse(re.match(r"(?:\.\.?/)?(?:docs|src|tests|prereg|data)/", href), href)

    def test_diagram_image_viewbox_and_dimensions(self):
        image = ROOT / "assets" / "img" / "margin-and-financing-lab-flow.svg"
        self.assertTrue(image.is_file())
        svg = image.read_text(encoding="utf-8")
        viewbox = re.search(r'viewBox="([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)"', svg)
        self.assertIsNotNone(viewbox)
        _, _, width, height = map(float, viewbox.groups())
        img = re.search(r'<img[^>]*src="\.\./assets/img/margin-and-financing-lab-flow\.svg"[^>]*>', self.case)
        self.assertIsNotNone(img)
        attrs = dict(re.findall(r'(width|height)="([^"]+)"', img.group(0)))
        self.assertEqual(attrs, {"width": str(round(width)), "height": str(round(height))})
        self.assertLessEqual(width, 800)
        self.assertGreaterEqual(height / width, 0.6)
        self.assertLessEqual(height / width, 1.6)

    def test_result_hero_and_glance_numbers_have_provenance(self):
        result_start = self.case.index('<h2 id="results">')
        result_end = self.case.index('<h2 id="model">', result_start)
        result_section = self.case[result_start:result_end]
        hero = re.search(r'<p class="cs-lede">(.*?)</p>', self.case, re.S).group(1)
        glance = re.search(r'<dl class="glance".*?</dl>', self.case, re.S).group(0)
        for region in (result_section, hero, glance):
            for number in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?%?", region):
                self.assertIn(number, self.source_text, number)

    def test_firm_term_scan_reuses_local_ignored_terms(self):
        terms = [t.strip() for t in (ROOT / "checks" / "scan-terms.local.txt").read_text(encoding="utf-8").splitlines() if t.strip()]
        for document in (self.case, HTML):
            for term in terms:
                self.assertNotIn(term, document)

    def test_quant_card_and_feature_panel(self):
        self.assertEqual(HTML.count('<div class="card" data-tracks="quant data" data-featured-track="quant">'), 1)
        self.assertEqual(HTML.count('<div class="feature-panel" data-feature-panel="quant" hidden>'), 1)
        card = re.search(r'<div class="card" data-tracks="quant data" data-featured-track="quant">(.*?)</div>', HTML, re.S).group(1)
        expected_tags = ["Quant research", "Optimisation", "Treasury", "Synthetic data"]
        self.assertEqual(re.findall(r'<span class="tag">(.*?)</span>', card), expected_tags)
        self.assertIn('src="assets/img/margin-and-financing-lab-thumb.svg"', HTML)
        self.assertTrue((ROOT / "assets" / "img" / "margin-and-financing-lab-thumb.svg").is_file())
        self.assertEqual(PAGE.cards[[c["title"] for c in PAGE.cards].index("Margin and financing lab")]["links"], [
            "/case-studies/margin-and-financing-lab.html",
            "https://github.com/kakali-bandyopadhyay/margin-and-financing-lab/blob/main/docs/MODEL_DOC.md",
            "https://github.com/kakali-bandyopadhyay/margin-and-financing-lab/blob/main/RESULTS.md",
            "https://github.com/kakali-bandyopadhyay/margin-and-financing-lab",
        ])

    def test_quant_track_filter_and_short_link(self):
        self.assertIn('quant: ["Quant research and treasury models", "Pre-registered studies, margin and financing optimisation, forecasting.", "Quant research and treasury models – Portfolio"],', HTML)
        self.assertEqual(HTML.count('data-track-filter="quant" aria-pressed="false">Quant</button>'), 1)
        self.assertIn('data-track-filter="data" aria-pressed="false">Data</button>\n  <button type="button" class="filter-chip" data-track-filter="quant" aria-pressed="false">Quant</button>', HTML)
        short = (ROOT / "quant" / "index.html").read_text(encoding="utf-8")
        self.assertIn('content="0; url=https://kakali-bandyopadhyay.github.io/?track=quant"', short)
        self.assertIn('window.location.replace("https://kakali-bandyopadhyay.github.io/?track=quant")', short)
        self.assertIn('<link rel="icon" href="/assets/favicon-32x32.png" sizes="32x32">', short)
        self.assertIn('<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">', short)

    def test_volatility_card_moves_to_quant_without_changing_data_panel(self):
        self.assertIn('<div class="card" data-tracks="data ai quant" data-featured-track="data">', HTML)
        self.assertIn('<div class="feature-panel" data-feature-panel="data" hidden>', HTML)
        self.assertIn('src="assets/img/vol-forecast-lab-thumb.svg"', HTML)
        self.assertIn('<h3>Volatility forecasting lab: pre-registered study and data/AI platform</h3>', HTML)

    def test_tsmom_card_copy_tags_and_links(self):
        self.assertEqual(HTML.count('<div class="card" data-tracks="quant">'), 1)
        card = re.search(r'<div class="card" data-tracks="quant">(.*?)</div>', HTML, re.S).group(1)
        copy = "A pre-registered test (OSF) of time-series momentum across 18 cross-asset ETFs, 2011–2026. Effective breadth was measured before the run (B = 4.04), then the result reported against a size-corrected test: Sharpe +0.526, 95% interval [0.038, 1.054]."
        self.assertIn(f"<p>{copy}</p>", card)
        self.assertEqual(re.findall(r'<span class="tag">(.*?)</span>', card), ["Quant research", "Pre-registered (OSF)", "Python", "Market data"])
        self.assertEqual(re.findall(r'<a href="([^"]+)">', card), [
            "https://github.com/kakali-bandyopadhyay/tsmom-panel-study/blob/main/RESULTS.md",
            "https://doi.org/10.17605/OSF.IO/W86XT",
            "https://github.com/kakali-bandyopadhyay/tsmom-panel-study",
        ])


class VolForecastLabEventDrivenChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_path = ROOT / "case-studies" / "vol-forecast-lab.html"
        cls.case = cls.case_path.read_text(encoding="utf-8")
        cls.event_start = cls.case.index('<h2 id="event-driven">')
        cls.checks_start = cls.case.index('<h2 id="checks">')
        cls.section = cls.case[cls.event_start:cls.checks_start]

    def test_section_position_and_headings(self):
        self.assertEqual(self.case.count('id="event-driven"'), 1)
        self.assertLess(self.case.index('id="platform"'), self.event_start)
        self.assertLess(self.event_start, self.checks_start)
        headings = re.findall(r'<h2\b[^>]*>(.*?)</h2>', self.case, re.S)
        headings = [re.sub(r"<[^>]+>", "", heading).strip() for heading in headings]
        self.assertIn("4. Event-driven ingestion", headings)
        self.assertIn("5. How every number is checked", headings)
        self.assertIn("6. What it does not claim", headings)

    def test_toc_order_and_anchor_count(self):
        toc = re.search(r'<nav class="toc".*?</nav>', self.case, re.S).group(0)
        labels = re.findall(r'<a\b[^>]*>(.*?)</a>', toc, re.S)
        self.assertIn(["The platform", "Event-driven ingestion", "How numbers are checked"], [labels[i:i + 3] for i in range(len(labels) - 2)])
        self.assertEqual(self.case.count('href="#event-driven"'), 2)

    def test_hero_chip_follows_aws_lake_once(self):
        chip = "<span>SQS&nbsp;·&nbsp;Lambda&nbsp;·&nbsp;DynamoDB</span>"
        self.assertEqual(self.case.count(chip), 1)
        self.assertIn("<span>AWS lake</span>" + chip, self.case)

    def test_index_chips_appear_twice(self):
        chip = '<span class="tag">SQS&nbsp;·&nbsp;Lambda&nbsp;·&nbsp;DynamoDB</span>'
        self.assertEqual(HTML.count(chip), 2)

    def test_diagram_file_dimensions_and_target(self):
        image = re.search(r'<img\b[^>]*>', self.section).group(0)
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', image))
        diagram = (self.case_path.parent / attrs["src"]).resolve()
        self.assertTrue(diagram.is_file())
        svg = diagram.read_text(encoding="utf-8")
        viewbox = re.search(r'viewBox="([^"]+)"', svg)
        self.assertIsNotNone(viewbox)
        x, y, width, height = map(float, viewbox.group(1).split())
        self.assertEqual(int(attrs["width"]), round(width))
        self.assertEqual(int(attrs["height"]), round(height))
        self.assertLessEqual(width, 800)
        self.assertGreaterEqual(height / width, 0.6)
        self.assertLessEqual(height / width, 1.6)

    def test_root_absolute_favicons_remain(self):
        self.assertIn('<link rel="icon" href="/assets/favicon-32x32.png" sizes="32x32">', self.case)
        self.assertIn('<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">', self.case)

    def test_repo_blob_links_resolve(self):
        lab = ROOT.parent / "vol-forecast-lab"
        self.assertTrue(lab.is_dir())
        urls = re.findall(r'https://github\.com/kakali-bandyopadhyay/vol-forecast-lab/blob/main/([^"?#]+)', self.case)
        self.assertTrue(urls)
        for relative in urls:
            self.assertTrue((lab / Path(*relative.split("/"))).is_file(), relative)

    def test_relative_links_do_not_point_into_repo_code(self):
        class LinkParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.hrefs = []

            def handle_starttag(self, tag, attrs):
                if tag == "a":
                    href = dict(attrs).get("href")
                    if href:
                        self.hrefs.append(href)

        parser = LinkParser()
        parser.feed(self.case)
        for href in parser.hrefs:
            if urlsplit(href).scheme or href.startswith("#"):
                continue
            self.assertTrue(
                href.startswith(("../assets/", "/assets/", "/vol-forecast-lab/dashboard/", "/?track=")),
                href,
            )

    def test_phase_table_and_latency(self):
        table = re.search(r'<table>.*?</table>', self.section, re.S).group(0)
        rows = re.findall(r'<tr>(.*?)</tr>', table, re.S)
        body_rows = rows[1:]
        first_cells = [re.search(r'<td>(.*?)</td>', row, re.S).group(1) for row in body_rows]
        self.assertEqual(first_cells, ["R2", "R3", "R4", "R5", "R6"])
        self.assertIn("p50 11 s", self.case)
        self.assertIn("p95 17 s", self.case)

    def test_firm_term_scan(self):
        index = HTML
        terms = [t.strip() for t in (ROOT / "checks" / "scan-terms.local.txt").read_text(encoding="utf-8").splitlines() if t.strip()]
        for document in (self.case, index):
            for term in terms:
                self.assertNotIn(term, document)

    def test_exactly_once_wording_is_absent(self):
        self.assertNotIn("exactly-once", self.case.lower())

if __name__ == "__main__":
    unittest.main(verbosity=2)
