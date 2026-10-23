"""Platform-independent tests for store and launcher logic. Run: python -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CLAUDOU_HOME"] = tempfile.mkdtemp()

from claudou import launcher, store  # noqa: E402


class CommandTests(unittest.TestCase):
    def test_default_has_no_flag(self):
        self.assertEqual(launcher.build_command("C:\\Claude\\claude.exe", None), "C:\\Claude\\claude.exe")

    def test_profile_flag_quotes_spaces(self):
        cmd = launcher.build_command("C:\\Claude\\claude.exe", "D:\\My Data\\work")
        self.assertIn('"--user-data-dir=D:\\My Data\\work"', cmd)


class MatchTests(unittest.TestCase):
    spec = [("default", None), ("work", "D:\\data\\work"), ("work_2", "D:\\data\\work_2")]

    def test_matches_exact_dir_only(self):
        procs = [(1, ["claude.exe"]), (2, ["claude.exe", "--user-data-dir=D:\\data\\work_2"]),
                 (3, ["claude.exe", "--user-data-dir=d:/data/WORK"])]
        self.assertEqual(launcher.match_profiles(procs, self.spec), {"default": 1, "work_2": 2, "work": 3})

    def test_unknown_dir_matches_nothing(self):
        self.assertEqual(launcher.match_profiles([(9, ["c", "--user-data-dir=X:\\other"])], self.spec), {})


class StoreTests(unittest.TestCase):
    def setUp(self):
        os.environ["CLAUDOU_HOME"] = tempfile.mkdtemp()
        self.s = store.ProfileStore()

    def test_default_profile_created(self):
        self.assertEqual([p.id for p in self.s.profiles], ["default"])

    def test_slug_and_unique_ids(self):
        a, b = self.s.create("Công ty A", "#000000"), self.s.create("Cong ty A", "#000000")
        self.assertEqual((a.id, b.id), ("cong_ty_a", "cong_ty_a_2"))

    def test_roundtrip_and_schema(self):
        self.s.create("Work", "#e8590c", data_dir=str(Path(os.environ["CLAUDOU_HOME"]) / "ext"))
        again = store.ProfileStore()
        w = again.get("work")
        self.assertEqual(w.data_dir, str(Path(os.environ["CLAUDOU_HOME"]) / "ext"))
        self.assertFalse(again.is_owned_folder(w))

    def test_delete_rules(self):
        p = self.s.create("Tmp", "#000000")
        self.assertFalse(self.s.can_delete(self.s.get("default"), {}))
        self.assertFalse(self.s.can_delete(p, {"tmp": 1}))
        self.s.delete(p, {})
        self.assertIsNone(self.s.get("tmp"))
        self.assertFalse(p.dir.exists())

    def test_external_folder_is_kept_on_delete(self):
        ext = Path(tempfile.mkdtemp())
        p = self.s.create("Ext", "#000000", data_dir=str(ext))
        self.s.delete(p, {})
        self.assertTrue(ext.exists())


if __name__ == "__main__":
    unittest.main()
