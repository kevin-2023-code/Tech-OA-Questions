#!/usr/bin/env python3
"""The renderers, end to end, from a small fixture: no network, no clock."""

from __future__ import annotations

import copy
import csv
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api  # noqa: E402
import build  # noqa: E402
import model  # noqa: E402
import sync  # noqa: E402

TODAY = date(2026, 10, 11)


def q(slug, companies, *, seniority=(), roles=("Software",), titles=("Software Engineer",), rounds=("oa",),
      reported=None, last=None, tier="insider", type_="algorithm", difficulty="medium", **extra):
    row = {
        "slug": slug,
        "number": 1,
        "title": slug.replace("-", " ").title(),
        "type": type_,
        "typeLabel": type_,
        "difficulty": difficulty,
        "company": companies[0] if companies else None,
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
            # OA rows.
            q("order-book", ["citadel"], seniority=["senior"], roles=["Quantitative Finance"], titles=[], reported="2026-10-01", difficulty="hard",
              oaPlatform="HackerRank"),
            q("dice-game", ["citadel"], seniority=["junior"], roles=["Quantitative Finance"], titles=[], reported="2026-07-02"),
            q("lru-cache", ["amazon", "microsoft"], seniority=["new-grad", "junior"], reported="2026-05-05", last="2026-09"),
            q("sql-funnel", ["amazon"], seniority=["senior"], roles=["Data & AI"], titles=["Data Scientist"], type_="sql", last="2026-08"),
            q("tell-me-why", ["amazon"], type_="blog", difficulty=None, reported="2026-06-10"),
            q("rate-limiter", ["stripe"], seniority=["senior"], reported="2126-02-23"),  # a typo upstream
            q("undated", ["stripe"], seniority=["senior"]),
            q("pipe|title [x]", ["acme-widgets"], reported="2026-09-01", contentMd="SECRET STATEMENT", solution="SECRET SOLUTION"),
            q("mixed-rounds", ["openai"], rounds=["oa", "onsite"], reported="2026-10-05"),
            q("no-company", [], reported="2026-04-01"),
            # Not OA: belongs to the sibling repository.
            q("news-feed", ["meta"], seniority=["senior"], rounds=["onsite"], type_="system-design", reported="2026-09-30"),
            q("kv-cache", ["openai"], seniority=["senior"], rounds=["phone-screen"], reported="2026-10-06"),
            q("take-home", ["netflix"], rounds=["take-home"], reported="2026-10-02"),
            q("no-round", ["google"], rounds=[], reported="2026-10-03"),
        ],
        "companies": [{"name": "OpenAI", "slug": "openai", "questionCount": 2, "url": "https://trueinterview.io/problems/company/openai"}],
    }


def render(snap=None):
    return build.build(model.load(snap or snapshot()), TODAY)


def rows_of(text):
    return list(csv.reader(io.StringIO(text)))


class OnlyOA(unittest.TestCase):
    def test_a_company_with_no_oa_question_gets_no_folder(self):
        files = render()
        folders = {path.split("/")[1] for path in files if path.startswith("companies/")}
        self.assertEqual(folders, {"acme-widgets", "amazon", "citadel", "microsoft", "openai", "stripe"})

    def test_other_rounds_reach_no_file(self):
        for path, text in render().items():
            for title in ("News Feed", "Kv Cache", "Take Home", "No Round"):
                self.assertNotIn(title, text, path)

    def test_a_question_with_oa_among_its_rounds_is_listed(self):
        self.assertIn("Mixed Rounds", render()["companies/openai/README.md"])

    def test_a_question_at_two_companies_is_listed_under_each(self):
        files = render()
        self.assertIn("Lru Cache", files["companies/amazon/README.md"])
        self.assertIn("Lru Cache", files["companies/microsoft/oa.csv"])

    def test_every_folder_has_exactly_the_two_files(self):
        names = sorted(path.split("/", 2)[2] for path in render() if path.startswith("companies/amazon/"))
        self.assertEqual(names, ["README.md", "oa.csv"])

    def test_the_flat_and_cut_layouts_are_gone(self):
        for path in render():
            self.assertFalse(path.startswith(("lists/", "rounds/", "formats/", "question-bank/")), path)
            if path.startswith("companies/"):
                self.assertEqual(path.count("/"), 2, path)


