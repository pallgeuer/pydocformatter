import re
import tempfile
import unittest
from pathlib import Path

from pydocformatter.utils import classify_file, collect_file_decisions


class TestUtils(unittest.TestCase):
    def test_classify_file_reasoning(self) -> None:
        include = re.compile(r"\.py$")
        exclude = re.compile(r"skip\.py$")

        accepted = classify_file("pkg/module.py", include, exclude)
        self.assertTrue(accepted.accepted)
        self.assertEqual(accepted.reason, "included")

        rejected_include = classify_file("pkg/module.txt", include, exclude)
        self.assertFalse(rejected_include.accepted)
        self.assertEqual(
            rejected_include.reason,
            "does not match the --include regular expression",
        )

        rejected_exclude = classify_file("pkg/skip.py", include, exclude)
        self.assertFalse(rejected_exclude.accepted)
        self.assertEqual(
            rejected_exclude.reason,
            "matches the --exclude regular expression",
        )

    def test_collect_file_decisions_is_deterministic(self) -> None:
        include = re.compile(r"\.py$")
        exclude = None

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "z_dir").mkdir()
            (root / "a_dir").mkdir()
            (root / "b.py").write_text("", encoding="utf-8")
            (root / "a.py").write_text("", encoding="utf-8")
            (root / "z_dir" / "c.py").write_text("", encoding="utf-8")
            (root / "a_dir" / "d.py").write_text("", encoding="utf-8")

            decisions = collect_file_decisions([str(root)], include, exclude)

        collected = [
            Path(decision.path).relative_to(root).as_posix() for decision in decisions
        ]
        self.assertEqual(collected, ["a.py", "b.py", "a_dir/d.py", "z_dir/c.py"])


if __name__ == "__main__":
    unittest.main()
