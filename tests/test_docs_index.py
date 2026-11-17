"""Tests for skills/docs-1/scripts/docs_index.py (standard library only; run: python3 -m unittest discover -s tests -v).

Each test builds a throwaway project in a temp dir (usually a real git repo) and runs the script as a subprocess,
the way an agent would, so exit codes and printed output are what is checked.
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "docs-1" / "scripts" / "docs_index.py"
sys.path.insert(0, str(SCRIPT.parent))
import docs_index  # noqa: E402  (imported to unit-test the pure helpers)


def doc(id="DOC-001", title="Auth", summary="How auth works", type="explanation", status="current",
        updated="2026-01-01", extra="", body="# Auth\n"):
    lines = [f"id: {id}", f"title: {title}", f"summary: {summary}", f"type: {type}", f"status: {status}",
             f"updated: {updated}"]
    return "---\n" + "\n".join(lines) + ("\n" + extra if extra else "") + "\n---\n\n" + body


class Project(unittest.TestCase):
    git_repo = True

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        (self.root / "docs").mkdir()
        if self.git_repo:
            self.git("init", "-q")
            self.git("config", "user.email", "t@example.com")
            self.git("config", "user.name", "Test")
            self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        r = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def commit(self, msg="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "--short", "HEAD")

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run_cli(self, *args):
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull}
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], cwd=self.root, capture_output=True,
                              text=True, env=env)


class FrontmatterTests(unittest.TestCase):
    def test_scalars_inline_lists_and_comments(self):
        m = docs_index.frontmatter(textwrap.dedent("""\
            ---
            id: DOC-007
            type: how-to          # tutorial | how-to
            covers: [src/a.py, "src/b/"]
            related: []
            superseded_by:
            ---
            body
            """))
        self.assertEqual(m["id"], "DOC-007")
        self.assertEqual(m["type"], "how-to")
        self.assertEqual(m["covers"], ["src/a.py", "src/b/"])
        self.assertEqual(m["related"], [])
        self.assertEqual(m["superseded_by"], "")

    def test_block_lists(self):
        m = docs_index.frontmatter("---\ncovers:\n  - src/a.py\n  - 'src/b.py'\n---\n")
        self.assertEqual(m["covers"], ["src/a.py", "src/b.py"])

    def test_no_frontmatter(self):
        self.assertIsNone(docs_index.frontmatter("# Just a heading\n"))


class GlobTests(unittest.TestCase):
    def match(self, pattern, path):
        return bool(docs_index.glob_re(pattern).match(path))

    def test_exact_file_and_directory_prefix(self):
        self.assertTrue(self.match("src/a.py", "src/a.py"))
        self.assertTrue(self.match("src/auth", "src/auth/token.py"))
        self.assertFalse(self.match("src/auth", "src/authz/token.py"))

    def test_trailing_slash_covers_everything_below(self):
        self.assertTrue(self.match("src/", "src/deep/er/x.py"))

    def test_single_star_does_not_cross_directories(self):
        self.assertTrue(self.match("src/*.py", "src/a.py"))
        self.assertFalse(self.match("src/*.py", "src/sub/a.py"))

    def test_double_star(self):
        self.assertTrue(self.match("src/**/x.py", "src/x.py"))
        self.assertTrue(self.match("src/**/x.py", "src/a/b/x.py"))
        self.assertFalse(self.match("src/**/x.py", "other/x.py"))

    def test_leading_dot_slash_is_ignored(self):
        self.assertTrue(self.match("./src/a.py", "src/a.py"))


class WriteTests(Project):
    def test_index_lists_docs_by_area_with_history_last(self):
        self.write("docs/api/auth.md", doc("DOC-001", "Auth", "How auth works"))
        self.write("docs/overview.md", doc("DOC-002", "Overview", "What this is", type="reference"))
        self.write("docs/archive/old.md", doc("DOC-003", "Old", "Gone", status="superseded",
                                              extra="superseded_by: DOC-001"))
        r = self.run_cli("write")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.root / "docs/INDEX.md").read_text()
        self.assertIn("- DOC-001 [Auth](api/auth.md) explanation: How auth works", text)
        self.assertIn("- DOC-003 [Old](archive/old.md) explanation (superseded): Gone", text)
        self.assertLess(text.index("## General"), text.index("## api"))
        self.assertLess(text.index("## api"), text.index("## History"))
        self.assertIn("wrote", r.stdout)

    def test_write_is_idempotent_and_skips_generated_index(self):
        self.write("docs/a.md", doc())
        self.run_cli("write")
        first = (self.root / "docs/INDEX.md").read_text()
        self.run_cli("write")
        self.assertEqual(first, (self.root / "docs/INDEX.md").read_text())
        self.assertEqual(first.count("DOC-001"), 1)

    def test_docs_outside_docs_folder_are_indexed_by_id(self):
        self.write("specs/login/SPEC.md", doc("DOC-005", "Login spec", "Login flow"))
        self.write("README.md", "# no frontmatter\n")
        self.run_cli("write")
        text = (self.root / "docs/INDEX.md").read_text()
        self.assertIn("## specs", text)
        self.assertIn("[Login spec](../specs/login/SPEC.md)", text)
        self.assertNotIn("README", text)

    def test_vendored_and_hidden_folders_are_pruned(self):
        self.write("node_modules/pkg/doc.md", doc("DOC-009"))
        self.write(".hidden/doc.md", doc("DOC-010"))
        self.write("docs/a.md", doc())
        self.run_cli("write")
        text = (self.root / "docs/INDEX.md").read_text()
        self.assertNotIn("DOC-009", text)
        self.assertNotIn("DOC-010", text)

    def test_splits_into_area_indexes_past_150_docs(self):
        for i in range(1, 152):
            self.write(f"docs/ops/d{i}.md", doc(f"DOC-{i:03d}", f"T{i}", f"S{i}"))
        self.write("docs/top.md", doc("DOC-900", "Top", "Top-level"))
        self.run_cli("write")
        main = (self.root / "docs/INDEX.md").read_text()
        self.assertIn("## Areas", main)
        self.assertIn("- [ops](ops/INDEX.md): 151 docs", main)
        self.assertIn("DOC-900", main)
        self.assertNotIn("DOC-001 ", main)
        self.assertIn("DOC-001 ", (self.root / "docs/ops/INDEX.md").read_text())
        # the split index must still pass check (area indexes are counted)
        self.assertEqual(self.run_cli("check").returncode, 0)


class CheckTests(Project):
    def check(self):
        self.run_cli("write")
        return self.run_cli("check")

    def test_clean_project_passes(self):
        self.write("docs/a.md", doc())
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 docs, 0 errors, 0 warnings", r.stdout)

    def test_missing_index_is_an_error(self):
        self.write("docs/a.md", doc())
        r = self.run_cli("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("INDEX.md missing", r.stdout)

    def test_outdated_index_is_an_error(self):
        self.write("docs/a.md", doc())
        self.run_cli("write")
        self.write("docs/b.md", doc("DOC-002", "B", "Second"))
        r = self.run_cli("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("INDEX.md is out of date", r.stdout)

    def test_missing_required_field_and_bad_enums(self):
        self.write("docs/a.md", "---\nid: DOC-001\ntitle: A\ntype: essay\nstatus: wip\nupdated: 2026-01-01\n---\n")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing summary", r.stdout)
        self.assertIn("type essay not in", r.stdout)
        self.assertIn("status wip not in", r.stdout)

    def test_bad_id_format(self):
        self.write("docs/a.md", doc("ABC-1"))
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("is not DOC-<number>", r.stdout)

    def test_duplicate_ids(self):
        self.write("docs/a.md", doc("DOC-001"))
        self.write("docs/b.md", doc("DOC-001", "Other"))
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("duplicate id DOC-001", r.stdout)

    def test_broken_relative_link_but_not_urls_or_anchors(self):
        self.write("docs/b.md", doc("DOC-002", "B", "B doc"))
        self.write("docs/a.md", doc(body="[ok](b.md#x) [web](https://example.com/x) [mail](mailto:a@b.c) "
                                         "[bad](missing.md)\n"))
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("broken link missing.md", r.stdout)
        self.assertNotIn("broken link b.md", r.stdout)
        self.assertNotIn("example.com", r.stdout)

    def test_unknown_related_and_superseded_without_pointer(self):
        self.write("docs/a.md", doc(extra="related: [DOC-099]"))
        self.write("docs/archive/b.md", doc("DOC-002", "B", "B", status="superseded"))
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("related DOC-099 is not a known id", r.stdout)
        self.assertIn("superseded but no superseded_by", r.stdout)

    def test_history_doc_outside_archive_is_only_a_warning(self):
        self.write("docs/a.md", doc(status="deprecated"))
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("deprecated doc outside docs/archive/", r.stdout)

    def test_file_without_frontmatter_in_docs_is_a_warning(self):
        self.write("docs/a.md", doc())
        self.write("docs/plain.md", "# plain\n")
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no docs-1 frontmatter, not indexed", r.stdout)


class StalenessTests(Project):
    def setUp(self):
        super().setUp()
        self.write("src/auth.py", "v1\n")
        self.write("src/other.py", "v1\n")
        self.write("docs/a.md", doc(extra="covers: [src/auth.py]\nverified:"))
        self.commit("initial")

    def stamp(self, sha):
        self.write("docs/a.md", doc(extra=f"covers: [src/auth.py]\nverified: 2026-01-01 {sha}"))

    def test_change_to_covered_file_after_verified_commit_is_flagged(self):
        sha = self.git("rev-parse", "--short", "HEAD")
        self.stamp(sha)
        self.write("src/auth.py", "v2\n")
        self.commit("change auth")
        self.run_cli("write")
        r = self.run_cli("check")
        self.assertEqual(r.returncode, 0)  # stale is a warning, not an error
        self.assertIn("STALE?", r.stdout)
        self.assertIn("1 commit(s) touched its covered paths", r.stdout)

    def test_change_to_unrelated_file_is_not_flagged(self):
        sha = self.git("rev-parse", "--short", "HEAD")
        self.stamp(sha)
        self.write("src/other.py", "v2\n")
        self.commit("change other")
        self.run_cli("write")
        self.assertNotIn("STALE?", self.run_cli("check").stdout)

    def test_directory_cover_matches_nested_files(self):
        self.write("docs/a.md", doc(extra="covers: [src/]\nverified: 2026-01-01 " + self.git("rev-parse", "--short", "HEAD")))
        self.write("src/deep/x.py", "x\n")
        self.commit("add nested")
        self.run_cli("write")
        self.assertIn("STALE?", self.run_cli("check").stdout)

    def test_current_doc_with_covers_but_no_verified_warns(self):
        self.run_cli("write")
        r = self.run_cli("check")
        self.assertIn("never verified against the code", r.stdout)
        self.assertEqual(r.returncode, 0)

    def test_deprecated_docs_are_never_stale(self):
        sha = self.git("rev-parse", "--short", "HEAD")
        self.write("docs/archive/a.md", doc(status="deprecated",
                                            extra=f"covers: [src/auth.py]\nverified: 2026-01-01 {sha}"))
        (self.root / "docs/a.md").unlink()
        self.write("src/auth.py", "v2\n")
        self.commit("change")
        self.run_cli("write")
        self.assertNotIn("STALE?", self.run_cli("check").stdout)


class CoversTests(Project):
    def setUp(self):
        super().setUp()
        self.write("docs/a.md", doc("DOC-001", "Auth", "Auth docs", extra="covers: [src/auth/]"))
        self.write("docs/b.md", doc("DOC-002", "Cfg", "Config docs", extra="covers: [config.yml, src/*.py]"))

    def test_lists_matching_docs_only(self):
        r = self.run_cli("covers", "src/auth/token.py")
        self.assertIn("DOC-001 docs/a.md [current]: Auth docs", r.stdout)
        self.assertNotIn("DOC-002", r.stdout)

    def test_several_paths_and_absolute_paths(self):
        r = self.run_cli("covers", str(self.root / "config.yml"), "src/x.py")
        self.assertIn("DOC-002", r.stdout)
        self.assertNotIn("DOC-001", r.stdout)

    def test_no_match_prints_nothing(self):
        r = self.run_cli("covers", "unrelated/file.py")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")


class NextIdTests(Project):
    def test_empty_project_starts_at_001(self):
        self.assertEqual(self.run_cli("next-id").stdout.strip(), "DOC-001")

    def test_uses_highest_id_not_count(self):
        self.write("docs/a.md", doc("DOC-003"))
        self.write("docs/b.md", doc("DOC-041", "B", "B"))
        self.assertEqual(self.run_cli("next-id").stdout.strip(), "DOC-042")


class VerifyTests(Project):
    def test_stamps_date_and_head_and_preserves_the_rest(self):
        self.write("docs/a.md", doc(extra="verified:\ncovers: [src/x.py]", body="# Auth\n\nBody text.\n"))
        sha = self.commit()
        r = self.run_cli("verify", "DOC-001")
        self.assertEqual(r.returncode, 0, r.stdout)
        text = (self.root / "docs/a.md").read_text()
        meta = docs_index.frontmatter(text)
        self.assertRegex(meta["verified"], rf"^\d{{4}}-\d{{2}}-\d{{2}} {sha}$")
        self.assertEqual(meta["covers"], ["src/x.py"])
        self.assertTrue(text.endswith("# Auth\n\nBody text.\n"))

    def test_adds_verified_when_absent(self):
        self.write("docs/a.md", doc())
        self.commit()
        self.run_cli("verify", "DOC-001")
        self.assertTrue(docs_index.frontmatter((self.root / "docs/a.md").read_text())["verified"])

    def test_unknown_id_exits_1(self):
        self.write("docs/a.md", doc())
        r = self.run_cli("verify", "DOC-001", "DOC-404")
        self.assertEqual(r.returncode, 1)
        self.assertIn("DOC-404: no such doc", r.stdout)


class NoGitTests(Project):
    git_repo = False

    def test_all_commands_work_without_git(self):
        self.write("docs/a.md", doc(extra="covers: [src/x.py]\nverified: 2026-01-01"))
        self.assertEqual(self.run_cli("write").returncode, 0)
        r = self.run_cli("check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.run_cli("next-id").stdout.strip(), "DOC-002")
        self.assertIn("DOC-001", self.run_cli("covers", "src/x.py").stdout)
        self.assertEqual(self.run_cli("verify", "DOC-001").returncode, 0)


class CliTests(Project):
    def test_missing_docs_folder(self):
        r = self.run_cli("--docs", "nope", "check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no docs folder at nope", r.stderr)

    def test_custom_docs_folder(self):
        self.write("handbook/a.md", doc())
        self.assertEqual(self.run_cli("--docs", "handbook", "write").returncode, 0)
        self.assertTrue((self.root / "handbook/INDEX.md").exists())

    def test_unknown_command_rejected(self):
        self.assertEqual(self.run_cli("bogus").returncode, 2)


class RepoContentTests(unittest.TestCase):
    """The shipped skill folder itself must stay consistent."""

    skill = SCRIPT.parent.parent

    def test_skill_md_frontmatter(self):
        m = docs_index.frontmatter((self.skill / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(m["name"], "docs-1")
        self.assertTrue(m["description"])

    def test_template_has_every_required_field_and_passes_the_parser(self):
        m = docs_index.frontmatter((self.skill / "templates" / "doc.md").read_text(encoding="utf-8"))
        for k in docs_index.REQUIRED:
            self.assertIn(k, m)

    def test_template_becomes_a_valid_doc_once_filled_in(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            text = (self.skill / "templates" / "doc.md").read_text(encoding="utf-8")
            text = text.replace("<Title>", "T").replace("<one line: what this doc answers, naming the specifics a "
                                                        "reader would search for>", "S").replace("YYYY-MM-DD", "2026-01-01")
            (root / "docs" / "t.md").write_text(text, encoding="utf-8")
            env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull}
            kw = dict(cwd=root, capture_output=True, text=True, env=env)
            subprocess.run([sys.executable, "-I", str(SCRIPT), "write"], **kw)
            r = subprocess.run([sys.executable, "-I", str(SCRIPT), "check"], **kw)
            self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
