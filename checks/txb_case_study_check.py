from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
TXB = ROOT.parent / "txb-readiness-workbench"
PAGE_PATH = ROOT / "case-studies" / "txb-readiness-workbench.html"
PAGE = PAGE_PATH.read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
FINDINGS = (TXB / "FINDINGS.md").read_text(encoding="utf-8")


def _featured_txb_markup():
    panel = re.search(
        r'<div class="feature-panel" data-feature-panel="engineering" hidden>(.*?)</div>\s*</div>\s*</div>',
        INDEX,
        re.S,
    )
    assert panel is not None, "engineering feature panel is missing"
    return panel.group(1)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.links = []
        self.images = []
        self.stylesheets = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "img" and attrs.get("src"):
            self.images.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.stylesheets.append(attrs.get("href", ""))

    def handle_data(self, data):
        self.text_parts.append(data)


def _page_parser():
    parser = PageParser()
    parser.feed(PAGE)
    return parser


def test_case_study_favicons_stylesheet_and_diagrams_exist():
    assert '<link rel="icon" href="/assets/favicon-32x32.png" sizes="32x32">' in PAGE
    assert '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">' in PAGE
    assert '<link rel="stylesheet" href="../assets/style.css?v=20261125t1">' in PAGE
    for name in ("txb-optimistic-lock.svg", "txb-loadtest-setup.svg"):
        asset = ROOT / "assets" / "img" / name
        assert asset.is_file() and asset.stat().st_size > 0
        assert f'../assets/img/{name}' in PAGE


def test_local_links_and_assets_resolve_without_404s():
    parser = _page_parser()
    assert PAGE_PATH.is_file()
    for href in parser.links:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc:
            continue
        if href.startswith("#"):
            assert href[1:] in parser.ids, href
            continue
        if not parsed.path:
            continue
        target = (PAGE_PATH.parent / parsed.path).resolve()
        if target.is_dir():
            target = target / "index.html"
        assert target.is_file(), href
    for src in parser.images:
        assert (PAGE_PATH.parent / urlsplit(src).path).resolve().is_file(), src
    for href in parser.stylesheets:
        assert (PAGE_PATH.parent / urlsplit(href).path).resolve().is_file(), href
    assert (ROOT / "assets" / "favicon-32x32.png").is_file()
    assert (ROOT / "assets" / "apple-touch-icon.png").is_file()


def test_github_links_are_absolute_and_map_to_existing_txb_paths():
    parser = _page_parser()
    github_links = [href for href in parser.links if "github.com" in href]
    assert github_links
    for href in github_links:
        parsed = urlsplit(href)
        assert parsed.scheme == "https" and parsed.netloc == "github.com", href
        parts = [part for part in parsed.path.split("/") if part]
        assert parts[:2] == ["kakali-bandyopadhyay", "txb-readiness-workbench"], href
        if len(parts) >= 4 and parts[2:4] == ["blob", "main"]:
            target = TXB.joinpath(*parts[4:])
            assert target.is_file(), href
        else:
            assert TXB.is_dir(), href


def test_every_visible_number_appears_in_findings():
    visible_text = " ".join(_page_parser().text_parts)
    numbers = re.findall(r"(?<![A-Za-z])\d+(?:,\d{3})*(?:\.\d+)*%?", visible_text)
    missing = sorted({number for number in numbers if number not in FINDINGS})
    assert not missing, f"page numbers absent from FINDINGS.md: {missing}"


def test_banned_terms_are_absent_from_case_study():
    lower = PAGE.lower()
    banned = ("production", "bank-scale", "personal", "hobby", "side project", "self-directed", "hand-coded")
    for term in banned:
        assert not re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", lower), term


def test_portfolio_card_links_to_case_study_first():
    card = _featured_txb_markup()
    assert '<div class="card" data-tracks="operations engineering" data-featured-track="engineering">' in INDEX
    assert '<div class="card feature feature-build">' in card
    assert '<img src="assets/img/txb-loadtest-setup.svg"' in card
    assert "<h3>Transaction readiness workbench: does every concurrent update survive?</h3>" in card
    assert "Fifty requests updating the same record at once silently lost 45 of 50 changes – and the service handled under 40 requests a second for a reason that wasn't the database." in card
    assert "A Java 25 / Spring Boot 4.1.2 service on PostgreSQL." in card
    assert "optimistic locking (@Version, bounded back-off, HTTP 409) and pessimistic locking (SELECT … FOR UPDATE) are compared" in card
    assert "5 of 50 updates survived before the fix; 0 lost after." in card
    assert "JFR traced 99.5% of CPU samples to password hashing" in card
    assert "38.6 → 399.4 req/s and cut p95 1,545 → 264.8 ms (median of 3 runs)." in card
    assert "Virtual threads added no throughput – the 10-connection pool was the limit. 71 tests in CI. Synthetic data, single workstation." in card
    assert all(f'<span class="tag">{tag}</span>' in card for tag in ("Backend engineering", "Java", "Concurrency"))
    links = re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
    assert [(re.sub(r"<[^>]+>", "", label).strip(), href) for href, label in links] == [
        ("Case study", "case-studies/txb-readiness-workbench.html"),
        ("Code", "https://github.com/kakali-bandyopadhyay/txb-readiness-workbench"),
        ("Findings", "https://github.com/kakali-bandyopadhyay/txb-readiness-workbench/blob/main/FINDINGS.md"),
        ("ADR-001", "https://github.com/kakali-bandyopadhyay/txb-readiness-workbench/blob/main/docs/adr/ADR-001-readiness-action-locking.md"),
    ]
    assert (ROOT / links[0][0]).is_file()


def test_every_number_in_featured_txb_card_appears_verbatim_in_findings():
    card = _featured_txb_markup()
    numbers = re.findall(r"(?<![A-Za-z])\d+(?:,\d{3})*(?:\.\d+)*%?", card)
    missing = sorted({number for number in numbers if number not in FINDINGS})
    assert not missing, f"featured card numbers absent from FINDINGS.md: {missing}"


def test_featured_txb_card_avoids_banned_words():
    card = _featured_txb_markup().lower()
    for term in ("personal", "laptop", "hand-coded", "self-directed"):
        assert not re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", card), term


def test_phase_two_section_is_no_longer_duplicated():
    case_study = (TXB / "docs" / "CASE_STUDY.md").read_text(encoding="utf-8")
    assert case_study.count("## Phase 2") == 1