class CompanyFiles(unittest.TestCase):
    def test_csv_columns(self):
        rows = rows_of(render()["companies/citadel/oa.csv"])
        self.assertEqual(rows[0], ["Title", "Format", "Platform", "Difficulty", "Level", "Role", "Last Reported", "Link"])
        self.assertEqual(rows[1], ["Order Book", "Coding", "HackerRank", "Hard", "Senior", "Quantitative Finance", "2026-10", "https://trueinterview.io/questions/order-book"])

    def test_newest_first_in_table_and_csv(self):
        files = render()
        titles = [row[0] for row in rows_of(files["companies/amazon/oa.csv"])[1:]]
        self.assertEqual(titles, ["Lru Cache", "Sql Funnel", "Tell Me Why"])
        page = files["companies/amazon/README.md"]
        self.assertLess(page.index("Lru Cache"), page.index("Sql Funnel"))
        self.assertLess(page.index("Sql Funnel"), page.index("Tell Me Why"))

    def test_a_later_report_month_wins_over_the_first_report(self):
        rows = rows_of(render()["companies/amazon/oa.csv"])
        self.assertEqual(rows[1][6], "2026-09")

    def test_levels_render_in_ladder_order(self):
        rows = rows_of(render()["companies/amazon/oa.csv"])
        self.assertEqual(rows[1][4], "New grad; Mid")

    def test_role_is_the_title_or_else_the_group_never_invented(self):
        files = render()
        self.assertEqual(rows_of(files["companies/amazon/oa.csv"])[2][5], "Data Scientist")
        self.assertEqual(rows_of(files["companies/citadel/oa.csv"])[1][5], "Quantitative Finance")
        snap = snapshot()
        snap["questions"] = [q("bare", ["acme"], roles=[], titles=[])]
        self.assertEqual(rows_of(render(snap)["companies/acme/oa.csv"])[1][4:7], ["", "", ""])

    def test_missing_values_stay_empty(self):
        row = next(r for r in rows_of(render()["companies/amazon/oa.csv"]) if r[0] == "Tell Me Why")
        self.assertEqual(row[1:5], ["Behavioral / concept", "", "", ""])
        self.assertIn("| Behavioral / concept | - | - | - |", render()["companies/amazon/README.md"])

    def test_future_and_undated_rows_sort_last_and_carry_no_date(self):
        rows = rows_of(render()["companies/stripe/oa.csv"])[1:]
        self.assertEqual([r[0] for r in rows], ["Rate Limiter", "Undated"])
        self.assertEqual([r[6] for r in rows], ["", ""])

    def test_table_cells_are_escaped(self):
        page = render()["companies/acme-widgets/README.md"]
        self.assertIn("[Pipe\\|Title \\[X\\]](https://trueinterview.io/questions/pipe|title [x])", page)

    def test_page_names_the_company_and_the_count(self):
        page = render()["companies/citadel/README.md"]
        self.assertIn("# Citadel OA Questions", page)
        self.assertIn("2 online assessment questions reported at Citadel", page)
        self.assertIn("1 online assessment question reported at OpenAI", render()["companies/openai/README.md"])


