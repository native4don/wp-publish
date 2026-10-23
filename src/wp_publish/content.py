"""Turning a Markdown document into a page title and an HTML body."""
import re

from markdown_it import MarkdownIt

# A square-bracket note: brackets not followed by "(", so not a link.
NOTE = re.compile(r"\[[^\]\n]+\](?!\()")

_markdown = MarkdownIt("commonmark", {"html": False}).enable("table")


class ContentError(Exception):
    """The document cannot be turned into a page."""


def find_internal_notes(text: str) -> list[tuple[int, str]]:
    """Each line holding a square-bracket note, as (line number, line)."""
    return [
        (number, line)
        for number, line in enumerate(text.splitlines(), start=1)
        if NOTE.search(line)
    ]


def render(text: str) -> tuple[str, str]:
    """The page title (the first "# " heading) and the body as HTML, without that heading."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body = "\n".join(lines[:index] + lines[index + 1:])
            return title, _markdown.render(body)
    raise ContentError("the document has no '# ' heading to use as its title")
