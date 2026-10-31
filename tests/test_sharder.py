"""Tests for Code Sharder and Master Dispatch Table Generator (Step 2.4)."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.generate_shards import (
    generate_fntab_header,
    generate_fntab_source,
    generate_shards,
    DISPATCH_TEXT_BASE,
    DISPATCH_TEXT_SIZE,
)
from tools.lift_catalog import FunctionLifter


class TestSharderUnit(unittest.TestCase):
    """Unit tests for dispatch table generation and sharding logic."""

    def setUp(self) -> None:
        self.sample_funcs = [
            {"address": 0x00401000, "blocks": [[0x00401000, 0x00401005, [], True]]},
            {"address": 0x00402000, "blocks": [[0x00402000, 0x00402010, [], True]]},
            {"address": 0x00968100, "blocks": [[0x00968100, 0x00968120, [], True]]}, # Outside text
            {"address": 0x01ba1000, "blocks": [[0x01ba1000, 0x01ba1020, [], True]]}, # SecuROM bridge
        ]

    def test_generate_fntab_header(self) -> None:
        header = generate_fntab_header(self.sample_funcs)
        self.assertIn("#ifndef PROSTREET_FNTAB_H", header)
        self.assertIn("#define PROSTREET_FNTAB_H", header)
        self.assertIn('void sub_00401000(CPU *c);', header)
        self.assertIn('void sub_00402000(CPU *c);', header)
        self.assertIn('void sub_00968100(CPU *c);', header)
        self.assertIn('void sub_01ba1000(CPU *c);', header)
        self.assertIn('void fntab_init(void);', header)
        self.assertIn('void dispatch_indirect(struct CPU *c, uint32_t addr);', header)
        self.assertIn('void dispatch_tail(struct CPU *c);', header)

    def test_generate_fntab_source(self) -> None:
        src = generate_fntab_source(self.sample_funcs, chunk_size=2)
        self.assertIn('guest_fn_t g_dtab[DISPATCH_TEXT_SIZE];', src)
        self.assertIn('fntab_init_chunk_0', src)
        # Direct dispatch slots
        self.assertIn('g_dtab[0x00000000u] = sub_00401000;', src)
        self.assertIn('g_dtab[0x00001000u] = sub_00402000;', src)
        self.assertIn('void fntab_init(void)', src)
        # Secondary indirect dispatch for non-text functions
        self.assertIn('void dispatch_indirect(struct CPU *c, uint32_t addr)', src)
        self.assertIn('case 0x00968100u: sub_00968100(c); return;', src)
        self.assertIn('case 0x01ba1000u: sub_01ba1000(c); return;', src)
        self.assertIn('void dispatch_tail(struct CPU *c)', src)

    def test_generate_shards_synthetic(self) -> None:
        synthetic_exe = bytearray(0x200000)
        # Place a ret (0xC3) at 0x00401000, 0x00402000, 0x00403000, 0x00404000
        # In nfs.exe, VA 0x401000 maps to offset 0x1000
        synthetic_exe[0x1000] = 0xC3
        synthetic_exe[0x2000] = 0xC3
        synthetic_exe[0x3000] = 0xC3
        synthetic_exe[0x4000] = 0xC3

        cat = {
            "image_base": 0x400000,
            "code_start": 0x401000,
            "code_end": 0x967000,
            "summary": {"total_basic_blocks": 4},
            "functions": [
                {"address": 0x00401000, "blocks": [[0x00401000, 0x00401001, [], True]]},
                {"address": 0x00402000, "blocks": [[0x00402000, 0x00402001, [], True]]},
                {"address": 0x00403000, "blocks": [[0x00403000, 0x00403001, [], True]]},
                {"address": 0x00404000, "blocks": [[0x00404000, 0x00404001, [], True]]},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir)
            manifest = generate_shards(
                catalog=cat,
                raw_exe=bytes(synthetic_exe),
                out_dir=out_path,
                num_shards=2,
            )

            self.assertEqual(manifest["total_functions"], 4)
            self.assertEqual(manifest["num_shards"], 2)
            self.assertTrue((out_path / "fntab.h").is_file())
            self.assertTrue((out_path / "fntab.c").is_file())
            self.assertTrue((out_path / "shard_0000.c").is_file())
            self.assertTrue((out_path / "shard_0001.c").is_file())
            self.assertTrue((out_path / "manifest.json").is_file())

            # Verify shard contents
            shard0 = (out_path / "shard_0000.c").read_text()
            self.assertIn("#define PROSTREET_LREGS 1", shard0)
            self.assertIn('void sub_00401000(CPU *c)', shard0)
            self.assertIn('void sub_00402000(CPU *c)', shard0)

            shard1 = (out_path / "shard_0001.c").read_text()
            self.assertIn('void sub_00403000(CPU *c)', shard1)
            self.assertIn('void sub_00404000(CPU *c)', shard1)


class TestSharderIntegration(unittest.TestCase):
    """Integration tests verifying sharding on real nfs.exe catalog slices."""

    def setUp(self) -> None:
        workspace = Path(__file__).resolve().parent.parent
        self.catalog_path = workspace / "research" / "local" / "phase1" / "catalog.json"
        if not self.catalog_path.is_file():
            self.skipTest("Catalog not available")

        cfg_path = workspace / "config" / "local.json"
        if not cfg_path.is_file():
            self.skipTest("Config not available")

        cfg = json.loads(cfg_path.read_text())
        self.exe_path = Path(cfg["game_root"]) / "Need For Spped - Pro Street" / "nfs.exe"
        if not self.exe_path.is_file():
            self.skipTest("nfs.exe not found")

        self.raw_exe = self.exe_path.read_bytes()
        self.catalog = json.loads(self.catalog_path.read_text())

    def test_generate_shards_catalog_slice(self) -> None:
        # Test sharding a slice of 20 real functions into 4 shards
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir)
            manifest = generate_shards(
                catalog=self.catalog,
                raw_exe=self.raw_exe,
                out_dir=out_path,
                num_shards=4,
                max_functions=20,
            )

            self.assertEqual(manifest["total_functions"], 20)
            self.assertEqual(manifest["num_shards"], 4)
            self.assertEqual(len(manifest["shards"]), 4)

            # Check each shard has 5 functions
            for s in manifest["shards"]:
                self.assertEqual(s["function_count"], 5)
                shard_file = out_path / s["filename"]
                self.assertTrue(shard_file.is_file())
                content = shard_file.read_text()
                self.assertIn("#define PROSTREET_LREGS 1", content)
                self.assertIn('LR_ENTER;', content)


if __name__ == "__main__":
    unittest.main()

