# Contributing

This repository lists online assessment (OA) questions by company. The most useful
thing you can send is **an OA question you were asked, with the company, the level and
the role it was for.**

## Submit a question

[**Open a submission**](https://github.com/kevin-2023-code/Tech-OA-Questions/issues/new?template=oa-report.yml)

The form asks for the company, role, level, round, format, a summary in your own
words, and when you saw it. Questions from phone screens, onsites and take-homes are
welcome through the same form; they are listed in the sibling repository
[Tech-Interview-Questions](https://github.com/kevin-2023-code/Tech-Interview-Questions).

### Source-safe, always

**Do not** submit screenshots, account-only assessment pages, private recruiter
messages, copied problem statements, or anything covered by an NDA you signed. Two or
three sentences describing the task and its follow-ups are enough for a maintainer to
verify the report. Reports that copy a prompt verbatim are closed.

## Corrections

A wrong company, a wrong level, a duplicate row, a broken link: open an issue that
links the row and says what should change. Please **do not open a pull request against
a table or a CSV**. `README.md`, `companies/` and `data/` are generated from the
TrueInterview catalog, so an edit to a generated file is overwritten on the next sync.
The fix is made in the catalog and arrives here by itself.

## How the repository is built

- A question is listed when the catalog tags it with the `oa` round (`rounds` in the
  [public API](https://trueinterview.io/developers/api)). The tag belongs to the
  question, so a question reported at several companies is listed under each of them.
- `companies/<company>/README.md` and `companies/<company>/oa.csv` hold one company's
  rows, newest first. `data/questions.csv` and `data/questions.jsonl` hold every row.
- Level and role are the catalog's own fields (`seniority`, `roleTitles`, `roles`).
  A value the catalog does not publish is left empty, never guessed.
- Platform is the catalog's `oaPlatform`: the assessment platform (HackerRank,
  CodeSignal, Codility, ...) a candidate's report names. It is empty when no report
  names one, and the column stays empty, rather than failing, on a catalog that does
  not carry the field.

## Running it locally

```bash
python3 -m unittest discover -s scripts -p "test_*.py"   # the renderers, from a fixture
python3 scripts/sync.py --check                          # is the repository current?
python3 scripts/sync.py                                  # regenerate from the live API
```

Python 3.11+, standard library only. `scripts/api.py` is the only module that touches
the network, and it reads only the public, metadata-only API: no statement, solution
or test case ever reaches this repository. `scripts/build.py` is a pure function of
that read and the date, and `scripts/sync.py` refuses to write anything if the read
failed, if a page would exceed its byte budget, or if a relative link would break.
