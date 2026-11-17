<p align="center">
  <img src="assets/icon.svg" alt="docs-1 icon" width="96" height="96">
</p>

<h1 align="center">docs-1</h1>

<p align="center">
  <b>Docs that AI coding agents can find their way through, and know when to trust.</b>
</p>

<p align="center">
  <a href="https://github.com/illescasDaniel/docs-1-skill/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/illescasDaniel/docs-1-skill/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-blue.svg">
  <img alt="Dependencies: none" src="https://img.shields.io/badge/dependencies-none%20(stdlib)-brightgreen.svg">
  <a href="https://agentskills.io"><img alt="Agent Skill" src="https://img.shields.io/badge/Agent%20Skill-SKILL.md-6f42c1.svg"></a>
</p>

Project documentation that AI coding agents can navigate and maintain. Each Markdown doc has a stable ID, a summary, status and the code paths it covers. A small script generates an index and flags covered code changes for review.

- **Find the right doc:** a short index points agents to each subject.
- **Review changes:** `covers` locates related docs; `check` flags potentially stale ones.
- **Preserve context:** stable IDs survive moves, and superseded docs remain in the archive.

## How it works

| In `docs/` | Purpose |
| --- | --- |
| 🗂️ `INDEX.md` | Generated index of doc IDs, titles and summaries |
| 📝 `<area>/<slug>.md` | One subject per document |
| 🧭 `<area>/INDEX.md` | Area index when the collection grows past 150 docs |
| 🗄️ `archive/` | Deprecated and superseded documents |

The script also discovers docs-1 frontmatter in Markdown files elsewhere in the repository.

<details>
<summary>See an example document</summary>

```markdown
---
id: DOC-012
title: Release process
summary: How a version is tagged, built and published to PyPI, who approves it, and how to roll back
type: how-to          # tutorial | how-to | reference | explanation | decision | runbook
status: current       # draft | current | deprecated | superseded
updated: 2026-11-15
verified: 2026-11-15 a1b2c3d
covers: [.github/workflows/release.yml, scripts/release.sh]
related: [DOC-003]
supersedes:
superseded_by:
---

# Release process

Tag `vX.Y.Z` on main; the release workflow builds, waits for approval, then publishes.
Use this when cutting a release or fixing a failed one.
```

The types follow [Diátaxis](https://diataxis.fr), plus `decision` (one decision record) and `runbook`. Past 150 docs,
the script gives each area its own `INDEX.md` and the main index lists the areas.

</details>

## Quick start

```bash
npx skills add illescasDaniel/docs-1-skill
```

Ask your agent **“set up docs-1 for this project”**. It inventories existing docs, proposes a plan, adds frontmatter and builds the index. Existing files stay in place unless you agree to move them.

<details>
<summary>Manual installation and agent instructions</summary>

Copy the `skills/docs-1` folder into your agent's skills directory.

| | Project (shared with your team) | All your projects |
|---|---|---|
| Claude Code | `.claude/skills/docs-1/` | `~/.claude/skills/docs-1/` |
| Codex | `.agents/skills/docs-1/` | `~/.agents/skills/docs-1/` |
| Cursor | `.cursor/skills/docs-1/` | `~/.cursor/skills/docs-1/` |

Add this to `AGENTS.md` (or `CLAUDE.md`) so every agent, including ones that do not load skills, starts at the index:

```markdown
## Docs

Project docs are in `docs/`; start at `docs/INDEX.md` (generated, one line per doc). Cite docs by ID (`DOC-012`).
Code at HEAD wins over a doc. Before changing code, find the docs that cover it
(`python3 <path to the docs-1 skill>/scripts/docs_index.py covers <file>`; replace the path with where the skill is
installed, for example `.claude/skills/docs-1`) and update them in the same change, then run
`docs_index.py write` and `check`. Full protocol: the `docs-1` skill.
```

</details>

<details>
<summary>Script commands</summary>

```bash
python3 skills/docs-1/scripts/docs_index.py write            # regenerate docs/INDEX.md
python3 skills/docs-1/scripts/docs_index.py check            # missing fields, duplicate IDs, broken links, stale docs
python3 skills/docs-1/scripts/docs_index.py covers src/x.py  # which docs describe this file
python3 skills/docs-1/scripts/docs_index.py next-id          # next free DOC-n
python3 skills/docs-1/scripts/docs_index.py verify DOC-012   # stamp a doc you re-checked against the code
```

`check` exits with 1 on errors, so it can run in CI. Stale docs are warnings: a change to covered code does not always
make a doc wrong.

</details>

## Requirements and limits

Python 3.9+ and Git for history-based stale checks; the script uses only the standard library. Without Git, other checks and index generation remain available. A changed covered file is a review hint, not proof a doc is wrong.

## Evaluation

The keyless [NVIDIA SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator) quality check gave **A, 93.5/100** on the revision checked on 2026-11-17. SkillSpector reported **medium risk / caution**; its findings and review are in the evaluation details. Some checks apply to the preceding revision, and the paid Tier 3 live-agent evaluation was not run.

In separate agent tests, ordinary answer accuracy was similar with and without docs-1. The checker flagged all **15 deliberately outdated docs**, alongside **6 harmless changes**; locating docs for a file took about three fewer turns in the synthetic test. These are limited experiments, not a general guarantee. [Evaluation details](docs/evaluation.md) · [Benchmark method and results](docs/benchmark.md)

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The free, standard-library tests exercise the scripts using temporary fixtures. They require no API key and live outside the installable skill folder. They do not measure whether an agent follows the skill. See the [CI workflow](.github/workflows/ci.yml) for the test matrix.

## Related

[memory-1](https://github.com/illescasDaniel/memory-1-skill) keeps decisions, preferences and project history; docs-1 describes how the system works now.

## License

[MIT](LICENSE) · Issues and pull requests are welcome.
