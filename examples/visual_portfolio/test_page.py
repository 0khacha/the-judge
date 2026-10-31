"""Tests for index.html, written from SPEC.md. Standard library only."""

from html.parser import HTMLParser
from pathlib import Path

PAGE = Path(__file__).with_name("index.html")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def all(self, tag):
        return [attrs for t, attrs in self.tags if t == tag]


def parse() -> Page:
    page = Page()
    page.feed(PAGE.read_text(encoding="utf-8"))
    return page


def test_language_charset_and_viewport():  # R1
    page = parse()
    assert page.all("html")[0].get("lang")
    metas = page.all("meta")
    assert any(m.get("charset", "").lower() == "utf-8" for m in metas)
    assert any(m.get("name") == "viewport" and "width=device-width" in m.get("content", "")
               for m in metas)


def test_title_single_h1_and_nav():  # R2
    page = parse()
    assert len(page.all("title")) == 1
    assert len(page.all("h1")) == 1
    assert len(page.all("nav")) >= 1


def test_every_link_has_a_real_target():  # R3
    page = parse()
    ids = {attrs["id"] for _, attrs in page.tags if "id" in attrs}
    broken = []
    for link in page.all("a"):
        href = link.get("href", "")
        if href.startswith("#"):
            if href[1:] not in ids:  # also catches a bare "#"
                broken.append(href)
        elif not href.startswith(("mailto:", "https://", "http://")):
            broken.append(href)
    assert broken == []


def test_navigation_sections_exist():  # R4
    page = parse()
    ids = {attrs["id"] for _, attrs in page.tags if "id" in attrs}
    assert {"about", "projects", "contact"} <= ids
