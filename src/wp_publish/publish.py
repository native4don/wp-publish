"""Publishing: create or update each page, report what happened, record the ids.

Only WordPress's own REST API is used (wp/v2/pages). Pages are found by slug,
so an existing page is updated in place and keeps its address.
"""
from pathlib import Path

import requests
import yaml

from .config import Page, load_pages
from .content import ContentError, find_internal_notes, render
from .credentials import load_credentials

TIMEOUT = 30


class PageFailed(Exception):
    """This page was not published; the message says why."""


def run(pages_yml: Path, credentials: Path, publish: bool = False) -> int:
    """Publish (or, without publish=True, only report) every page in pages.yml.

    Returns 0 when every page went through, 1 otherwise.
    """
    pages_yml = Path(pages_yml)
    pages = load_pages(pages_yml)
    creds = load_credentials(credentials)
    session = requests.Session()
    session.auth = (creds.user, creds.password)
    api = f"{creds.url}/wp-json/wp/v2/pages"

    print(("Publishing" if publish else "Dry run: nothing is sent") + f" to {creds.url}")
    published: dict[str, dict[str, int]] = {}
    failures = 0
    total = len(pages)
    for number, page in enumerate(pages, start=1):
        prefix = f"{number} of {total} {page.slug} ({page.lang}):"
        try:
            outcome = _one(session, api, page, publish)
        except PageFailed as error:
            failures += 1
            print(f"{prefix} failed: {error}")
            continue
        action, page_id = outcome
        print(f"{prefix} {action}" + (f" page {page_id}" if page_id else ""))
        if publish and page_id:
            published.setdefault(page.key, {})[page.lang] = page_id

    if publish and published:
        _record(pages_yml.parent / "published.yml", published)
    return 1 if failures else 0


def _one(session: requests.Session, api: str, page: Page, publish: bool) -> tuple[str, int | None]:
    try:
        text = page.file.read_text(encoding="utf-8")
    except OSError as error:
        raise PageFailed(f"cannot read {page.file} ({error.strerror})") from None
    notes = find_internal_notes(text)
    if notes:
        line, content = notes[0]
        raise PageFailed(f"internal note on line {line}: {content}")
    try:
        title, html = render(text)
    except ContentError as error:
        raise PageFailed(str(error)) from None

    fields: dict = {"title": title, "content": html}
    if page.parent:
        parent = _find(session, api, page.parent)
        if parent is None:
            raise PageFailed(f"parent page '{page.parent}' not found")
        fields["parent"] = parent

    existing = _find(session, api, page.slug)
    if not publish:
        return ("would update" if existing else "would create"), existing

    if existing:
        response = _send(session, f"{api}/{existing}", fields)
        return "updated", _confirmed_id(response)
    fields.update(slug=page.slug, status="publish")
    response = _send(session, api, fields)
    return "created", _confirmed_id(response)


def _find(session: requests.Session, api: str, slug: str) -> int | None:
    """The id of the page with this slug, in any status, or None."""
    try:
        response = session.get(api, params={"slug": slug, "status": "any"}, timeout=TIMEOUT)
    except requests.RequestException as error:
        raise PageFailed(f"could not reach the site ({type(error).__name__})") from None
    if response.status_code != 200:
        raise PageFailed(f"looking up '{slug}' answered {response.status_code}")
    found = response.json()
    if not isinstance(found, list):
        raise PageFailed(f"looking up '{slug}' gave an unexpected answer")
    return found[0]["id"] if found else None


def _send(session: requests.Session, url: str, fields: dict) -> requests.Response:
    try:
        return session.post(url, json=fields, timeout=TIMEOUT)
    except requests.RequestException as error:
        raise PageFailed(f"could not reach the site ({type(error).__name__})") from None


def _confirmed_id(response: requests.Response) -> int:
    """The page id WordPress answered with; anything else is a failure."""
    try:
        data = response.json()
    except ValueError:
        data = {}
    page_id = data.get("id") if isinstance(data, dict) else None
    if response.status_code not in (200, 201) or not isinstance(page_id, int):
        code = data.get("code") if isinstance(data, dict) else None
        raise PageFailed(f"WordPress answered {response.status_code}" + (f" ({code})" if code else ""))
    return page_id


def _record(path: Path, published: dict[str, dict[str, int]]) -> None:
    """Merge the published page ids into published.yml, by key and language."""
    recorded = {}
    if path.exists():
        recorded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key, ids in published.items():
        recorded.setdefault(key, {}).update(ids)
    path.write_text(yaml.safe_dump(recorded, sort_keys=True, allow_unicode=True), encoding="utf-8")
