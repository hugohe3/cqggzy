import json
import tempfile
import unittest
from pathlib import Path

import step2_scrape_details as step2


class Step2ProgressTests(unittest.TestCase):
    def setUp(self):
        self._old_progress_file = step2.PROGRESS_FILE
        self._tmp_dir = tempfile.TemporaryDirectory()
        step2.PROGRESS_FILE = str(Path(self._tmp_dir.name) / "progress.json")

    def tearDown(self):
        step2.PROGRESS_FILE = self._old_progress_file
        self._tmp_dir.cleanup()

    def test_load_progress_returns_default_when_file_is_corrupted(self):
        Path(step2.PROGRESS_FILE).write_text("{bad json", encoding="utf-8")
        progress = step2.load_progress()
        self.assertEqual([], progress["completed"])
        self.assertEqual({}, progress["failed"])
        self.assertEqual([], progress["details"])

    def test_apply_scrape_result_error_wont_mark_completed(self):
        all_details = []
        detail_index = {}
        completed_ids = set()
        progress = {"completed": [], "failed": {}, "details": []}
        record = {
            "记录ID": "rid-1",
            "标题": "标题1",
            "发布日期": "2026-01-01",
            "业务类型": "工程",
            "区域": "渝北区",
            "详情链接": "https://example.com/1",
        }

        has_error = step2.apply_scrape_result(
            orig_idx=0,
            record=record,
            detail={"错误": "HTTP 500"},
            all_details=all_details,
            detail_index=detail_index,
            completed_ids=completed_ids,
            progress=progress,
        )

        self.assertTrue(has_error)
        self.assertNotIn("rid-1", completed_ids)
        self.assertEqual([], progress["completed"])
        self.assertEqual("HTTP 500", progress["failed"]["rid-1"])
        self.assertEqual([], all_details)

    def test_apply_scrape_result_success_marks_completed_and_replace(self):
        all_details = [{"序号": 1, "标题": "旧标题", "详情链接": "https://example.com/1"}]
        detail_index = {"https://example.com/1": 0}
        completed_ids = set()
        progress = {"completed": [], "failed": {"rid-1": "旧错误"}, "details": []}
        record = {
            "记录ID": "rid-1",
            "标题": "新标题",
            "发布日期": "2026-01-01",
            "业务类型": "工程",
            "区域": "渝北区",
            "详情链接": "https://example.com/1",
        }

        has_error = step2.apply_scrape_result(
            orig_idx=0,
            record=record,
            detail={"项目编号": "X001"},
            all_details=all_details,
            detail_index=detail_index,
            completed_ids=completed_ids,
            progress=progress,
        )

        self.assertFalse(has_error)
        self.assertIn("rid-1", completed_ids)
        self.assertEqual(["rid-1"], progress["completed"])
        self.assertNotIn("rid-1", progress["failed"])
        self.assertEqual("新标题", all_details[0]["标题"])
        self.assertEqual("X001", all_details[0]["项目编号"])

    def test_save_progress_writes_valid_json(self):
        progress = {
            "completed": ["a", "a", "b"],
            "failed": {"x": "err"},
            "details": [{"序号": 1}],
        }
        step2.save_progress(progress)
        loaded = json.loads(Path(step2.PROGRESS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(["a", "b"], loaded["completed"])
        self.assertEqual({"x": "err"}, loaded["failed"])
        self.assertEqual([{"序号": 1}], loaded["details"])


if __name__ == "__main__":
    unittest.main()
