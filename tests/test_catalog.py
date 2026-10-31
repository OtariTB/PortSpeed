"""Unit and Integration Tests for NFS ProStreet Function Catalog and CFG Recovery.

Validates the master control-flow graph (CFG) database, basic block splitting,
switch table recovery, schema normalization, and integration against nfs.exe.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
import unittest

from tools.build_catalog import CatalogBuilder, normalize_catalog
from tools.clean_drm import EXPECTED_NFS_EXE_SHA256

WORKSPACE = Path(__file__).resolve().parent.parent


class TestCatalogUnit(unittest.TestCase):
    """Unit tests for catalog schema validation, normalization, and CFG extraction."""

    def test_normalize_catalog_valid(self) -> None:
        raw = {
            "image_base": 0x400000,
            "code_start": 0x401000,
            "code_end": 0x500000,
            "functions": [
                {
                    "address": 0x401000,
                    "blocks": [[0x401000, 0x401010, [0x401020], 0], [0x401020, 0x401030, [], 1]],
                    "calls_to": [0x402000, 0x600000],
                    "jump_targets": [0x401020],
                },
                {
                    "address": 0x402000,
                    "blocks": [[0x402000, 0x402005, [], 1]],
                    "is_thunk": True,
                },
            ],
        }
        norm = normalize_catalog(raw)
        self.assertEqual(norm["schema"], "nfsu-catalog-bridge-v1")
        self.assertEqual(len(norm["functions"]), 2)
        self.assertEqual(norm["functions"][0]["address"], 0x401000)
        self.assertEqual(norm["functions"][1]["address"], 0x402000)
        self.assertTrue(norm["functions"][1]["is_thunk"])
        self.assertEqual(norm["unresolved_calls"], [0x600000])

    def test_normalize_catalog_invalid_bounds(self) -> None:
        raw = {
            "image_base": 0x400000,
            "code_start": 0x500000,
            "code_end": 0x401000,  # inverted bounds
            "functions": [],
        }
        with self.assertRaises(ValueError):
            normalize_catalog(raw)

    def test_normalize_catalog_duplicate_function(self) -> None:
        raw = {
            "image_base": 0x400000,
            "code_start": 0x401000,
            "code_end": 0x500000,
            "functions": [
                {"address": 0x401000, "blocks": [[0x401000, 0x401010, [], 1]]},
                {"address": 0x401000, "blocks": [[0x401000, 0x401010, [], 1]]},
            ],
        }
        with self.assertRaises(ValueError):
            normalize_catalog(raw)

    def test_normalize_catalog_missing_entry_block(self) -> None:
        raw = {
            "image_base": 0x400000,
            "code_start": 0x401000,
            "code_end": 0x500000,
            "functions": [
                {"address": 0x401000, "blocks": [[0x401005, 0x401010, [], 1]]},
            ],
        }
        with self.assertRaises(ValueError):
            normalize_catalog(raw)

    def test_normalize_catalog_invalid_block_bounds(self) -> None:
        raw = {
            "image_base": 0x400000,
            "code_start": 0x401000,
            "code_end": 0x500000,
            "functions": [
                {"address": 0x401000, "blocks": [[0x401010, 0x401000, [], 1]]},  # b_start > b_end
            ],
        }
        with self.assertRaises(ValueError):
            normalize_catalog(raw)

    def test_in_code_ranges(self) -> None:
        # Dummy builder structure to test range logic
        t_data = {"trampolines": []}
        # Create minimal 1024-byte PE header
        raw = bytearray(0x2000)
        # DOS header
        raw[0:2] = b"MZ"
        raw[0x3C:0x40] = struct.pack("<I", 0x80)
        pe_off = 0x80
        raw[pe_off : pe_off + 4] = b"PE\x00\x00"
        raw[pe_off + 4 : pe_off + 6] = b"\x4c\x01"  # x86 machine
        raw[pe_off + 6 : pe_off + 8] = struct.pack("<H", 1)  # 1 section
        raw[pe_off + 20 : pe_off + 22] = struct.pack("<H", 224)  # opt header size
        # Optional header: magic = 0x10B (PE32), EntryPoint = 0x1000, ImageBase = 0x400000
        raw[pe_off + 24 : pe_off + 26] = b"\x0b\x01"
        raw[pe_off + 24 + 16 : pe_off + 24 + 20] = struct.pack("<I", 0x1000)
        raw[pe_off + 24 + 28 : pe_off + 24 + 32] = struct.pack("<I", 0x00400000)
        # Section table at pe_off + 24 + 224 = 0x178
        sec = pe_off + 24 + 224
        raw[sec : sec + 8] = b".text\x00\x00\x00"
        raw[sec + 8 : sec + 12] = struct.pack("<I", 0x1000)   # virt size 0x1000
        raw[sec + 12 : sec + 16] = struct.pack("<I", 0x1000)  # RVA 0x1000
        raw[sec + 16 : sec + 20] = struct.pack("<I", 0x1000)  # raw size 0x1000
        raw[sec + 20 : sec + 24] = struct.pack("<I", 0x1000)  # raw offset 0x1000

        builder = CatalogBuilder(bytes(raw), t_data)
        self.assertTrue(builder.in_code(0x00401000))
        self.assertTrue(builder.in_code(0x00401FFF))
        self.assertFalse(builder.in_code(0x00400FFF))
        self.assertFalse(builder.in_code(0x00402000))


class TestCatalogIntegration(unittest.TestCase):
    """Integration tests verifying the generated catalog for nfs.exe."""

    catalog_path = WORKSPACE / "research" / "local" / "phase1" / "catalog.json"
    meta_path = WORKSPACE / "research" / "local" / "phase1" / "catalog.metadata.json"

    def setUp(self) -> None:
        if not self.catalog_path.is_file():
            self.skipTest(f"Catalog file not yet generated: {self.catalog_path}")

    def test_catalog_file_integrity(self) -> None:
        size = self.catalog_path.stat().st_size
        self.assertGreater(size, 10_000_000, "Catalog JSON should be >= 10MB")

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)

        self.assertEqual(cat["schema"], "nfsu-catalog-bridge-v1")
        self.assertEqual(cat["image_base"], 0x400000)
        self.assertEqual(cat["binary_identity"], f"verified-sha256:{EXPECTED_NFS_EXE_SHA256}")

    def test_catalog_function_and_block_counts(self) -> None:
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)

        num_funcs = len(cat["functions"])
        self.assertGreaterEqual(num_funcs, 30_000, "Expected >= 30,000 recovered functions")

        total_blocks = sum(len(f["blocks"]) for f in cat["functions"])
        self.assertGreaterEqual(total_blocks, 200_000, "Expected >= 200,000 basic blocks")

        # Unresolved calls should be minimal (< 20)
        self.assertLess(len(cat["unresolved_calls"]), 20, "Expected < 20 unresolved external calls")

    def test_critical_entry_points_present(self) -> None:
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)

        func_addrs = {f["address"] for f in cat["functions"]}
        # PE Entry Point
        self.assertIn(0x00828C25, func_addrs, "PE entry point 0x00828c25 must be cataloged")
        # Main entry
        self.assertIn(0x004AFEE0, func_addrs, "Main function 0x004afee0 must be cataloged")

    def test_trampoline_targets_present(self) -> None:
        t_path = WORKSPACE / "research" / "local" / "phase1" / "securom_trampolines.json"
        if not t_path.is_file():
            self.skipTest(f"Missing trampoline file: {t_path}")

        t_data = json.loads(t_path.read_text())
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            cat = json.load(f)

        func_addrs = {f["address"] for f in cat["functions"]}

        # Check that high-confidence MSVC trampoline targets in .securom and .text are present
        found = 0
        total_targets = 0
        for t in t_data.get("trampolines", []):
            target = t["target_va"]
            total_targets += 1
            if target in func_addrs:
                found += 1

        recovery_rate = found / total_targets if total_targets else 0
        self.assertGreaterEqual(recovery_rate, 0.90, f"Expected >= 90% trampoline targets cataloged (got {recovery_rate:.1%})")

    def test_metadata_file_consistency(self) -> None:
        if not self.meta_path.is_file():
            self.skipTest("Missing catalog metadata file")

        meta = json.loads(self.meta_path.read_text())
        summary = meta["summary"]
        self.assertEqual(summary["schema"], "nfsu-catalog-bridge-v1")
        self.assertEqual(meta["image_sha256"], EXPECTED_NFS_EXE_SHA256)
        self.assertGreaterEqual(summary["total_functions"], 30_000)
        self.assertGreaterEqual(summary["total_basic_blocks"], 200_000)


if __name__ == "__main__":
    unittest.main()
