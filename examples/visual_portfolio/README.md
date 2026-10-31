# Visual portfolio: tests and screenshots for a web page

A single-page portfolio (`index.html`), a spec with four rules (`SPEC.md`), and tests that
check the page's HTML against them (`test_page.py`, standard library only). The page
ships with a real defect: six links are `href="#"` placeholders that go nowhere.

```bash
cp -r examples/visual_portfolio /tmp/portfolio && cd /tmp/portfolio
judge freeze .
judge verify .
```

```
DECISION: FAIL
  1. [fix_code] AssertionError: assert ['#', '#', '#', '#', '#', '#'] == []  (test: test_every_link_has_a_real_target)
```

For a visual review, run `judge improve .`. It saves a screenshot of the page to
`_judge_visual/` (needs `pip install "the-judge-verify[visual]"` and
`playwright install chromium`) and adds a critique of the HTML (viewport,
accessibility, ...).

**Limitation:** a test counts as evidence for PASS only when it exercises a Python module
of the project. This page has no Python, so after you fix the links the verdict is ABSTAIN
(the tests pass but are not counted), not PASS. For a project that can reach PASS, see
[simple_cache](../simple_cache/README.md).
