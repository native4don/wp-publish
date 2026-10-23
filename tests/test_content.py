"""Turning a Markdown document into a page title and HTML body."""
import pytest

from wp_publish.content import ContentError, find_internal_notes, render

DOC = """# Credits

JoyWeShare is built on **good work** that others have shared.

## The piano

- FluidR3 by Frank Wen
- See [the source](https://example.org/source)

| Software | Licence |
|---|---|
| Vue | MIT |

Permission is hereby granted, free of charge (the "Software").
"""


def test_the_title_is_the_first_heading_and_is_left_out_of_the_body():
    title, html = render(DOC)
    assert title == "Credits"
    assert "<h1>" not in html
    assert ">Credits<" not in html


def test_markdown_becomes_html_with_no_markdown_left():
    _, html = render(DOC)
    assert "<h2>The piano</h2>" in html
    assert "<strong>good work</strong>" in html
    assert "<li>FluidR3 by Frank Wen</li>" in html
    assert '<a href="https://example.org/source">the source</a>' in html
    assert "<table>" in html and "<td>Vue</td>" in html
    assert "(the &quot;Software&quot;)" in html or '(the "Software")' in html
    for leftover in ("**", "## ", "|---|", "](http"):
        assert leftover not in html


def test_a_document_without_a_heading_is_refused():
    with pytest.raises(ContentError):
        render("No heading here.\n")


def test_square_bracket_notes_are_found_with_their_line():
    text = "# Title\n\nFine line.\n\nA line [to confirm later] here.\n"
    assert find_internal_notes(text) == [(5, "A line [to confirm later] here.")]


def test_links_are_not_internal_notes():
    text = "# Title\n\nSee [the source](https://example.org) and [GitHub](https://github.com).\n"
    assert find_internal_notes(text) == []
