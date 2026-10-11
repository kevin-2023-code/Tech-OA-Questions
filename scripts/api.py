#!/usr/bin/env python3
"""Read TrueInterview's public catalog API into one JSON-able snapshot.

This module is the ONLY thing in the repository that touches the network, and it
reads exactly one thing: the public, documented, read-only API at ``/api/v1``
(spec: https://trueinterview.io/openapi.json). That API publishes metadata and
never bodies — a title, the companies, the round, the level, a sighting month and
a URL. No statement, solution or test case can reach this repository through it,
which is what keeps the paid catalog paid.

Two rules the rest of the pipeline relies on:

  * **A read that failed is never an empty catalog.** Every failure raises
    :class:`CatalogError`, and the sync then writes nothing. An hourly job that
    rendered zero questions after a network blip would commit an empty repository
    over a good one at an hour nobody is watching.
  * **A field the pages promise must be published.** Every list here is cut by
    level and role, so a catalog that does not publish ``seniority`` / ``roles``
    cannot answer the questions the pages ask. That is a failure too — never a
    quiet re-render with the level columns blank.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://trueinterview.io"

# `/api/v1/*` caps `limit` at 50 (API_MAX_LIMIT in the site's OpenAPI document).
PAGE_LIMIT = 50

# The published quota is 240 requests per 60s. The whole catalog is ~85 pages, so
# a sync fits one window; the pause keeps a catalog five times the size inside it.
REQUEST_PAUSE_SECONDS = 0.25

# A runaway `hasMore` must stop the run rather than page for ever.
MAX_PAGES = 400

RETRIES = 3

USER_AGENT = "trueinterview-oa-list-sync/1 (+https://github.com/kevin-2023-code/Tech-OA-Questions)"

#: Fields every question must carry for the level/role cuts to mean anything.
REQUIRED_QUESTION_FIELDS = ("slug", "title", "type", "companies", "url", "rounds", "roles", "roleTitles", "seniority")


class CatalogError(RuntimeError):
    """The catalog could not be read, or read without a field the pages need."""


def _get(base_url: str, path: str) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    last: Exception | None = None
    for attempt in range(RETRIES):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            last = error
            # 429 and 5xx are worth a second look; a 4xx is our bug and retrying hides it.
            if error.code != 429 and error.code < 500:
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last = error
        else:
            if not isinstance(body, dict) or body.get("ok") is not True or "data" not in body:
                raise CatalogError(f"{path}: unexpected envelope {str(body)[:200]}")
            return body["data"]
        time.sleep(2 ** attempt)
    raise CatalogError(f"{path}: {last}")


def _paged(base_url: str, path: str, key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        data = _get(base_url, f"{path}?limit={PAGE_LIMIT}&page={page}")
        batch = data.get(key)
        meta = data.get("page") or {}
        if not isinstance(batch, list):
            raise CatalogError(f"{path}: page {page} has no `{key}` list")
        if meta.get("totalExact") is False:
            raise CatalogError(f"{path}: the catalog read was cut short (totalExact=false)")
        rows.extend(batch)
        if not meta.get("hasMore"):
            total = meta.get("total")
            if isinstance(total, int) and total != len(rows):
                raise CatalogError(f"{path}: read {len(rows)} rows but the API counts {total}")
            return rows
        time.sleep(REQUEST_PAUSE_SECONDS)
    raise CatalogError(f"{path}: still paging after {MAX_PAGES} pages")


def check_questions(questions: list[dict[str, Any]]) -> None:
    """Refuse a catalog the pages cannot be rendered from honestly."""
    if not questions:
        raise CatalogError("the catalog answered with no questions at all")
    for field in REQUIRED_QUESTION_FIELDS:
        if not any(field in q for q in questions):
            raise CatalogError(
                f"the API does not publish `{field}` on questions. Every list here is cut by "
                "level and role, so rendering without it would blank them; deploy the API "
                "change that publishes it (kevin-2023-code/trueinterview) and re-run."
            )
    seen: set[str] = set()
    for q in questions:
        slug = q.get("slug")
        if not slug or slug in seen:
            raise CatalogError(f"missing or duplicate slug: {slug!r}")
        seen.add(slug)


def fetch_snapshot(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    """Everything the renderers read, as one plain dict (what --snapshot-out writes)."""
    questions = _paged(base_url, "/api/v1/questions", "questions")
    check_questions(questions)
    articles = _paged(base_url, "/api/v1/articles", "articles")
    companies = _get(base_url, f"/api/v1/companies?limit={PAGE_LIMIT}").get("companies")
    if not isinstance(companies, list):
        raise CatalogError("/api/v1/companies: no `companies` list")
    experiences = _get(base_url, f"/api/v1/interview-experiences?limit={PAGE_LIMIT}")
    if not isinstance(experiences.get("experiences"), list):
        raise CatalogError("/api/v1/interview-experiences: no `experiences` list")
    return {
        "questions": questions,
        "articles": articles,
        "companies": companies,
        "experiences": experiences["experiences"],
        "experiencesTotal": experiences.get("total"),
    }
