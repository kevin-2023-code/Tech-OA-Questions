# Contributing

This list is for anyone interviewing in tech — interns and new grads through Staff+,
software engineers, ML and AI engineers, research scientists, data scientists, quants
and PMs — at big tech, AI labs, startups, fintechs, quant firms and everywhere in
between. It is only as good as the sightings behind it, and the most useful thing you
can send is **a question you were asked, with the level and the round it was for.**

## Submit a question

[**Open a submission →**](https://github.com/kevin-2023-code/Tech-OA-Questions/issues/new?template=oa-report.yml)

The form asks for:

- **Company** and **role** — software (backend, frontend, platform), ML / AI engineer,
  research scientist, data scientist, quant researcher / developer / trader, product
  manager, hardware.
- **Level** — intern, new grad, Mid (≈ L4 / E4), Senior (≈ L5 / E5), Staff+ (≈ L6 / E6
  and above). Every list here is cut by it, so it matters more than anything else on the form.
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

Every list is a cut of one bank by **role**, **level** or **industry** — the front page
is a role × level matrix plus one list per industry — and
[`lists/README.md`](lists/README.md) states exactly what each one selects.

- **Role and level** are the catalog's own facets on each question (`roles`,
  `roleTitles`, `seniority` in the [public API](https://trueinterview.io/developers/api)),
  reported by the candidate or inferred from their write-up. A question reported at two
  levels is on both lists; a question with no level on record is on no level list —
  unclassified is not "every level".
- **Industries** are the sectors of the shared company registry
  (`scripts/company_registry.py`), the same one the sister repositories file employers
  under. A company is never sorted into one by its name. If one is missing or
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