class Readme(unittest.TestCase):
    def test_snapshot_line_is_dated_and_counts_oa_only(self):
        self.assertIn("**Snapshot as of 2026-10-11: 10 OA questions from 6 companies.**", render()["README.md"])

    def test_one_table_ranked_by_oa_count_linking_each_folder(self):
        readme = render()["README.md"]
        table = [line for line in readme.splitlines() if line.startswith("|")]
        self.assertEqual(table[0], "| Company | OA questions | Newest OA |")
        self.assertEqual(sum(line.startswith("| :--") for line in table), 1)
        self.assertEqual(table[2], "| [Amazon](companies/amazon/README.md) | 3 | 2026-09 |")
        self.assertEqual(table[3], "| [Citadel](companies/citadel/README.md) | 2 | 2026-10 |")
        self.assertIn("| [Stripe](companies/stripe/README.md) | 2 | - |", table)
        self.assertEqual(len(table), 2 + 6)

    def test_short_and_plain(self):
        readme = render()["README.md"]
        prose = [line for line in readme.splitlines() if not line.startswith("|")]
        self.assertLessEqual(len(prose), 60)
        for banned in ("🔥", "🆕", "hourly", "every hour", "![", ".svg", "lists/", "question-bank/"):
            self.assertNotIn(banned, readme)
        self.assertTrue(all(ord(ch) < 0x2000 for ch in readme), "no emoji")

    def test_site_and_sibling_are_linked_once(self):
        readme = render()["README.md"]
        self.assertEqual(readme.count("trueinterview.io"), 1)
        self.assertEqual(readme.count(build.SISTER), 1)


class Data(unittest.TestCase):
    def test_csv_is_the_company_columns_plus_company(self):
        rows = rows_of(render()["data/questions.csv"])
        self.assertEqual(rows[0], ["Company", *build.COLUMNS])
        self.assertEqual(len(rows) - 1, 10)
        self.assertIn(["Amazon; Microsoft", "Lru Cache", "Coding", "", "Medium", "New grad; Mid", "Software Engineer", "2026-09",
                       "https://trueinterview.io/questions/lru-cache"], rows)

    def test_a_question_with_no_company_is_in_the_data_and_in_no_folder(self):
        files = render()
        self.assertIn("No Company", files["data/questions.csv"])
        self.assertEqual([p for p in files if p.startswith("companies/") and "No Company" in files[p]], [])

    def test_jsonl_carries_the_same_fields(self):
        lines = render()["data/questions.jsonl"].splitlines()
        self.assertEqual(len(lines), 10)
        for line in lines:
            self.assertEqual(sorted(json.loads(line)), sorted(("company", *build.FIELDS)))


class Platform(unittest.TestCase):
    def test_platform_renders_in_table_csv_and_jsonl(self):
        files = render()
        self.assertIn("| Coding | HackerRank | Hard |", files["companies/citadel/README.md"])
        row = next(r for r in rows_of(files["data/questions.csv"]) if r[1] == "Order Book")
        self.assertEqual(row[3], "HackerRank")
        line = next(json.loads(x) for x in files["data/questions.jsonl"].splitlines() if "Order Book" in x)
        self.assertEqual(line["platform"], "HackerRank")

    def test_a_catalog_without_the_field_still_renders_with_the_column_empty(self):
        # The API ships `oaPlatform` after this repository learns to read it: the
        # hourly sync must keep working on a catalog that has no such key at all.
        snap = snapshot()
        for row in snap["questions"]:
            row.pop("oaPlatform", None)
        api.check_questions(snap["questions"])
        rows = rows_of(render(snap)["companies/citadel/oa.csv"])
        self.assertEqual(rows[0][2], "Platform")
        self.assertEqual({r[2] for r in rows[1:]}, {""})

    def test_null_and_junk_values_read_as_unknown(self):
        for value in (None, "", "   ", 7, ["HackerRank"], "x" * 41):
            self.assertIsNone(model.parse_platform(value), value)
        self.assertEqual(model.parse_platform("  Code  Signal "), "Code Signal")

    def test_platform_is_escaped_in_the_table(self):
        snap = snapshot()
        snap["questions"] = [q("weird", ["acme"], oaPlatform="Hacker|Rank")]
        self.assertIn("Hacker\\|Rank", render(snap)["companies/acme/README.md"])


