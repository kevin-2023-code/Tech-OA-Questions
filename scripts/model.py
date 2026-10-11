#!/usr/bin/env python3
"""The catalog as records, and the two axes every page here is cut by.

This repository answers one question before any other: *is this list for me?*
Its readers are experienced engineers and researchers, so the bank is cut two
ways, and both are defined here and nowhere else:

  * **Where you are interviewing** — a :class:`Group` of employers: AI labs,
    quant firms, MAANG+. Membership comes from the shared company registry (the
    same sector table the sister repositories file employers under), never from
    a company's name.
  * **Who you are** — a :class:`Track`: Senior & Staff+, ML & research, quant.
    Membership comes from the facets the catalog publishes on each question
    (``seniority``, ``roleTitles``, ``roles``). A question with no level on
    record is in no level track: unclassified is not "every level".

Everything is a pure function of the snapshot and of ``today``, so a test can
render the whole repository from a fixture and compare bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

from labels import COMPANY_LABELS, company_key, company_label
from segments import segment_of

# ── Freshness ────────────────────────────────────────────────────────────────

HOT_DAYS = 14   # 🔥
NEW_DAYS = 45   # 🆕
RECENT_DAYS = 90

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def parse_sighting(value: str | None) -> tuple[date | None, bool]:
    """``YYYY-MM-DD`` or ``YYYY-MM`` into ``(date, month_only)``.

    A month-only value resolves to the FIRST of the month: it can only ever
    under-claim freshness, never put a 🔥 on a question nobody said was seen this
    fortnight. Anything unparseable is ``None`` — an unreadable date is not a date.
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


# ── Levels, rounds, formats ──────────────────────────────────────────────────

#: The site's seniority ladder (problems/services/seniority.ts), lowest first.
LEVELS = ("intern", "new-grad", "junior", "senior", "staff-plus", "manager")
LEVEL_SHORT = {
    "intern": "Intern",
    "new-grad": "New grad",
    # The rung of L4 / E4 / SDE II — the site labels it "Junior / Mid".
    "junior": "Mid",
    "senior": "**Senior**",
    "staff-plus": "**Staff+**",
    "manager": "Manager",
}
EXPERIENCED_LEVELS = frozenset({"senior", "staff-plus"})

ROUNDS = ("oa", "phone-screen", "onsite", "take-home")
ROUND_SHORT = {"oa": "OA", "phone-screen": "Phone", "onsite": "Onsite", "take-home": "Take-home"}
ROUND_LABELS = {"oa": "Online assessment (OA)", "phone-screen": "Phone screen", "onsite": "Onsite", "take-home": "Take-home"}
ROUND_EMOJI = {"oa": "📝", "phone-screen": "📞", "onsite": "🏢", "take-home": "🏠"}

FORMATS = ("algorithm", "system-design", "object-oriented-programming", "sql", "ai-coding")
FORMAT_SHORT = {
    "algorithm": "Coding",
    "system-design": "System design",
    "object-oriented-programming": "OOD / LLD",
    "sql": "SQL",
    "ai-coding": "AI coding",
}


# ── Records ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Question:
    slug: str
    title: str
    url: str
    format: str
    difficulty: str | None
    companies: tuple[str, ...]        # display names, primary first
    company_keys: tuple[str, ...]     # page slugs, same order
    rounds: tuple[str, ...]
    levels: tuple[str, ...]
    roles: tuple[str, ...]
    role_titles: tuple[str, ...]
    topics: tuple[str, ...]
    access_tier: str
    reported: str | None
    last_reported: str | None
    seen: date | None                 # the most recent sighting we know of
    seen_month_only: bool
    groups: frozenset[str]

    @property
    def free(self) -> bool:
        return self.access_tier == "free"


@dataclass(frozen=True)
class Guide:
    title: str
    url: str
    company_key: str
    role: str  # one of GUIDE_ROLES keys, or "overview"


@dataclass(frozen=True)
class Report:
    company: str
    company_key: str
    role_title: str | None
    level: str | None
    title: str
    url: str
    posted: date | None


@dataclass(frozen=True)
class Catalog:
    questions: tuple[Question, ...]
    guides: tuple[Guide, ...]
    reports: tuple[Report, ...]
    reports_total: int | None
    labels: dict[str, str]           # company key -> display name
    site_company_urls: dict[str, str]


# ── Where you are interviewing ───────────────────────────────────────────────

#: Spelled out because "MAANG" is a list of five names and this one has six.
MAANG_PLUS = ("meta", "apple", "amazon", "netflix", "google", "microsoft")

