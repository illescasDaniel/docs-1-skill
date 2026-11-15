# Test

One small test so far, and it did not show a difference in answer quality. It is reported here as it came out.

- **Project:** a real application repository with 38 Markdown docs (`docs/`, `specs/`, `design/`, `packaging/`).
- **Setup:** a Claude Haiku agent applied this skill to a copy of the repository ("set up docs-1", frontmatter in place,
  no files moved): 36 docs got frontmatter and a 52-line `docs/INDEX.md` was generated. 86 turns, $0.03.
- **Questions:** 14, written by Claude Sonnet from the docs (5 needle facts, 4 how-to, 3 why, 2 needing two docs).
- **Answering:** Claude Haiku with Read, Grep and Glob, 2 answers per question. The original copy was told the docs are
  in `docs/` and other Markdown files; the docs-1 copy was told to start at `docs/INDEX.md`.
- **Grading:** Claude Sonnet, blind, 2 passes, score 0 to 2.

| | score | turns per answer | $ per answer | opened the index |
|---|---|---|---|---|
| original docs | 2.00 | 6.8 | 0.0033 | n/a |
| with docs-1 | 1.98 | 6.3 | 0.0038 | 28 of 28 |

At 38 docs, grep already finds everything, so both score at the ceiling and the index saves about half a turn. What
this test does not cover, and where the design is aimed: hundreds of docs, stale docs (detected through `covers` and
`verified`, checked by hand here but not benchmarked), finding the docs for a file before editing it, and keeping the
index current over time. The setup run did surface one real gap, fixed since: the script only indexed `docs/`, and now
indexes any Markdown file in the repository that has docs-1 frontmatter.
