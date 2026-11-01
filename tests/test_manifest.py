"""
Unit tests for tools/generate_manifest.py and tools/serve.py (Step 7.2).
"""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.generate_manifest import (
    scan_game_directory,
    build_manifest_dict,
    verify_critical_assets,
    CRITICAL_CHECK_FILES,
    OPFS_BLOCK_SIZE,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT_DIR / "web" / "public"


class TestManifestGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_directory_and_block_calculation(self):
        # Create synthetic files
        (self.temp_dir / "dir1").mkdir()
        f1 = self.temp_dir / "dir1" / "file1.bin"
        f1.write_bytes(b"A" * 500)  # 500 bytes -> 1 block

        f2 = self.temp_dir / "file2.big"
        f2.write_bytes(b"B" * (OPFS_BLOCK_SIZE + 100))  # 1 MiB + 100 bytes -> 2 blocks

        files, total_bytes, total_blocks = scan_game_directory(self.temp_dir)
        self.assertEqual(len(files), 2)
        self.assertEqual(total_bytes, 500 + OPFS_BLOCK_SIZE + 100)
        self.assertEqual(total_blocks, 3)

        entries = {f["path"].lower(): f for f in files}
        self.assertIn("dir1/file1.bin", entries)
        self.assertEqual(entries["dir1/file1.bin"]["blocks"], 1)
        self.assertIn("file2.big", entries)
        self.assertEqual(entries["file2.big"]["blocks"], 2)

    def test_verify_critical_assets_detection(self):
        # Incomplete file list
        files = [{"path": "OTHER/FILE.DAT"}]
        missing = verify_critical_assets(files)
        self.assertEqual(len(missing), len(CRITICAL_CHECK_FILES))

        # Complete file list
        files_complete = [{"path": f} for f in CRITICAL_CHECK_FILES]
        missing_none = verify_critical_assets(files_complete)
        self.assertEqual(len(missing_none), 0)

    def test_generated_public_manifest_validity(self):
        manifest_path = PUBLIC_DIR / "data-manifest.json"
        self.assertTrue(manifest_path.is_file(), "web/public/data-manifest.json must exist")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("format"), "prostreet-opfs-v1")
        self.assertGreater(data.get("totalFiles", 0), 3000)
        self.assertGreater(data.get("totalBytes", 0), 5 * 1024**3)
        self.assertGreater(data.get("totalBlocks", 0), 5000)

        # Check critical bundles cataloged
        files = data.get("files", [])
        missing = verify_critical_assets(files)
        self.assertEqual(len(missing), 0, f"Missing critical assets in data-manifest.json: {missing}")

    def test_build_manifest_dict_schema(self):
        files = [{"path": "GLOBAL/GLOBALB.LZC", "size": 100, "mtime": 12345, "isDir": False, "blocks": 1}]
        m = build_manifest_dict(files, 100, 1, Path("C:/FakeGame"))
        self.assertEqual(m["totalFiles"], 1)
        self.assertEqual(m["totalBytes"], 100)
        self.assertEqual(m["totalBlocks"], 1)
        self.assertEqual(m["blockSize"], OPFS_BLOCK_SIZE)
        self.assertEqual(len(m["files"]), 1)


if __name__ == "__main__":
    unittest.main()

