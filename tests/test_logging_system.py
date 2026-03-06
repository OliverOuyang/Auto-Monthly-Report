import json
import shutil
import unittest
from pathlib import Path

from core.logging_utils import log_event, setup_logger


class LoggingTests(unittest.TestCase):
    def test_jsonl_log_written(self):
        root = Path("tests/.tmp_logs")
        shutil.rmtree(root, ignore_errors=True)
        logger = setup_logger(root, run_id="r001")
        log_event(logger, "indicator_start", indicator_id="abc", step="build")

        log_file = root / "logs" / "run.jsonl"
        self.assertTrue(log_file.exists())
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertGreaterEqual(len(lines), 1)
        row = json.loads(lines[-1])
        self.assertEqual("indicator_start", row["event"])
        self.assertEqual("abc", row["indicator_id"])
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

