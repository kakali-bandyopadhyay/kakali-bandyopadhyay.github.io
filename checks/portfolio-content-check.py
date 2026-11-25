from html import unescape
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
        self.assertIn('const featureTrack = ["ai", "data", "operations", "m-and-a", "private-markets", "transformation", "engineering"].includes(track) ? track : "deal";', HTML)
        self.assertIn('const queryTrack = url.searchParams.get("track");', HTML)

    def test_insurance_card_remains_in_ai_grid(self):
        self.assertIn('<h3>Enterprise AI architecture for a simulated reinsurer</h3>', HTML)
        self.assertIn('data-tracks="ai data"', HTML)

    def test_favicon_tags(self):
        self.assertIn(('icon', '/assets/favicon-32x32.png'), PAGE.icon_tags)
        self.assertIn(('apple-touch-icon', '/assets/apple-touch-icon.png'), PAGE.icon_tags)

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
        self.assertIn('const featureTrack = ["ai", "data", "operations", "m-and-a", "private-markets", "transformation", "engineering"].includes(track) ? track : "deal";', HTML)
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
        cls.prereg = (cls.lab / "prereg" / "PREREGISTRATION_PHASE2B.md").read_text(encoding="utf-8")
        cls.source_documents = {
            "RESULTS.md": cls.results,
            "MODEL_DOC.md": cls.model,
            "SOURCES.md": cls.sources,
            "PREREGISTRATION_PHASE2B.md": cls.prereg,
        }
        cls.source_text = "\n".join(cls.source_documents.values())

    def test_case_sections_and_numbering(self):
        self.assertTrue(self.case_path.is_file())
        headings = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', self.case, re.S)
        expected_ids = ["problem", "approach", "design", "results", "stress", "calibration", "model", "checks", "limits"]
        self.assertEqual([item[0] for item in headings], expected_ids)
        numbered = [re.sub(r"<[^>]+>", "", item[1]).strip() for item in headings[2:]]
        self.assertEqual([re.match(r"^(\d+)\.", text).group(1) for text in numbered], [str(n) for n in range(1, 8)])
        toc = re.search(r'<nav class="toc".*?</nav>', self.case, re.S).group(0)
        toc_items = [(href, re.sub(r"<[^>]+>", "", label).strip()) for href, label in re.findall(r'<a href="([^"]+)">(.*?)</a>', toc, re.S)]
        self.assertEqual(toc_items, [
            ("#problem", "The problem"), ("#approach", "The approach"),
            ("#design", "The question and the design"), ("#results", "Results"),
            ("#stress", "Stress-testing the book"),
            ("#calibration", "Calibrating the rates to public market data"),
            ("#model", "How the model fits together"),
            ("#checks", "How every number is checked"),
            ("#limits", "What it does not claim"),
        ])

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
        result_end = self.case.index('<h2 id="stress">', result_start)
        result_section = self.case[result_start:result_end]
        hero = re.search(r'<p class="cs-lede">(.*?)</p>', self.case, re.S).group(1)
        glance = re.search(r'<dl class="glance".*?</dl>', self.case, re.S).group(0)
        for region in (result_section, hero, glance):
            for number in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?%?", region):
                self.assertIn(number, self.source_text, number)

    def test_stress_and_calibration_number_tokens_have_source_provenance(self):
        number_token = re.compile(r"(?<![\w,])\b\d+(?:,\d{3})*(?:\.\d+)?%?(?![\w,])")
        self.assertEqual(number_token.findall("250,620.19"), ["250,620.19"])
        source_tokens = {
            name: {token.removesuffix("%") for token in number_token.findall(text)}
            for name, text in self.source_documents.items()
        }
        all_source_tokens = set().union(*source_tokens.values())
        for section_id, next_id in (("stress", "calibration"), ("calibration", "model")):
            start = self.case.index(f'<h2 id="{section_id}">')
            end = self.case.index(f'<h2 id="{next_id}">', start)
            section = self.case[start:end]
            visible = unescape(re.sub(r"<[^>]+>", " ", section))
            for number in number_token.findall(visible):
                # Match complete numeric tokens, so 250 cannot match inside 250,620.19.
                self.assertIn(number.removesuffix("%"), all_source_tokens, f"{section_id}: {number}")
            self.assertIn('class="table-scroll"', section)

    def test_stress_rows_and_wording(self):
        section = self.case[self.case.index('<h2 id="stress">'):self.case.index('<h2 id="calibration">')]
        table = re.search(r'<div class="table-scroll".*?</div>', section, re.S).group(0)
        rows = re.findall(r'<tr><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>', table)
        self.assertEqual([row[0] for row in rows], [
            "ST0 base", "ST1a vol ×2", "ST1b vol ×1.5", "ST2a margin rate ×1.5, all PBs",
            "ST2b margin rate ×1.5, PB_D + PB_A", "ST3 PB_D termination", "ST4 combined",
        ])
        self.assertEqual([row[2] for row in rows], ["optimal", "optimal", "optimal", "infeasible", "infeasible", "infeasible", "infeasible"])
        self.assertIn("3 of 5 pre-registered expectations met (E-S1, E-S3, E-S5); E-S2 and E-S4 reported as found.", section)
        self.assertIn("The allocation shown for infeasible cases is the minimum-slack allocation.", section)
        self.assertIn("The additional funding requirement is not a cash amount", section)

    def test_calibration_display_and_expectations(self):
        section = self.case[self.case.index('<h2 id="calibration">'):self.case.index('<h2 id="model">')]
        self.assertIn("7 product types · 5 public series", section)
        self.assertIn("<dt>Backtest:</dt><dd><span class=\"p-num\">every row in the green zone</span>", section)
        self.assertIn("0.662–1.073× exchange initial margin", section)
        self.assertIn("Byte-identical from a clean clone", section)
        self.assertIn("every month-end from January 2019 to September 2026", section)
        self.assertIn("4 of 6 distinct proxy/horizon pairs", section)
        self.assertIn("With 173–175 non-overlapping windows for h = 10, zero exceedances gives Kupiec p ≈ 0.06: at these sample sizes the test has little power to reject a conservative target, and every zone is green.", section)
        target_table = re.search(r'<div class="table-scroll".*?</div>', section, re.S).group(0)
        self.assertEqual(len(re.findall(r'<tr><td>', target_table)), 7)
        self.assertIn("href=\"https://github.com/kakali-bandyopadhyay/margin-and-financing-lab/blob/main/RESULTS.md\">Full calibration results</a>", section)
        expectation_table = re.findall(r'<div class="table-scroll".*?</div>', section, re.S)[1]
        expectation_rows = re.findall(r'<tr><td>(E-C\d)</td><td>(.*?)</td><td>(.*?)</td></tr>', expectation_table)
        self.assertEqual([row[0] for row in expectation_rows], ["E-C1", "E-C2", "E-C3", "E-C4", "E-C5"])
        self.assertEqual(expectation_rows[3][1], "Not met – no PM changes rank")
        self.assertEqual(expectation_rows[3][2], "")

    def test_existing_checks_limits_note_and_prohibited_claims(self):
        checks = self.case[self.case.index('<h2 id="checks">'):self.case.index('<h2 id="limits">')]
        self.assertIn("Exchange sanity band (sanity only – Phase 2b calibration is separate)", checks)
        self.assertIn("Stress tests (Phase 2a)", checks)
        self.assertIn("base case reproduces Phase 1 to the cent; scenario outputs reproduce", checks)
        self.assertIn("C1–C13 (Phase 2b)", checks)
        self.assertIn("ES/VaR rule, overlapping returns, floored target, mapping round-trip, relativities, point-in-time, backtest windows, traffic light, input digest", checks)

        limits = self.case[self.case.index('<h2 id="limits">'):]
        self.assertIn("rates are calibrated to illustrative public-market proxies – not to any broker, exchange or clearing house; proxies are not instrument-matched (index for single names, gold for other commodities, one 10-year duration for all rates products)", limits)
        self.assertIn("stress is static – no margin-call or path dynamics; slack is not a cash amount", limits)
        note = re.search(r'<p class="note">(.*?)</p>', self.case, re.S).group(1)
        self.assertEqual(note, "Synthetic book and broker terms; public market series are used only to calibrate rate levels and as an exchange sanity check. Illustrative model – not validated, not any firm's methodology.")

        visible = unescape(re.sub(r"<[^>]+>", " ", self.case))
        self.assertNotIn("the only public input", visible.lower())
        self.assertNotIn("803", visible)
        for match in re.finditer(r"\bvalidated\b", visible, re.I):
            self.assertTrue(visible[max(0, match.start() - 4):match.start()].lower().endswith("not "), match.group(0))

    def test_hero_pill_chips_and_size_rules(self):
        self.assertIn('<span class="cs-pill">Case study · pre-registered model · synthetic book · public-market calibration · worked example</span>', self.case)
        chip_block = re.search(r'<div class="cs-chips">(.*?)</div>', self.case, re.S).group(1)
        chips = re.findall(r'<span>(.*?)</span>', chip_block)
        self.assertEqual(chips, [
            "Pre-registered", "Margin proxy", "LP (cvxpy + HiGHS)", "DuckDB SQL",
            "Leave-one-out attribution", "Liquidity stress test", "Calibration (ES 97.5%)",
        ])
        css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.cs-hero h1\{[^}]*font-size:28px")
        self.assertRegex(css, r"@media\s*\(max-width:640px\)\{\.cs-hero h1\{[^}]*font-size:23px")
        self.assertRegex(css, r"main\.cs-main\{[^}]*font-size:15px")
        self.assertRegex(css, r"main\.cs-main h2\{[^}]*font-size:19px")
        self.assertIn("font-size:18px", self.case)
        self.assertIn("white-space:nowrap", self.case)
        self.assertIn("overflow-x:auto", self.case)

    def test_favicon_tags_and_repo_links_resolve(self):
        self.assertIn('<link rel="icon" href="/assets/favicon-32x32.png" sizes="32x32">', self.case)
        self.assertIn('<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">', self.case)
        documents = (self.case, HTML)
        for document in documents:
            urls = re.findall(r'https://github\.com/kakali-bandyopadhyay/margin-and-financing-lab/blob/main/([^"?#]+)', document)
            for relative in urls:
                self.assertTrue((self.lab / Path(*relative.split("/"))).is_file(), relative)
            hrefs = re.findall(r'<a\b[^>]*\bhref="([^"]+)"', document)
            self.assertFalse(any("reports/" in href for href in hrefs))

    def test_firm_term_scan_reuses_local_ignored_terms(self):
        terms = [t.strip() for t in (ROOT / "checks" / "scan-terms.local.txt").read_text(encoding="utf-8").splitlines() if t.strip()]
        private_credit = (ROOT / "case-studies" / "private-credit-allocation-engine.html").read_text(encoding="utf-8")
        for document in (self.case, HTML, private_credit):
            for term in terms:
                self.assertNotIn(term, document)

    def test_quant_card_and_feature_panel(self):
        grid_prefix = '<div class="card" data-tracks="quant data engineering" data-featured-track="quant">'
        panel_prefix = '<div class="feature-panel" data-feature-panel="quant" hidden>'
        self.assertEqual(HTML.count(grid_prefix), 1)
        self.assertEqual(HTML.count(panel_prefix), 1)
        card = re.search(re.escape(grid_prefix) + r'(.*?)</div>', HTML, re.S).group(1)
        self.assertIn('<p>Allocates a synthetic multi-PM book across prime brokers at minimum financing and margin cost, then attributes margin to PMs – pre-registered, stress-tested and calibrated to public-market proxies, with a validation-style model document.</p>', card)
        expected_tags = ["Quant research", "Optimisation", "Treasury", "Synthetic data"]
        self.assertEqual(re.findall(r'<span class="tag">(.*?)</span>', card), expected_tags)
        self.assertEqual(re.findall(r'<a\b[^>]*href="([^"]+)"', card), [
            "/case-studies/margin-and-financing-lab.html",
            "https://github.com/kakali-bandyopadhyay/margin-and-financing-lab/blob/main/docs/MODEL_DOC.md",
            "https://github.com/kakali-bandyopadhyay/margin-and-financing-lab/blob/main/RESULTS.md",
            "https://github.com/kakali-bandyopadhyay/margin-and-financing-lab",
        ])
        panel = re.search(re.escape(panel_prefix) + r'(.*?)</div>\s*</div>\s*</div>', HTML, re.S).group(1)
        evidence = re.search(r'<p><strong>Evidence</strong>(.*?)</p>', panel, re.S).group(1)
        self.assertTrue(evidence.endswith(" The margin rates are then calibrated to illustrative public-market proxies (ES 97.5%, point-in-time stressed weighting with a floor) and backtested walk-forward at every month-end from January 2019 to September 2026; every output reproduces byte-identical from a clean clone."))
        self.assertIn('src="assets/img/margin-and-financing-lab-thumb.svg"', panel)
        self.assertTrue((ROOT / "assets" / "img" / "margin-and-financing-lab-thumb.svg").is_file())

    def test_firm_term_scan_reuses_local_ignored_terms(self):
        terms = [t.strip() for t in (ROOT / "checks" / "scan-terms.local.txt").read_text(encoding="utf-8").splitlines() if t.strip()]
        private_credit = (ROOT / "case-studies" / "private-credit-allocation-engine.html").read_text(encoding="utf-8")
        for document in (self.case, HTML, private_credit):
            for term in terms:
                self.assertNotIn(term, document)

    def test_quant_card_and_feature_panel(self):
        self.assertEqual(HTML.count('<div class="card" data-tracks="quant data engineering" data-featured-track="quant">'), 1)
        self.assertEqual(HTML.count('<div class="feature-panel" data-feature-panel="quant" hidden>'), 1)
        card = re.search(r'<div class="card" data-tracks="quant data engineering" data-featured-track="quant">(.*?)</div>', HTML, re.S).group(1)
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
        self.assertIn('<div class="card" data-tracks="data ai quant engineering" data-featured-track="data">', HTML)
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

class PrivateCreditAllocationEngineChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_path = ROOT / "case-studies" / "private-credit-allocation-engine.html"
        cls.page = cls.page_path.read_text(encoding="utf-8")
        cls.source = ROOT.parent / "private-credit-allocation-engine"
        cls.readme = (cls.source / "README.md").read_text(encoding="utf-8")

    def test_page_exists_and_favicon_tags_match_index(self):
        self.assertTrue(self.page_path.is_file())
        index_icons = re.findall(r'<link rel="(?:icon|apple-touch-icon)"[^>]*>', HTML)
        page_icons = re.findall(r'<link rel="(?:icon|apple-touch-icon)"[^>]*>', self.page)
        self.assertEqual(page_icons, index_icons)
        self.assertEqual(page_icons, [
            '<link rel="icon" href="/assets/favicon-32x32.png" sizes="32x32">',
            '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">',
        ])

    def test_stylesheet_version_matches_other_case_studies(self):
        versions = {}
        for page_path in (ROOT / "case-studies").glob("*.html"):
            page = page_path.read_text(encoding="utf-8")
            match = re.search(r'<link rel="stylesheet" href="\.\./assets/style\.css\?v=([^" ]+)">', page)
            if match:
                versions[page_path.name] = match.group(1)
        self.assertIn(self.page_path.name, versions)
        self.assertEqual(versions[self.page_path.name], "20261119p1")
        self.assertEqual(versions["txb-readiness-workbench.html"], "20261125t1")
        self.assertEqual(
            {version for name, version in versions.items() if name != "txb-readiness-workbench.html"},
            {"20261119p1"},
        )

    def test_github_links_exist_in_read_only_source_repo(self):
        hrefs = re.findall(r'<a\b[^>]*\bhref="([^"]+)"', self.page)
        github_hrefs = [href for href in hrefs if urlsplit(href).netloc == "github.com"]
        self.assertTrue(github_hrefs)
        for href in github_hrefs:
            parts = [part for part in urlsplit(href).path.split("/") if part]
            self.assertGreaterEqual(len(parts), 2, href)
            self.assertEqual(parts[:2], ["kakali-bandyopadhyay", "private-credit-allocation-engine"], href)
            relative = parts[4:] if len(parts) >= 4 and parts[2:4] == ["blob", "main"] else []
            target = self.source.joinpath(*relative) if relative else self.source
            self.assertTrue(target.exists(), f"{href} maps to missing {target}")

    def test_no_relative_repo_file_links(self):
        hrefs = re.findall(r'<a\b[^>]*\bhref="([^"]+)"', self.page)
        for href in hrefs:
            parsed = urlsplit(href)
            if parsed.scheme or href.startswith(("/", "#")):
                continue
            self.assertFalse(re.match(r"(?:\.\.?/)?(?:docs|src|tests|data|queries)/", parsed.path), href)

    def test_pill_title_and_hero_buttons(self):
        self.assertIn('<span class="cs-pill">Case study · simulated scenario · synthetic data · worked example</span>', self.page)
        self.assertIn('<h1>Can an allocation engine show an auditor why every fund got what it got?</h1>', self.page)
        actions = re.search(r'<p class="cs-actions">(.*?)</p>', self.page, re.S).group(1)
        buttons = re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', actions, re.S)
        self.assertEqual([(re.sub(r"<[^>]+>", "", text).strip(), href) for href, text in buttons], [
            ("Watch the walkthrough (2 min)", "https://github.com/kakali-bandyopadhyay/private-credit-allocation-engine#walkthrough-2-min-synthetic-data"),
            ("Code", "https://github.com/kakali-bandyopadhyay/private-credit-allocation-engine"),
            ("Findings", "https://github.com/kakali-bandyopadhyay/private-credit-allocation-engine/blob/main/docs/FINDINGS.md"),
            ("Decision trace", "https://github.com/kakali-bandyopadhyay/private-credit-allocation-engine/blob/main/docs/samples/trace_R0008_D008.md"),
        ])

    def test_avoid_terms_absent_and_d008_table_numbers_are_sourced(self):
        for term in ("personal prototype", "personal build", "hobby", "side project", "production-ready", "validated"):
            self.assertNotIn(term, self.page.lower())
        table = re.search(r'<h2 id="decision">.*?</h2>\s*<div class="table-scroll".*?</div>', self.page, re.S).group(0)
        for number in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?%?", table):
            self.assertIn(number, self.readme, f"D008 table number {number} is absent from README.md")

    def test_portfolio_card_has_exactly_case_study_then_code_links(self):
        card = re.search(r'<div class="card" data-tracks="private-markets operations">(.*?)</div>', HTML, re.S).group(1)
        self.assertIn('<h3>Private-credit allocation engine</h3>', card)
        links = re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
        self.assertEqual([(re.sub(r"<[^>]+>", "", text).strip(), href) for href, text in links], [
            ("Case study", "https://kakali-bandyopadhyay.github.io/case-studies/private-credit-allocation-engine.html"),
            ("Code", "https://github.com/kakali-bandyopadhyay/private-credit-allocation-engine"),
        ])

if __name__ == "__main__":
    unittest.main(verbosity=2)
