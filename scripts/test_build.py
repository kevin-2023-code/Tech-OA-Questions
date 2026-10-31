#!/usr/bin/env python3
"""The renderers, end to end, from a small fixture — no network, no clock."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api  # noqa: E402
import build  # noqa: E402
import model  # noqa: E402
import sync  # noqa: E402

TODAY = date(2026, 10, 11)


def q(slug, companies, *, seniority=(), roles=("Software",), titles=("Software Engineer",), rounds=("onsite",),
      reported=None, last=None, tier="insider", type_="algorithm", **extra):
    row = {
        "slug": slug,
        "number": 1,
        "title": slug.replace("-", " ").title(),
        "type": type_,
        "typeLabel": type_,
        "difficulty": "medium",
        "company": companies[0],
        "companies": list(companies),
        "topics": [],
        "tags": [],
        "rounds": list(rounds),
        "roundsSource": "reported",
        "roles": list(roles),
        "roleTitles": list(titles),
        "seniority": list(seniority),
        "reported": reported,
        "lastReported": last,
        "hasSolution": True,
        "accessTier": tier,
        "url": f"https://trueinterview.io/questions/{slug}",
        "addedAt": "2026-07-01T00:00:00+00:00",
    }
    row.update(extra)
    return row


def snapshot():
    return {
        "questions": [
            q("kv-cache", ["openai"], seniority=["senior"], roles=["Data & AI"], titles=["Research Scientist"], rounds=["phone-screen"], reported="2026-10-05"),
            q("attention-grad", ["anthropic", "google"], seniority=["senior", "staff-plus"], roles=["Data & AI"], titles=["Machine Learning Engineer"], reported="2026-09-10"),
            q("rl-eval", ["xai"], seniority=["staff-plus"], roles=["Data & AI"], titles=["AI Engineer"], reported="2026-08"),
            q("order-book", ["citadel"], seniority=["senior"], roles=["Quantitative Finance"], titles=[], rounds=["oa"], reported="2026-10-01", tier="free"),
            q("dice-game", ["sig"], seniority=["junior"], roles=["Quantitative Finance"], titles=[], rounds=["oa"], reported="2026-07-02"),
            q("market-maker", ["jane-street"], seniority=[], roles=["Quantitative Finance"], titles=[], rounds=["onsite"], reported="2026-06-01"),
            q("news-feed", ["meta"], seniority=["senior", "staff-plus"], type_="system-design", reported="2026-09-30", last="2026-10"),
            q("lru-cache", ["amazon", "microsoft"], seniority=["new-grad", "junior"], rounds=["oa"], reported="2026-05-05", tier="free"),
            q("rate-limiter", ["stripe"], seniority=["senior"], reported="2126-02-23"),  # a typo upstream
            q("undated", ["netflix"], seniority=["senior"]),
            q("two-sum", ["acme-widgets"], seniority=[], reported="2026-09-01", contentMd="SECRET STATEMENT", solution="SECRET SOLUTION"),
            q("ml-ranking", ["openai"], seniority=["senior"], roles=["Data & AI"], titles=["Machine Learning Engineer"], reported="2026-04"),
        ],
        "articles": [
            {"slug": "openai-interview-process", "title": "OpenAI Interview Process & Questions", "company": "openai", "url": "https://trueinterview.io/study/openai-interview-process"},
            {"slug": "openai-research-scientist-interview-process", "title": "OpenAI Research Scientist Interview Process", "company": "openai", "url": "https://trueinterview.io/study/openai-research-scientist-interview-process"},
            {"slug": "citadel-quantitative-finance-interview-process", "title": "Citadel Quantitative Finance Interview Process", "company": "citadel", "url": "https://trueinterview.io/study/citadel-quantitative-finance-interview-process"},
            {"slug": "two-sum-explained", "title": "Two Sum, Explained", "company": None, "url": "https://trueinterview.io/study/two-sum-explained"},
        ],
        "companies": [{"name": "OpenAI", "slug": "openai", "questionCount": 2, "url": "https://trueinterview.io/problems/company/openai"}],
        "experiences": [
            {"id": f"o{i}", "company": "oracle", "role": "Software", "roleTitle": "Software Engineer", "seniority": "senior", "title": f"Oracle loop {i}", "url": f"https://trueinterview.io/interviews/o{i}", "postedAt": "2026-09-30T00:00:00Z"}
            for i in range(5)
        ] + [
            {"id": "a1", "company": "anthropic", "role": "Data & AI", "roleTitle": "Research Scientist", "seniority": "senior", "title": "Anthropic RS loop", "url": "https://trueinterview.io/interviews/a1", "postedAt": "2026-09-20T00:00:00Z"},
            {"id": "n1", "company": "acme-widgets", "role": "Software", "roleTitle": "Software Engineer", "seniority": "new-grad", "title": "New grad loop", "url": "https://trueinterview.io/interviews/n1", "postedAt": "2026-09-29T00:00:00Z"},
        ],
        "experiencesTotal": 7,
    }


def render(snap=None):
    return build.build(model.load(snap or snapshot()), TODAY)


class FirstScreen(unittest.TestCase):
    def test_says_who_it_is_for_before_anything_else(self):
        head = render()["README.md"][:1600]
        self.assertNotIn("Experienced Hires", head)
        for phrase in ("intern to Staff+", "SWE", "ML & AI", "Data Science", "Quant", "PM", "New grad", "Senior"):
            self.assertIn(phrase, head)

    def test_matrix_counts_and_links(self):
        files = render()
        readme = files["README.md"]
        # ML/AI/research at Senior: kv-cache, attention-grad, ml-ranking.
        self.assertIn("[**3**](lists/ml-research--senior.md)", readme)
        # Quant roles, every level: order-book, dice-game, market-maker.
        self.assertIn("[**3**](lists/quant-roles.md)", readme)
        # Every role at Senior: kv-cache, attention-grad, order-book, news-feed, rate-limiter, undated, ml-ranking.
        self.assertIn("[**7**](lists/senior.md)", readme)
        # A cut under the minimum gets a dash and no page.
        self.assertNotIn("lists/ml-research--new-grad.md", files)
        self.assertIn("lists/swe.md", files)

    def test_industry_lists_cover_the_registry_not_three_groups(self):
        files = render()
        readme = files["README.md"]
        self.assertIn("(lists/maang.md)", readme)
        self.assertIn("(lists/ai-labs.md)", readme)
        self.assertIn("(lists/quant.md)", readme)
        # OpenAI (twice), Anthropic and xAI: an AI-lab list with four rows.
        self.assertIn("lists/ai-labs.md", files)
        self.assertNotIn("lists/ai.md", files)

    def test_maang_plus_counts_microsoft(self):
        cat = model.load(snapshot())
        lru = next(x for x in cat.questions if x.slug == "lru-cache")
        self.assertIn("maang", lru.industries)

    def test_latest_table_is_not_limited_to_three_groups(self):
        latest = render()["README.md"].split("## 🔥")[1].split("\n## ")[0]
        # Acme Widgets is in no industry at all, and still a recent question.
        self.assertIn("Two Sum", latest)


class Facets(unittest.TestCase):
    def test_unclassified_is_in_no_level_list(self):
        files = render()
        for level in ("new-grad", "mid", "senior", "staff"):
            self.assertNotIn("Market Maker", files.get(f"lists/{level}.md", ""))
        self.assertIn("Market Maker", files["lists/quant-roles.md"])

    def test_new_grad_list_takes_interns_and_new_grads(self):
        cat = model.load(snapshot())
        self.assertEqual([x.slug for x in build.cut(cat, level="new-grad")], ["lru-cache"])

    def test_levels_render_in_ladder_order(self):
        cat = model.load(snapshot())
        attn = next(x for x in cat.questions if x.slug == "attention-grad")
        self.assertEqual(build.level_cell(attn), "Senior · Staff+")

    def test_refuses_a_catalog_without_the_level_facet(self):
        snap = snapshot()
        for row in snap["questions"]:
            row.pop("seniority")
        with self.assertRaises(api.CatalogError):
            api.check_questions(snap["questions"])


class Freshness(unittest.TestCase):
    def test_markers(self):
        cat = model.load(snapshot())
        by = {x.slug: x for x in cat.questions}
        self.assertEqual(model.marker(by["kv-cache"], TODAY), "🔥")
        self.assertEqual(model.marker(by["attention-grad"], TODAY), "🆕")
        self.assertEqual(model.marker(by["lru-cache"], TODAY), "")

    def test_a_later_report_month_wins_over_the_first_sighting(self):
        cat = model.load(snapshot())
        feed = next(x for x in cat.questions if x.slug == "news-feed")
        self.assertEqual(feed.seen, date(2026, 10, 1))
        self.assertTrue(feed.seen_month_only)
        self.assertEqual(model.seen_text(feed, TODAY), "🔥 Oct 2026")

    def test_future_and_undated_rows_sort_last_and_are_never_fresh(self):
        cat = model.load(snapshot())
        order = [x.slug for x in model.newest_first(cat.questions, TODAY)]
        self.assertEqual(order[-2:], ["rate-limiter", "undated"])
        typo = next(x for x in cat.questions if x.slug == "rate-limiter")
        self.assertEqual(model.marker(typo, TODAY), "")
        self.assertNotIn("Rate Limiter", render()["README.md"].split("## 🔥")[1].split("## ")[0])


class Safety(unittest.TestCase):
    def test_no_body_reaches_any_file(self):
        for path, text in render().items():
            self.assertNotIn("SECRET", text, path)

    def test_export_carries_exactly_the_documented_fields(self):
        line = render()["data/questions.jsonl"].splitlines()[0]
        self.assertEqual(sorted(json.loads(line)), sorted(build.EXPORT_FIELDS))


class Structure(unittest.TestCase):
    def test_every_relative_link_resolves(self):
        self.assertEqual(sync.broken_links(render()), [])

    def test_static_files_exist(self):
        for path in sync.STATIC_FILES:
            self.assertTrue((sync.ROOT / path).exists(), path)

    def test_deterministic_and_order_independent(self):
        snap = snapshot()
        shuffled = copy.deepcopy(snap)
        shuffled["questions"].reverse()
        self.assertEqual(render(snap), render(shuffled))

    def test_within_budget(self):
        self.assertEqual(build.over_budget(render()), [])

    def test_budget_is_enforced(self):
        self.assertTrue(build.over_budget({"README.md": "x" * (build.README_MAX_BYTES + 1)}))

    def test_pages_paginate(self):
        snap = snapshot()
        base = snap["questions"][0]
        snap["questions"] = [dict(base, slug=f"q{i}", title=f"Q {i}", url=f"https://trueinterview.io/questions/q{i}") for i in range(build.PAGE_ROWS + 5)]
        files = render(snap)
        self.assertIn("question-bank/page-2.md", files)
        self.assertIn("(page-2.md)", files["question-bank/README.md"])
        self.assertEqual(sync.broken_links(files), [])

    def test_company_pages_link_role_guides(self):
        page = render()["companies/openai.md"]
        self.assertIn("[Research scientist](https://trueinterview.io/study/openai-research-scientist-interview-process)", page)
        self.assertIn("[Overview](https://trueinterview.io/study/openai-interview-process)", page)

    def test_reports_cover_every_level_and_cap_per_company(self):
        readme = render()["README.md"]
        block = readme.split("## 🗣️")[1].split("## ")[0]
        self.assertIn("Anthropic RS loop", block)
        self.assertIn("New grad loop", block)
        self.assertEqual(block.count("Oracle loop"), 2)

    def test_oa_leaders_rank_by_oa_count(self):
        readme = render()["README.md"]
        block = readme.split("## 📝")[1].split("## ")[0]
        self.assertIn("[Citadel](companies/citadel.md)", block)
        self.assertNotIn("[OpenAI]", block)


class Insights(unittest.TestCase):
    def test_level_mix_counts_each_question_once_at_its_top_level(self):
        block = "\n".join(build.insights_block(model.load(snapshot())))
        # Staff+: attention-grad, rl-eval (coding) and news-feed (system design).
        self.assertIn("| 🚀 Staff+ | 3 | 67% | 33% | 0% | 0% | 0% |", block)
        # Lowest rung first, so a reader finds their row by reading down.
        self.assertLess(block.index("🌱 Mid"), block.index("🚀 Staff+"))
        # Senior: kv-cache, order-book, rate-limiter, undated, ml-ranking — not the Staff+ three.
        self.assertIn("| 🎯 Senior | 5 | 100% |", block)

    def test_oa_share_names_its_denominator(self):
        block = "\n".join(build.insights_block(model.load(snapshot())))
        # Quant firms: order-book and dice-game are OA, market-maker is not.
        self.assertIn("| 📈 Quant trading & hedge funds | 3 | 67% |", block)


class Guides(unittest.TestCase):
    def test_role_is_read_from_the_title(self):
        self.assertEqual(model.guide_role("OpenAI Research Scientist Interview Process"), "Research Scientist")
        self.assertEqual(model.guide_role("Two Sigma Interview Process & Questions"), "overview")
        self.assertIsNone(model.guide_role("Two Sum, Explained"))


if __name__ == "__main__":
    unittest.main()