#: Employers the shared registry has not classified yet but whose sector is not
#: in doubt. Each line is a correction waiting to land in the registry itself.
SECTOR_ALIASES = {
    "sig": "quant-trading",  # Susquehanna International Group
}


@dataclass(frozen=True)
class Group:
    id: str
    emoji: str
    label: str
    rule: str


GROUPS: tuple[Group, ...] = (
    Group("ai-labs", "🧠", "AI labs", "Employers the shared company registry files under *AI labs & AI infrastructure* — OpenAI, Anthropic, xAI, Microsoft AI, Perplexity, Scale AI and the rest."),
    Group("quant", "📈", "Quant firms", "Employers the shared company registry files under *Quant trading & hedge funds* — Jane Street, Citadel, Hudson River Trading, Two Sigma, Optiver and the rest."),
    Group("maang", "🏛️", "MAANG+", "Meta, Apple, Amazon, Netflix and Google — plus Microsoft, which is why it says MAANG**+**."),
)
GROUP_BY_ID = {g.id: g for g in GROUPS}


def group_of(company: str, labels: dict[str, str]) -> str | None:
    key = company_key(company, labels)
    if key in MAANG_PLUS:
        return "maang"
    sector, _ = segment_of(company, labels)
    sector = sector or SECTOR_ALIASES.get(key)
    if sector == "ai":
        return "ai-labs"
    if sector == "quant-trading":
        return "quant"
    return None


# ── Who you are ──────────────────────────────────────────────────────────────

ML_RESEARCH_TITLES = frozenset({"Machine Learning Engineer", "Research Scientist", "AI Engineer"})


@dataclass(frozen=True)
class Track:
    id: str
    emoji: str
    label: str
    hint: str
    rule: str
    test: Callable[[Question], bool]


TRACKS: tuple[Track, ...] = (
    Track(
        "senior-staff", "🎯", "Senior & Staff+", "≈ L5 / E5 and up",
        "Reported at a **Senior** or **Staff+** loop (the site's seniority ladder: Senior ≈ L5 / E5 / SDE III, Staff+ ≈ L6 / E6 and above).",
        lambda q: bool(EXPERIENCED_LEVELS & set(q.levels)),
    ),
    Track(
        "staff", "🚀", "Staff+ only", "≈ L6 / E6 and up",
        "Reported at a **Staff+** loop (≈ L6 / E6 / Principal and above).",
        lambda q: "staff-plus" in q.levels,
    ),
    Track(
        "ml-research", "🔬", "ML & Research Scientist", "MLE · Research scientist · AI engineer",
        "Asked for a **Machine Learning Engineer**, **Research Scientist** or **AI Engineer** role.",
        lambda q: bool(ML_RESEARCH_TITLES & set(q.role_titles)),
    ),
    Track(
        "quant-roles", "📊", "Quant researcher & developer", "QR · QD · QT",
        "Asked for a **Quantitative Finance** role — researcher, developer or trader.",
        lambda q: "Quantitative Finance" in q.roles,
    ),
    Track(
        "all", "🗂️", "Every level", "incl. new grad & unclassified",
        "Every question in the bank, whatever level or role it was reported for.",
        lambda q: True,
    ),
)
TRACK_BY_ID = {t.id: t for t in TRACKS}

#: A cut with fewer rows than this gets a dash, not a page: a page that exists for
#: an hour and then disappears breaks every link anybody shared to it.
MIN_LIST_ROWS = 3


def in_group(q: Question, group: str | None) -> bool:
    return group is None or group in q.groups


def list_slug(track: str, group: str | None) -> str:
    """The file a (track, group) cell links to, under ``lists/``."""
    if group is None:
        return track
    if track == "all":
        return group
    return f"{track}--{group}"


# ── Loop guides ──────────────────────────────────────────────────────────────

#: Role guides the Study section publishes as "<Company> <Role> Interview Process".
GUIDE_ROLES = {
    "Software Engineer": "SWE",
    "Machine Learning Engineer": "ML engineer",
    "Research Scientist": "Research scientist",
    "AI Engineer": "AI engineer",
    "Infrastructure Engineer": "Infra",
    "Quantitative Finance": "Quant",
    "Data Scientist": "Data scientist",
    "Frontend Engineer": "Frontend",
}


def guide_role(title: str) -> str | None:
    text = title.strip()
    if text.endswith("Interview Process & Questions"):
        return "overview"
    if not text.endswith(" Interview Process"):
        return None
    head = text[: -len(" Interview Process")]
    for role in GUIDE_ROLES:
        if head.endswith(" " + role):
            return role
    return "overview"


