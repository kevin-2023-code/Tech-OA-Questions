#!/usr/bin/env python3
"""The catalog as records, and the two axes every page here is cut by.

This repository answers one question before any other: *is this list for me?*
Its readers are the whole tech industry — interns and new grads through Staff+,
software engineers, ML and research, data scientists, quants, PMs — so the bank
is cut three ways, and all three are defined here and nowhere else:

  * **Role** — a :class:`Track` in ``ROLES`` (and the narrower ``SPECIALTIES``),
    read from the facets the catalog publishes on each question (``roles``,
    ``roleTitles``).
  * **Level** — a :class:`Track` in ``LEVEL_TRACKS``, read from ``seniority``.
    A question with no level on record is in no level list: unclassified is not
    "every level".
  * **Industry** — an :class:`Industry`: MAANG+, or a sector of the shared
    company registry (the same table the sister repositories file employers
    under), never inferred from a company's name.

Everything is a pure function of the snapshot and of ``today``, so a test can
render the whole repository from a fixture and compare bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

from labels import COMPANY_LABELS, company_key, company_label
from segments import SECTOR_BY_ID, SECTORS, segment_of

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
    "senior": "Senior",
    "staff-plus": "Staff+",
    "manager": "Manager",
}

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
    "blog": "Behavioral / concept",
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
    industries: frozenset[str]

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


# ── Industry: where you are interviewing ─────────────────────────────────────

#: Spelled out because "MAANG" is a list of five names and this one has six.
MAANG_PLUS = ("meta", "apple", "amazon", "netflix", "google", "microsoft")

#: Employers the shared registry has not classified yet but whose sector is not
#: in doubt. Each line is a correction waiting to land in the registry itself.
SECTOR_ALIASES = {
    "sig": "quant-trading",  # Susquehanna International Group
}


@dataclass(frozen=True)
class Industry:
    id: str        # also the file name under lists/
    emoji: str
    label: str
    rule: str


def _sector_industry(sector_id: str) -> Industry:
    sector = SECTOR_BY_ID[sector_id]
    return Industry(
        _SECTOR_SLUGS.get(sector_id, sector_id),
        sector.emoji,
        sector.label,
        f"Employers the shared company registry files under *{sector.label}*.",
    )


#: Two sectors keep the list names they were first published under, so links
#: shared to ``lists/ai-labs.md`` and ``lists/quant.md`` keep working.
_SECTOR_SLUGS = {"ai": "ai-labs", "quant-trading": "quant"}

#: Every industry a page can be cut by: MAANG+ first (it is how most candidates
#: name their target), then every sector of the shared registry, in its order.
INDUSTRIES: tuple[Industry, ...] = (
    Industry("maang", "🏛️", "MAANG+", "Meta, Apple, Amazon, Netflix and Google — plus Microsoft, which is why it says MAANG**+**."),
    *(_sector_industry(s.id) for s in SECTORS),
)
INDUSTRY_BY_ID = {i.id: i for i in INDUSTRIES}


def industries_of(company: str, labels: dict[str, str]) -> frozenset[str]:
    """The industries one employer is filed under: its registry sector, plus
    MAANG+ for the six. Unclassified employers are in none — never guessed."""
    key = company_key(company, labels)
    out = set()
    if key in MAANG_PLUS:
        out.add("maang")
    sector, _ = segment_of(company, labels)
    sector = sector or SECTOR_ALIASES.get(key)
    if sector:
        out.add(_SECTOR_SLUGS.get(sector, sector))
    return frozenset(out)


def sector_industry(company: str, labels: dict[str, str]) -> str | None:
    """The one registry-sector industry of an employer (not MAANG+), or None."""
    key = company_key(company, labels)
    sector, _ = segment_of(company, labels)
    sector = sector or SECTOR_ALIASES.get(key)
    return _SECTOR_SLUGS.get(sector, sector) if sector else None


# ── Role and level: who you are ──────────────────────────────────────────────

ML_RESEARCH_TITLES = frozenset({"Machine Learning Engineer", "Research Scientist", "AI Engineer"})


@dataclass(frozen=True)
class Track:
    id: str
    emoji: str
    label: str
    hint: str
    rule: str
    test: Callable[[Question], bool]


#: The role rows of the front-page matrix, broadest first.
ROLES: tuple[Track, ...] = (
    Track(
        "swe", "💻", "Software Engineering", "SWE · backend · frontend · platform",
        "Asked for a **Software** role — software, backend, frontend, platform and infrastructure engineers.",
        lambda q: "Software" in q.roles,
    ),
    Track(
        "ml-research", "🤖", "ML, AI & Research", "MLE · AI engineer · research scientist",
        "Asked for a **Machine Learning Engineer**, **AI Engineer** or **Research Scientist** role.",
        lambda q: bool(ML_RESEARCH_TITLES & set(q.role_titles)),
    ),
    Track(
        "data", "📊", "Data Science & Analytics", "DS · analytics · SQL-heavy loops",
        "Asked for a **Data Scientist** role.",
        lambda q: "Data Scientist" in q.role_titles,
    ),
    Track(
        "quant-roles", "📈", "Quantitative Finance", "QR · QD · QT",
        "Asked for a **Quantitative Finance** role — researcher, developer or trader.",
        lambda q: "Quantitative Finance" in q.roles,
    ),
    Track(
        "pm", "📱", "Product Management", "PM · TPM",
        "Asked for a **Product Manager** role.",
        lambda q: "Product & Design" in q.roles,
    ),
    Track(
        "hardware", "🔧", "Hardware Engineering", "hardware · embedded",
        "Asked for a **Hardware** role.",
        lambda q: "Hardware & Engineering" in q.roles,
    ),
)

#: Narrower cuts inside Software Engineering, one list each and no matrix row.
SPECIALTIES: tuple[Track, ...] = (
    Track("backend", "⚙️", "Backend", "", "Asked for a **Backend Engineer** role.", lambda q: "Backend Engineer" in q.role_titles),
    Track("frontend", "🖥️", "Frontend", "", "Asked for a **Frontend Engineer** role.", lambda q: "Frontend Engineer" in q.role_titles),
    Track("platform", "☁️", "Platform & infra", "", "Asked for a **Platform Engineer** role.", lambda q: "Platform Engineer" in q.role_titles),
    Track("manager", "👔", "Engineering manager", "", "Reported at a **Manager** loop.", lambda q: "manager" in q.levels),
)

#: The level columns of the front-page matrix, lowest rung first. A question
#: reported at two levels is in both columns.
LEVEL_TRACKS: tuple[Track, ...] = (
    Track(
        "new-grad", "🎓", "Intern & New grad", "university · 0–1 yrs",
        "Reported at an **Intern** or **New grad** loop.",
        lambda q: bool({"intern", "new-grad"} & set(q.levels)),
    ),
    Track(
        "mid", "🌱", "Mid", "≈ L4 / E4 / SDE II",
        "Reported at a **Mid** loop (≈ L4 / E4 / SDE II).",
        lambda q: "junior" in q.levels,
    ),
    Track(
        "senior", "🎯", "Senior", "≈ L5 / E5 / SDE III",
        "Reported at a **Senior** loop (≈ L5 / E5 / SDE III).",
        lambda q: "senior" in q.levels,
    ),
    Track(
        "staff", "🚀", "Staff+", "≈ L6 / E6 and up",
        "Reported at a **Staff+** loop (≈ L6 / E6 / Principal and above).",
        lambda q: "staff-plus" in q.levels,
    ),
)

TRACK_BY_ID = {t.id: t for t in (*ROLES, *SPECIALTIES, *LEVEL_TRACKS)}

#: A cut with fewer rows than this gets a dash, not a page: a page that exists for
#: an hour and then disappears breaks every link anybody shared to it.
MIN_LIST_ROWS = 3


def in_industry(q: Question, industry: str | None) -> bool:
    return industry is None or industry in q.industries


def list_slug(role: str | None, level: str | None) -> str:
    """The file a (role, level) matrix cell links to, under ``lists/``."""
    if role and level:
        return f"{role}--{level}"
    return role or level or ""


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
                industries=frozenset(i for c in companies for i in industries_of(c, labels)),
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
