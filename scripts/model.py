#!/usr/bin/env python3
"""The catalog as records.

This repository carries one cut of the catalog: questions tagged with the online
assessment (``oa``) round, filed by company. Everything here is a pure function
of the snapshot and of ``today``, so a test can render the whole repository from
a fixture and compare bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from labels import COMPANY_LABELS, company_key, company_label

#: The round this repository lists. Rows of the other rounds belong to the
#: sibling repository (Tech-Interview-Questions).
OA_ROUND = "oa"


def parse_sighting(value: str | None) -> tuple[date | None, bool]:
    """``YYYY-MM-DD`` or ``YYYY-MM`` into ``(date, month_only)``.

    A month-only value resolves to the FIRST of the month, so it can only ever
    under-claim recency. Anything unparseable is ``None``: an unreadable date
    is not a date.
    """
    if not value:
        return None, False
    text = value.strip()
    try:
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return date.fromisoformat(text[:10]), False
        if len(text) == 7 and text[4] == "-":
            return date(int(text[:4]), int(text[5:7]), 1), True
    except (ValueError, IndexError):
        pass
    return None, False


#: The site's seniority ladder, lowest first.
LEVELS = ("intern", "new-grad", "junior", "senior", "staff-plus", "manager")
LEVEL_SHORT = {
    "intern": "Intern",
    "new-grad": "New grad",
    # The rung of L4 / E4 / SDE II; the site labels it "Junior / Mid".
    "junior": "Mid",
    "senior": "Senior",
    "staff-plus": "Staff+",
    "manager": "Manager",
}

ROUNDS = ("oa", "phone-screen", "onsite", "take-home")

FORMAT_SHORT = {
    "algorithm": "Coding",
    "system-design": "System design",
    "object-oriented-programming": "OOD / LLD",
    "sql": "SQL",
    "ai-coding": "AI coding",
    "blog": "Behavioral / concept",
}

DIFFICULTY_SHORT = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}

#: Longest platform name kept; anything longer is not a display name.
PLATFORM_MAX = 40


def parse_platform(value: Any) -> str | None:
    """The API's ``oaPlatform``: the assessment platform a report names
    (``HackerRank``, ``CodeSignal``, ...). Tolerant on purpose: the field is
    newer than this repository, so a catalog that does not carry it yet (or
    carries ``null``, or anything that is not a short string) reads as unknown
    and the Platform column stays empty. Never guessed from the company."""
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text if 0 < len(text) <= PLATFORM_MAX else None


@dataclass(frozen=True)
class Question:
    slug: str
    title: str
    url: str
    format: str
    difficulty: str | None
    companies: tuple[str, ...]        # display names, primary first
    company_keys: tuple[str, ...]     # folder names, same order
    rounds: tuple[str, ...]
    levels: tuple[str, ...]
    roles: tuple[str, ...]
    role_titles: tuple[str, ...]
    platform: str | None              # the OA platform a report names, or None
    seen: date | None                 # the most recent report we know of
    seen_month_only: bool

    @property
    def is_oa(self) -> bool:
        return OA_ROUND in self.rounds


@dataclass(frozen=True)
class Catalog:
    questions: tuple[Question, ...]
    labels: dict[str, str]            # company slug -> display name, from the API


def load(snapshot: dict[str, Any]) -> Catalog:
    labels: dict[str, str] = {}
    for row in snapshot.get("companies", []):
        slug, name = row.get("slug"), row.get("name")
        # The API's names are title-cased slugs where the site has no label
        # ("Ebay"); a casing this repository knows better wins.
        if slug and name and slug.lower() not in COMPANY_LABELS:
            labels[slug] = name

    questions = []
    for row in snapshot["questions"]:
        # Two spellings of one employer share a folder; keep the first.
        companies: list[tuple[str, str]] = []
        for raw in row.get("companies") or []:
            if not raw:
                continue
            key = company_key(raw, labels)
            if key and key not in {k for k, _ in companies}:
                companies.append((key, company_label(raw, labels)))
        reported_date, reported_month_only = parse_sighting(row.get("reported"))
        last_date, _ = parse_sighting(row.get("lastReported"))
        seen, month_only = reported_date, reported_month_only
        # A later report outranks the first one; it is month-precision, so it
        # takes over only when it lands in a LATER month than the first report.
        if last_date and (seen is None or last_date > seen.replace(day=1)):
            seen, month_only = last_date, True
        questions.append(
            Question(
                slug=row["slug"],
                title=" ".join(str(row["title"]).split()),
                url=row["url"],
                format=row.get("type") or "",
                difficulty=row.get("difficulty"),
                companies=tuple(name for _, name in companies),
                company_keys=tuple(key for key, _ in companies),
                rounds=tuple(r for r in ROUNDS if r in (row.get("rounds") or [])),
                levels=tuple(level for level in LEVELS if level in (row.get("seniority") or [])),
                roles=tuple(row.get("roles") or []),
                role_titles=tuple(row.get("roleTitles") or []),
                platform=parse_platform(row.get("oaPlatform")),
                seen=seen,
                seen_month_only=month_only,
            )
        )

    return Catalog(questions=tuple(sorted(questions, key=lambda q: q.slug)), labels=labels)


def is_future(q: Question, today: date) -> bool:
    return q.seen is not None and q.seen > today


def newest_first(questions, today: date) -> list[Question]:
    """Total order: dated rows newest first, then future-dated (a typo upstream),
    then undated, so no row can swap places between two runs."""

    def key(q: Question):
        if q.seen is None:
            bucket, ordinal = 2, 0
        elif q.seen > today:
            bucket, ordinal = 1, 0
        else:
            bucket, ordinal = 0, -q.seen.toordinal()
        return (bucket, ordinal, q.seen_month_only, q.title.lower(), q.slug)

    return sorted(questions, key=key)


def last_reported(q: Question, today: date) -> str:
    """The month of the most recent report as ``YYYY-MM``, or ``""``.

    Month precision throughout, because that is what the API publishes for the
    latest report. A date in the future is a typo upstream and is shown as
    unknown rather than repeated.
    """
    if q.seen is None or q.seen > today:
        return ""
    return f"{q.seen.year:04d}-{q.seen.month:02d}"
