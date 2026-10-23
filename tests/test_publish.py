"""Publishing: create or update each page, report what happened, record the ids.

WordPress is simulated with `responses`; no test reaches a real site.
"""
import json
import os
from urllib.parse import parse_qs, urlparse

import pytest
import responses
import yaml

from wp_publish.publish import run

SITE = "https://joyweshare.org"
PAGES = f"{SITE}/wp-json/wp/v2/pages"
SECRET = "abcd efgh ijkl mnop qrst uvwx"


@pytest.fixture
def site(tmp_path):
    """A pages.yml with two pages, their documents, and a credential file."""
    (tmp_path / "credits.md").write_text("# Credits\n\nThanks to all.\n", encoding="utf-8")
    (tmp_path / "credits.fi.md").write_text("# Tekijät\n\nKiitos kaikille.\n", encoding="utf-8")
    (tmp_path / "pages.yml").write_text(
        "pages:\n"
        "  - {file: credits.md, slug: credits, lang: en, key: credits}\n"
        "  - {file: credits.fi.md, slug: tekijat, lang: fi, key: credits}\n",
        encoding="utf-8",
    )
    creds = tmp_path / "wordpress.env"
    creds.write_text(f"WP_URL={SITE}\nWP_USER=don\nWP_APP_PASSWORD={SECRET}\n", encoding="utf-8")
    os.chmod(creds, 0o600)
    return tmp_path


def lookup(slug, found):
    responses.add(
        responses.GET, PAGES, json=found,
        match=[responses.matchers.query_param_matcher({"slug": slug, "status": "any"}, strict_match=False)],
    )


def posts():
    return [c for c in responses.calls if c.request.method == "POST"]


def body(call):
    return json.loads(call.request.body)


def lines(capsys):
    return capsys.readouterr().out.splitlines()


@responses.activate
def test_a_dry_run_sends_nothing(site, capsys):
    lookup("credits", [])
    lookup("tekijat", [{"id": 7, "slug": "tekijat"}])
    run(site / "pages.yml", site / "wordpress.env", publish=False)
    assert posts() == []
    out = "\n".join(lines(capsys))
    assert "would create" in out and "would update" in out
    assert not (site / "published.yml").exists()


@responses.activate
def test_creates_a_new_page_and_updates_an_existing_one_in_place(site):
    lookup("credits", [])
    lookup("tekijat", [{"id": 7, "slug": "tekijat"}])
    responses.add(responses.POST, PAGES, json={"id": 41, "slug": "credits"}, status=201)
    responses.add(responses.POST, f"{PAGES}/7", json={"id": 7, "slug": "tekijat"}, status=200)
    run(site / "pages.yml", site / "wordpress.env", publish=True)
    created, updated = posts()
    assert created.request.url == PAGES
    assert body(created)["slug"] == "credits"
    assert body(created)["title"] == "Credits"
    assert body(created)["status"] == "publish"
    assert "Thanks to all." in body(created)["content"]
    assert updated.request.url == f"{PAGES}/7"
    assert body(updated)["title"] == "Tekijät"


@responses.activate
def test_signs_in_with_the_application_password(site):
    lookup("credits", [])
    lookup("tekijat", [])
    responses.add(responses.POST, PAGES, json={"id": 41}, status=201)
    responses.add(responses.POST, PAGES, json={"id": 42}, status=201)
    run(site / "pages.yml", site / "wordpress.env", publish=True)
    assert all(c.request.headers["Authorization"].startswith("Basic ") for c in responses.calls)


@responses.activate
def test_reports_a_running_count_and_only_what_wordpress_confirmed(site, capsys):
    lookup("credits", [])
    lookup("tekijat", [])
    responses.add(responses.POST, PAGES, json={"id": 41}, status=201)
    responses.add(responses.POST, PAGES, json={"code": "rest_cannot_create"}, status=403)
    run(site / "pages.yml", site / "wordpress.env", publish=True)
    out = lines(capsys)
    first = next(l for l in out if l.startswith("1 of 2"))
    second = next(l for l in out if l.startswith("2 of 2"))
    assert "created" in first and "41" in first
    assert "failed" in second and "403" in second
    assert "created" not in second
    assert not any(SECRET in l for l in out)


@responses.activate
def test_records_page_ids_by_key_and_language_for_successes_only(site):
    lookup("credits", [])
    lookup("tekijat", [])
    responses.add(responses.POST, PAGES, json={"id": 41}, status=201)
    responses.add(responses.POST, PAGES, json={}, status=500)
    run(site / "pages.yml", site / "wordpress.env", publish=True)
    recorded = yaml.safe_load((site / "published.yml").read_text(encoding="utf-8"))
    assert recorded == {"credits": {"en": 41}}


@responses.activate
def test_a_parent_page_is_found_by_its_slug(site):
    (site / "pages.yml").write_text(
        "pages:\n  - {file: credits.md, slug: credits, lang: en, key: credits, parent: about}\n",
        encoding="utf-8",
    )
    lookup("about", [{"id": 3, "slug": "about"}])
    lookup("credits", [])
    responses.add(responses.POST, PAGES, json={"id": 41}, status=201)
    run(site / "pages.yml", site / "wordpress.env", publish=True)
    assert body(posts()[0])["parent"] == 3


@responses.activate
def test_a_missing_parent_stops_that_page_and_says_so(site, capsys):
    (site / "pages.yml").write_text(
        "pages:\n  - {file: credits.md, slug: credits, lang: en, key: credits, parent: about}\n",
        encoding="utf-8",
    )
    lookup("about", [])
    lookup("credits", [])
    run(site / "pages.yml", site / "wordpress.env", publish=True)
    assert posts() == []
    out = "\n".join(lines(capsys))
    assert "about" in out and "failed" in out


@responses.activate
def test_a_document_with_an_internal_note_is_refused(site, capsys):
    (site / "credits.md").write_text("# Credits\n\nThanks [to confirm].\n", encoding="utf-8")
    lookup("credits", [])
    lookup("tekijat", [])
    responses.add(responses.POST, PAGES, json={"id": 42}, status=201)
    run(site / "pages.yml", site / "wordpress.env", publish=True)
    assert [body(c)["slug"] for c in posts()] == ["tekijat"]
    out = "\n".join(lines(capsys))
    assert "[to confirm]" in out and "line 3" in out


@responses.activate
def test_no_request_carries_polylang_language_fields(site):
    lookup("credits", [])
    lookup("tekijat", [])
    responses.add(responses.POST, PAGES, json={"id": 41}, status=201)
    responses.add(responses.POST, PAGES, json={"id": 42}, status=201)
    run(site / "pages.yml", site / "wordpress.env", publish=True)
    for call in responses.calls:
        query = parse_qs(urlparse(call.request.url).query)
        assert "lang" not in query
        assert not any(k.startswith("translations") for k in query)
        if call.request.method == "POST":
            assert "lang" not in body(call) and "translations" not in body(call)
