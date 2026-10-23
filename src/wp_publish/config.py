"""Reading pages.yml: which document goes to which page."""
from dataclasses import dataclass
from pathlib import Path

import yaml

REQUIRED = ("file", "slug", "lang", "key")


class ConfigError(Exception):
    """pages.yml cannot be used as it stands."""


@dataclass(frozen=True)
class Page:
    file: Path
    slug: str
    lang: str
    key: str
    parent: str | None = None


def load_pages(path: Path) -> list[Page]:
    """The pages listed in pages.yml, with each file relative to pages.yml's folder."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as error:
        raise ConfigError(f"{path}: cannot be read ({error.strerror})") from None
    entries = data.get("pages") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ConfigError(f"{path}: needs a 'pages' list")
    pages = []
    for number, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ConfigError(f"{path}: entry {number} is not a set of fields")
        for field in REQUIRED:
            if not entry.get(field):
                raise ConfigError(f"{path}: entry {number} is missing '{field}'")
        pages.append(Page(
            file=path.parent / str(entry["file"]),
            slug=str(entry["slug"]),
            lang=str(entry["lang"]),
            key=str(entry["key"]),
            parent=str(entry["parent"]) if entry.get("parent") else None,
        ))
    return pages
