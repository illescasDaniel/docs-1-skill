# docs-1

Project documentation that AI coding agents can find their way through and know when to trust. Each doc covers one
subject and starts with a small frontmatter block: a stable ID to cite (`DOC-012`), a one-line summary, a type, a
status, dates, and the code paths it describes. A script builds `docs/INDEX.md` (one line per doc) from that
frontmatter and flags docs whose code changed after they were last checked. It is an
[Agent Skill](https://agentskills.io) (a `SKILL.md`, a doc template and one standard-library script), so it works in
Claude Code, Codex, Cursor and any agent that can read files.

- **Read the index, open one doc.** The agent reads a short index and opens only the doc whose summary answers the
  question, instead of grepping every Markdown file.
- **Stale docs are visible.** `covers` says which files a doc describes and `verified` says at which commit it was last
  checked. `docs_index.py check` lists docs whose covered files changed since then.
- **Docs for the file you are editing.** `docs_index.py covers src/auth/token.py` lists the docs to update in the same
  change.
- **IDs survive moves.** Cite `DOC-012` in code comments, PRs and other docs; the path can change.
- **History is kept.** Replaced docs are marked `superseded` with a pointer to the new one and moved to `docs/archive/`.

## The files

```
docs/
  INDEX.md               generated: one line per doc (ID, title, type, summary), grouped by area; History last
  <area>/<slug>.md       one subject per doc
  archive/               deprecated and superseded docs
```

A doc:

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

## The script

```bash
python3 skills/docs-1/scripts/docs_index.py write            # regenerate docs/INDEX.md
python3 skills/docs-1/scripts/docs_index.py check            # missing fields, duplicate IDs, broken links, stale docs
python3 skills/docs-1/scripts/docs_index.py covers src/x.py  # which docs describe this file
python3 skills/docs-1/scripts/docs_index.py next-id          # next free DOC-n
python3 skills/docs-1/scripts/docs_index.py verify DOC-012   # stamp a doc you re-checked against the code
```

`check` exits with 1 on errors, so it can run in CI. Stale docs are warnings: a change to covered code does not always
make a doc wrong.

## Install

### Any agent: the `skills` CLI

```bash
npx skills add illescasDaniel/docs-1-skill
```

It asks which agents to install for and whether to install into the current project or globally. Non-interactive:
`npx skills add illescasDaniel/docs-1-skill -a claude-code -a codex -y`, plus `-g` for global.

### By hand

Copy the `skills/docs-1` folder into your agent's skills directory.

| | Project (shared with your team) | All your projects |
|---|---|---|
| Claude Code | `.claude/skills/docs-1/` | `~/.claude/skills/docs-1/` |
| Codex | `.agents/skills/docs-1/` | `~/.agents/skills/docs-1/` |
| Cursor | `.cursor/skills/docs-1/` | `~/.cursor/skills/docs-1/` |

## Use it

Ask your agent: *"set up docs-1 for this project"*. It lists the existing docs, shows you the plan, adds frontmatter
(in place, unless you agree to move files), and generates the index. After that, the skill's description tells the
agent to use it when writing or changing docs and when looking for the docs of a file.

Add this to `AGENTS.md` (or `CLAUDE.md`) so every agent, including ones that do not load skills, starts at the index:

```markdown
## Docs

Project docs are in `docs/`; start at `docs/INDEX.md` (generated, one line per doc). Cite docs by ID (`DOC-012`).
Code at HEAD wins over a doc. Before changing code, find the docs that cover it
(`python3 <path to the docs-1 skill>/scripts/docs_index.py covers <file>`; replace the path with where the skill is
installed, for example `.claude/skills/docs-1`) and update them in the same change, then run
`docs_index.py write` and `check`. Full protocol: the `docs-1` skill.
```

## With memory-1

[memory-1](https://github.com/illescasDaniel/memory-1-skill) and docs-1 do different jobs, so they are separate skills:

| | docs-1 | memory-1 |
|---|---|---|
| Holds | how the system works and how to work with it, now | why it is this way, what changed, preferences, status |
| Edited | in place; git keeps old versions | append-only facts; a change supersedes the old note |
| Written by | people and agents, on purpose | agents, as a side effect of working |

A formal, reviewed decision can be a `decision` doc. The informal "we tried X, the user preferred Y" belongs in memory.

## Evidence

Two tests ([docs/benchmark.md](docs/benchmark.md)). On answer accuracy docs-1 ties plain docs, on 38 real docs and on
309 synthetic ones: an agent with grep already finds the facts. What it adds is measurable elsewhere: `check` flagged
all 15 deliberately outdated docs (and 6 harmless code changes, none of 263 untouched docs), and "which docs cover this
file" was answered completely in about 3 fewer turns. It costs about one extra turn per ordinary question. The single
most useful line against outdated docs is the trust rule, "code at HEAD wins over a doc", which the `AGENTS.md`
paragraph above carries.

## Contributing

Issues and pull requests are welcome. The skill is deliberately short: if a change makes `SKILL.md` longer, it should
earn it.

## Evaluation

Checked on 2026-11-17 with [NVIDIA SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator) 0.9.0 (security scan by
SkillSpector 2.13.3, run directly because SkillEvaluator's own launch of it did not complete on this setup).

| Check | Result |
| --- | --- |
| Quality score | B, 88.5/100 (correctness 85, discoverability 85, reliability 90, efficiency 100) |
| LLM rubric score | 83.6/100 |
| Tier 1 (schema, version, license, code risk, lint, unicode) | 11 of 12 checks passed, none failed; the 12th (security scan) is the SkillSpector run below |
| Tier 2 (duplicate context) | passed, no duplicated content found |
| PII and secrets scans | passed |
| SkillSpector (with LLM review) | risk score 35, MEDIUM, recommendation CAUTION; 1 finding confirmed (no declared permissions), 4 disagreed on review |

The confirmed SkillSpector finding is accepted: the skill reads and edits Markdown files and runs one local script, and does not declare a tool allowlist, which is left to the agent runtime. The other findings (broad description, `subprocess` call to read-only `git`) were reviewed and rejected.

Not run: Tier 3, the live agent evaluation (it needs Docker). The remaining quality notes are generic ones that do not
fit this skill: no `## Purpose`/`## Troubleshooting` headings, a long description that carries the trigger conditions, and a
`version` field that is set under `metadata:` rather than at the top level.

Reproduce:

```bash
uvx --python 3.13 --from 'skillevaluator[all]' skillevaluator quality-check ./skills/docs-1
```

## License

MIT, see [LICENSE](LICENSE).
