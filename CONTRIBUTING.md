# Contributing

This list is for experienced candidates — Senior, Staff+, ML engineers, research
scientists and quants — preparing for AI labs, quant firms and MAANG. It is only as
good as the sightings behind it, and the most useful thing you can send is **a
question you were asked, with the level and the round it was for.**

## Submit a question

[**Open a submission →**](https://github.com/kevin-2023-code/Tech-OA-Questions/issues/new?template=oa-report.yml)

The form asks for:

- **Company** and **role** — software, ML engineer, research scientist / engineer,
  AI engineer, quant researcher / developer / trader.
- **Level** — Senior (≈ L5 / E5), Staff+ (≈ L6 / E6 and above), Mid, new grad. This is
  the column every list here is cut by, so it matters more than anything else on the form.
- **Round** — OA, phone screen, onsite or take-home.
- **Format** — including the ones generic lists miss: ML coding, ML system design,
  probability and brainteasers, research talks and paper discussions.
- **A summary in your own words**, and when you saw it.

### Source-safe, always

**Do not** submit screenshots, account-only assessment pages, private recruiter
messages, copied problem statements, or anything covered by an NDA you signed. Two or
three sentences describing the task and its follow-ups are enough for a maintainer to
verify the report and build a practice-safe version. Reports that copy a prompt
verbatim are closed.

## Corrections

A wrong company, a wrong level, a duplicate row, a broken link — open an issue that
links the row and says what should change. Please **do not open a pull request against
a table**: every page here is generated from the TrueInterview catalog every hour, so
an edit to a generated file is overwritten on the next sync. The fix is made in the
catalog and arrives here by itself.

## How the lists are cut

Every list is one cell of the matrix on the front page — **who you are** × **where you
are interviewing** — and [`lists/README.md`](lists/README.md) states exactly what each
one selects.

- **Level and role** are the catalog's own facets on each question (`seniority`,
  `roleTitles`, `roles` in the [public API](https://trueinterview.io/developers/api)),
  reported by the candidate or inferred from their write-up. A question with no level
  on record is in no level list — unclassified is not "every level".
- **AI labs** and **quant firms** are sectors in the shared company registry
  (`scripts/company_registry.py`), the same one the sister repositories file employers
  under. A company is never sorted into a group by its name. If one is missing or
  misfiled, a two-line pull request to the registry is welcome.
- **MAANG+** is Meta, Apple, Amazon, Netflix and Google, plus Microsoft.

## Running it locally

```bash
python3 -m unittest discover -s scripts -p "test_*.py"   # the renderers, from a fixture
python3 scripts/sync.py --check                          # is the repository current?
python3 scripts/sync.py                                  # regenerate from the live API
```

Python 3.11+, standard library only. `scripts/api.py` is the only module that touches
the network, and it reads only the public, metadata-only API — no statement, solution
or test case ever reaches this repository. `scripts/build.py` is a pure function of
that read and the date, and `scripts/sync.py` refuses to write anything if a page
would exceed its byte budget or a relative link would break.