# ── Loading ──────────────────────────────────────────────────────────────────


def _date_of_iso(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def load(snapshot: dict[str, Any]) -> Catalog:
    labels: dict[str, str] = {}
    site_urls: dict[str, str] = {}
    for row in snapshot.get("companies", []):
        slug, name = row.get("slug"), row.get("name")
        if slug and name:
            # The API's names are title-cased slugs where the site has no label
            # ("Ebay"); a casing this repository knows better wins.
            if slug.lower() not in COMPANY_LABELS:
                labels[slug] = name
            if row.get("url"):
                site_urls[company_key(slug, labels)] = row["url"]

    questions = []
    for row in snapshot["questions"]:
        companies = tuple(c for c in row.get("companies") or [] if c)
        reported_date, reported_month_only = parse_sighting(row.get("reported"))
        last_date, _ = parse_sighting(row.get("lastReported"))
        seen, month_only = reported_date, reported_month_only
        # A later report outranks the first one; it is month-precision, so it
        # takes over only when it lands in a LATER month than the first sighting.
        if last_date and (seen is None or last_date > seen.replace(day=1)):
            seen, month_only = last_date, True
        levels = tuple(level for level in LEVELS if level in (row.get("seniority") or []))
        questions.append(
            Question(
                slug=row["slug"],
                title=" ".join(str(row["title"]).split()),
                url=row["url"],
                format=row.get("type") or "",
                difficulty=row.get("difficulty"),
                companies=tuple(company_label(c, labels) for c in companies),
                company_keys=tuple(company_key(c, labels) for c in companies),
                rounds=tuple(r for r in ROUNDS if r in (row.get("rounds") or [])),
                levels=levels,
                roles=tuple(row.get("roles") or []),
                role_titles=tuple(row.get("roleTitles") or []),
                topics=tuple(row.get("topics") or []),
                access_tier=row.get("accessTier") or "insider",
                reported=row.get("reported"),
                last_reported=row.get("lastReported"),
                seen=seen,
                seen_month_only=month_only,
                groups=frozenset(g for g in (group_of(c, labels) for c in companies) if g),
            )
        )

    guides = []
    for row in snapshot.get("articles", []):
        role = guide_role(row.get("title") or "")
        company = row.get("company")
        if role and company:
            guides.append(Guide(row["title"], row["url"], company_key(company, labels), role))

    reports = []
    for row in snapshot.get("experiences", []):
        reports.append(
            Report(
                company=company_label(row["company"], labels),
                company_key=company_key(row["company"], labels),
                role_title=row.get("roleTitle"),
                level=row.get("seniority"),
                title=" ".join(str(row["title"]).split()),
                url=row["url"],
                posted=_date_of_iso(row.get("postedAt")),
            )
        )

    return Catalog(
        questions=tuple(sorted(questions, key=lambda q: q.slug)),
        guides=tuple(sorted(guides, key=lambda g: (g.company_key, g.role, g.url))),
        reports=tuple(reports),
        reports_total=snapshot.get("experiencesTotal"),
        labels=labels,
        site_company_urls=site_urls,
    )


# ── Ordering and freshness ───────────────────────────────────────────────────


def is_future(q: Question, today: date) -> bool:
    return q.seen is not None and q.seen > today


def newest_first(questions, today: date) -> list[Question]:
    """Total order: dated rows newest first, then future-dated (a typo upstream),
    then undated — so no row can swap places between two runs."""

    def key(q: Question):
        if q.seen is None:
            bucket, ordinal = 2, 0
        elif q.seen > today:
            bucket, ordinal = 1, 0
        else:
            bucket, ordinal = 0, -q.seen.toordinal()
        return (bucket, ordinal, q.seen_month_only, q.title.lower(), q.slug)

    return sorted(questions, key=key)


def marker(q: Question, today: date) -> str:
    if q.seen is None or q.seen > today:
        return ""
    age = (today - q.seen).days
    if age <= HOT_DAYS:
        return "🔥"
    if age <= NEW_DAYS:
        return "🆕"
    return ""


def is_recent(q: Question, today: date, days: int = RECENT_DAYS) -> bool:
    return q.seen is not None and today - timedelta(days=days) <= q.seen <= today


def seen_text(q: Question, today: date) -> str:
    if q.seen is None:
        return "—"
    if q.seen_month_only:
        text = f"{MONTHS[q.seen.month - 1]} {q.seen.year}"
    else:
        text = f"{MONTHS[q.seen.month - 1]} {q.seen.day}, {q.seen.year}"
    mark = marker(q, today)
    return f"{mark} {text}" if mark else text
