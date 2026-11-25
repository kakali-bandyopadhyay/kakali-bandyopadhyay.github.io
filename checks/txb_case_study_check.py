from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
TXB = ROOT.parent / "txb-readiness-workbench"
PAGE_PATH = ROOT / "case-studies" / "txb-readiness-workbench.html"
PAGE = PAGE_PATH.read_text(encoding="utf-8")
FINDINGS = (TXB / "FINDINGS.md").read_text(encoding="utf-8")


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
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<div class="card" data-tracks="operations">(.*?)</div>', index, re.S)
    assert match is not None
    card = match.group(1)
    assert "Lost-update race fixed to 0 lost; JFR-led fix 38.6 → 399.4 req/s (synthetic, single workstation)." in card
    links = re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
    assert re.sub(r"<[^>]+>", "", links[0][1]).strip() == "Case study"
    assert links[0][0] == "case-studies/txb-readiness-workbench.html"
    assert (ROOT / links[0][0]).is_file()


def test_phase_two_section_is_no_longer_duplicated():
    case_study = (TXB / "docs" / "CASE_STUDY.md").read_text(encoding="utf-8")
    assert case_study.count("## Phase 2") == 1
