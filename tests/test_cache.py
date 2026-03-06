import shutil
import unittest
from pathlib import Path

from core.cache import DiskCache


class CacheTests(unittest.TestCase):
    def test_disk_cache_hit_and_miss(self):
        root = Path("tests/.tmp_cache")
        shutil.rmtree(root, ignore_errors=True)
        cache = DiskCache(root)
        calls = {"n": 0}

        def _compute():
            calls["n"] += 1
            return {"x": 1}

        v1 = cache.get_or_compute("pivot", "k1", _compute)
        v2 = cache.get_or_compute("pivot", "k1", _compute)
        self.assertEqual({"x": 1}, v1)
        self.assertEqual({"x": 1}, v2)
        self.assertEqual(1, calls["n"])
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

