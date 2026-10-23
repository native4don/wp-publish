"""Reading pages.yml: which file goes to which page."""
from pathlib import Path

import pytest

from wp_publish.config import ConfigError, load_pages


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "pages.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_reads_each_entry_with_files_relative_to_pages_yml(tmp_path):
    path = write(tmp_path, """
pages:
  - file: credits.md
    slug: credits
    lang: en
    key: credits
  - file: credits.fi.md
    slug: tekijat
    lang: fi
    key: credits
    parent: tietoja
""")
    pages = load_pages(path)
    assert [p.slug for p in pages] == ["credits", "tekijat"]
    assert pages[0].file == tmp_path / "credits.md"
    assert pages[0].lang == "en" and pages[0].key == "credits"
    assert pages[0].parent is None
    assert pages[1].parent == "tietoja"


@pytest.mark.parametrize("missing", ["file", "slug", "lang", "key"])
def test_a_missing_field_stops_the_run_naming_the_entry_and_field(tmp_path, missing):
    fields = {"file": "credits.md", "slug": "credits", "lang": "en", "key": "credits"}
    del fields[missing]
    body = "\n".join(f"    {k}: {v}" for k, v in fields.items())
    path = write(tmp_path, "pages:\n  -\n" + body + "\n")
    with pytest.raises(ConfigError) as error:
        load_pages(path)
    assert missing in str(error.value)
    assert "1" in str(error.value)
