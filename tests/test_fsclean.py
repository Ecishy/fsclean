"""Tests for fsclean's core planner and CLI."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from fsclean.cli import main
from fsclean.core import parse_rules, plan_moves


class CoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def touch(self, name: str, content: bytes = b"x" * 10) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_plan_groups_by_category(self) -> None:
        self.touch("photo.jpg")
        self.touch("doc.pdf")
        moves, unknown = plan_moves(self.root)
        self.assertEqual(unknown, 0)
        self.assertEqual(
            {(m.src.name, m.category) for m in moves},
            {("photo.jpg", "images"), ("doc.pdf", "documents")},
        )

    def test_unknown_extension_left_in_place(self) -> None:
        self.touch("weird.zqx")
        moves, unknown = plan_moves(self.root)
        self.assertEqual(moves, [])
        self.assertEqual(unknown, 1)

    def test_hidden_files_skipped(self) -> None:
        self.touch(".env")
        moves, unknown = plan_moves(self.root)
        self.assertEqual((moves, unknown), ([], 0))

    def test_symlinks_skipped(self) -> None:
        real = self.touch("real.jpg")
        try:
            (self.root / "link.jpg").symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        moves, _ = plan_moves(self.root)
        self.assertEqual([m.src.name for m in moves], ["real.jpg"])

    def test_exclude_pattern(self) -> None:
        self.touch("a.jpg")
        self.touch("b.jpg")
        moves, _ = plan_moves(self.root, exclude=("b.jpg",))
        self.assertEqual([m.src.name for m in moves], ["a.jpg"])

    def test_custom_rule_overrides_builtin(self) -> None:
        self.touch("pic.jpg")
        moves, _ = plan_moves(self.root, rules=("jpg=pics",))
        self.assertEqual(moves[0].category, "pics")

    def test_dest_diverts_target(self) -> None:
        self.touch("doc.pdf")
        dest = self.root / "sorted"
        moves, _ = plan_moves(self.root, dest=dest)
        self.assertEqual(moves[0].dest, dest / "documents" / "doc.pdf")

    def test_case_insensitive_extension(self) -> None:
        self.touch("PHOTO.JPG")
        moves, _ = plan_moves(self.root)
        self.assertEqual(moves[0].category, "images")

    def test_parse_rules_valid_and_invalid(self) -> None:
        self.assertEqual(parse_rules(["log=logs", ".JPG=pics"]), {"log": "logs", "jpg": "pics"})
        for bad in ("bogus", "=logs", "log=", "log=a/b", "log=..", "log=."):
            with self.assertRaises(ValueError):
                parse_rules([bad])

    def test_missing_root_raises(self) -> None:
        with self.assertRaises(NotADirectoryError):
            plan_moves(self.root / "nope")


class CliTestCase(CoreTestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_dry_run_is_the_default(self) -> None:
        self.touch("a.jpg")
        code, out, _ = self.run_cli(str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertTrue((self.root / "a.jpg").exists())
        self.assertFalse((self.root / "images").exists())

    def test_apply_moves_files(self) -> None:
        self.touch("a.jpg")
        self.touch("b.pdf")
        code, out, _ = self.run_cli("--apply", str(self.root))
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "images" / "a.jpg").exists())
        self.assertTrue((self.root / "documents" / "b.pdf").exists())
        self.assertIn("Applied: 2 file(s) moved", out)

    def test_apply_handles_collision(self) -> None:
        (self.root / "images").mkdir()
        (self.root / "images" / "a.jpg").write_bytes(b"old")
        self.touch("a.jpg")
        code, _, _ = self.run_cli("--apply", str(self.root))
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "images" / "a.jpg").exists())
        self.assertTrue((self.root / "images" / "a (1).jpg").exists())

    def test_apply_with_dest(self) -> None:
        self.touch("a.jpg")
        code, _, _ = self.run_cli("--apply", "--dest", str(self.root / "sorted"), str(self.root))
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "sorted" / "images" / "a.jpg").exists())

    def test_unknown_files_reported(self) -> None:
        self.touch("weird.zqx")
        code, out, _ = self.run_cli(str(self.root))
        self.assertIn("unknown extension", out)
        self.assertTrue((self.root / "weird.zqx").exists())

    def test_bad_rule_exit_two(self) -> None:
        self.touch("a.jpg")
        code, _, err = self.run_cli("--rule", "bogus", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("invalid rule", err)

    def test_missing_dir_exit_two(self) -> None:
        code, _, err = self.run_cli(str(self.root / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)

    def test_non_recursive(self) -> None:
        nested = self.root / "sub"
        nested.mkdir()
        (nested / "deep.jpg").write_bytes(b"x")
        moves, _ = plan_moves(self.root)
        self.assertEqual(moves, [])


if __name__ == "__main__":
    unittest.main()