class Safety(unittest.TestCase):
    def test_no_body_reaches_any_file(self):
        for path, text in render().items():
            self.assertNotIn("SECRET", text, path)

    def test_refuses_a_catalog_without_a_field_the_pages_need(self):
        for field in ("rounds", "seniority", "roles"):
            snap = snapshot()
            for row in snap["questions"]:
                row.pop(field)
            with self.assertRaises(api.CatalogError):
                api.check_questions(snap["questions"])

    def test_refuses_an_empty_catalog(self):
        with self.assertRaises(api.CatalogError):
            api.check_questions([])

    def test_the_sync_reads_only_the_public_metadata_endpoints(self):
        seen = []

        def fake_get(base_url, path):
            seen.append(path.split("?")[0])
            if "questions" in path:
                return {"questions": snapshot()["questions"], "page": {"hasMore": False, "total": 14, "totalExact": True}}
            return {"companies": []}

        with mock.patch.object(api, "_get", fake_get):
            api.fetch_snapshot("https://example.invalid")
        self.assertEqual(seen, ["/api/v1/questions", "/api/v1/companies"])


class Sync(unittest.TestCase):
    """sync.main against a temporary tree: what it writes, prunes and refuses."""

    def run_sync(self, root: Path, snap, *args):
        source = root / "snapshot.json"
        source.write_text(json.dumps(snap), encoding="utf-8")
        with mock.patch.object(sync, "ROOT", root):
            return sync.main(["--catalog-file", str(source), "--today", TODAY.isoformat(), "--quiet", *args])

    def test_second_run_changes_nothing_and_orphans_are_pruned_in_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CONTRIBUTING.md").write_text("hand-written", encoding="utf-8")
            (root / "scripts").mkdir()
            (root / "scripts" / "keep.py").write_text("x", encoding="utf-8")
            (root / "companies").mkdir()
            (root / "companies" / "old-flat-page.md").write_text("stale", encoding="utf-8")
            self.assertEqual(self.run_sync(root, snapshot()), 0)
            self.assertFalse((root / "companies" / "old-flat-page.md").exists())
            self.assertTrue((root / "companies" / "citadel" / "oa.csv").exists())
            self.assertEqual((root / "CONTRIBUTING.md").read_text(encoding="utf-8"), "hand-written")
            self.assertTrue((root / "scripts" / "keep.py").exists())
            self.assertEqual(self.run_sync(root, snapshot(), "--check"), 0)
            self.assertNotIn(b"\r\n", (root / "companies" / "citadel" / "oa.csv").read_bytes())

            # Citadel loses its OA questions: its folder goes, nothing else does.
            snap = snapshot()
            snap["questions"] = [row for row in snap["questions"] if row["companies"] != ["citadel"]]
            self.assertEqual(self.run_sync(root, snap, "--check"), 1)
            self.assertEqual(self.run_sync(root, snap), 0)
            self.assertFalse((root / "companies" / "citadel").exists())
            self.assertTrue((root / "companies" / "amazon" / "README.md").exists())

    def test_a_catalog_with_no_oa_row_writes_and_prunes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(self.run_sync(root, snapshot()), 0)
            snap = snapshot()
            snap["questions"] = [row for row in snap["questions"] if "oa" not in row["rounds"]]
            self.assertEqual(self.run_sync(root, snap), 3)
            self.assertTrue((root / "companies" / "citadel" / "oa.csv").exists())

    def test_an_unreadable_catalog_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(self.run_sync(root, {"questions": []}), 2)
            self.assertFalse((root / "README.md").exists())


class Structure(unittest.TestCase):
    def test_every_relative_link_resolves(self):
        self.assertEqual(sync.broken_links(render()), [])

    def test_a_broken_link_is_reported(self):
        files = render()
        files["README.md"] += "[x](companies/nowhere/README.md)\n"
        self.assertEqual(sync.broken_links(files), ["README.md → companies/nowhere/README.md"])

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
        self.assertTrue(build.over_budget({"companies/a/README.md": "x" * (build.PAGE_MAX_BYTES + 1)}))

    def test_generated_scope_is_two_directories(self):
        self.assertEqual(sync.GENERATED_DIRS, ("companies", "data"))


if __name__ == "__main__":
    unittest.main()
