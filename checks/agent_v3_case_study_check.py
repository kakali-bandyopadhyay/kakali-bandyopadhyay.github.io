from html.parser import HTMLParser
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "case-studies" / "vol-forecast-lab.html"
FINDINGS = ROOT.parent / "vol-forecast-lab" / "FINDINGS.md"
EXPECTED_TITLE = "Agents: LangGraph supervisor (v2) and Claude Agent SDK port (v3)"
FINDINGS_URL = (
    "https://github.com/kakali-bandyopadhyay/vol-forecast-lab/blob/main/FINDINGS.md"
)


class AgentSectionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_section = False
        self.done = False
        self.text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h2" and attrs.get("id") == "agents":
            self.in_section = True
        elif tag == "h2" and self.in_section:
            self.in_section = False
            self.done = True
        if self.in_section and tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_data(self, data):
        if self.in_section:
            self.text.append(data)


def main():
    page = PAGE.read_text(encoding="utf-8")
    findings = FINDINGS.read_text(encoding="utf-8")
    parser = AgentSectionParser()
    parser.feed(page)
    visible = " ".join(parser.text)
    assert EXPECTED_TITLE in visible
    assert FINDINGS_URL + "#agent-v3-claude-agent-sdk-port-lean-nov-2026" in parser.links
    numbers = re.findall(r"(?<![A-Za-z])\d+(?:,\d{3})*(?:\.\d+)*%?", visible)
    missing = sorted({number for number in numbers if number not in findings})
    assert not missing, f"case-study numbers absent from FINDINGS.md: {missing}"
    print(f"Agent case-study check passed: {len(numbers)} number occurrences checked.")


if __name__ == "__main__":
    main()
