"""
Unit tests for tools/build_wasm.py WebAssembly compilation orchestrator.
"""

import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.build_wasm import (
    discover_sources,
    compute_header_hash,
    compute_file_hash,
    get_compiler_flags,
    get_linker_flags,
    build_synthetic_wasm_binary,
    emit_build_manifest,
    detect_toolchain,
    ToolchainInfo,
    EXPECTED_SHARD_COUNT,
    RUNTIME_C_FILES,
    GUEST_MEMORY_SIZE,
    INITIAL_MEMORY_BYTES,
    MAX_MEMORY_BYTES,
)


class TestBuildWasm(unittest.TestCase):
    def test_discover_sources(self):
        shards, fntab, runtime_files = discover_sources()
        self.assertEqual(len(shards), EXPECTED_SHARD_COUNT)
        self.assertEqual(fntab.name, "fntab.c")
        self.assertEqual(len(runtime_files), len(RUNTIME_C_FILES))
        for rf in runtime_files:
            self.assertTrue(rf.is_file(), f"Missing runtime file: {rf}")

    def test_header_and_file_hashing(self):
        h_hash = compute_header_hash()
        self.assertIsInstance(h_hash, str)
        self.assertGreater(len(h_hash), 0)

        shards, _, _ = discover_sources()
        f_hash = compute_file_hash(shards[0], h_hash, "-O3 -msimd128")
        self.assertEqual(len(f_hash), 64)  # SHA-256 hex length

    def test_compiler_flags_wasi(self):
        tc = ToolchainInfo("wasi-sdk", Path("clang"), None, "18.1.0")
        flags = get_compiler_flags(tc, "-O3")
        self.assertIn("-O3", flags)
        self.assertIn("-msimd128", flags)
        self.assertIn("-mbulk-memory", flags)
        self.assertIn("-fno-delete-null-pointer-checks", flags)
        self.assertIn("-DPROSTREET_PORT=1", flags)
        self.assertIn("-DPROSTREET_LREGS=1", flags)
        self.assertIn("-D__wasm__=1", flags)
        self.assertIn("--target=wasm32-wasip1-threads", flags)

    def test_compiler_flags_emscripten(self):
        tc = ToolchainInfo("emscripten", Path("emcc"), None, "3.1.50")
        flags = get_compiler_flags(tc, "-O2")
        self.assertIn("-O2", flags)
        self.assertIn("-sUSE_PTHREADS=1", flags)
        self.assertIn("-DPROSTREET_PORT=1", flags)

    def test_linker_flags_wasi(self):
        tc = ToolchainInfo("wasi-sdk", Path("clang"), None, "18.1.0")
        out_wasm = Path("out.wasm")
        flags = get_linker_flags(tc, "-O3", out_wasm)
        self.assertIn(f"-Wl,--initial-memory={INITIAL_MEMORY_BYTES}", flags)
        self.assertIn(f"-Wl,--max-memory={MAX_MEMORY_BYTES}", flags)
        self.assertIn(f"-Wl,--global-base={GUEST_MEMORY_SIZE}", flags)
        self.assertIn("-Wl,--import-memory", flags)
        self.assertIn("-Wl,--export-memory", flags)
        self.assertIn("-Wl,--shared-memory", flags)

    def test_synthetic_wasm_binary_validity(self):
        wasm = build_synthetic_wasm_binary()
        self.assertGreater(len(wasm), 50)
        self.assertEqual(wasm[:4], b"\x00asm")
        self.assertEqual(wasm[4:8], b"\x01\x00\x00\x00")

        # Verify exported names present in byte stream
        self.assertIn(b"memory", wasm)
        self.assertIn(b"prostreet_main", wasm)
        self.assertIn(b"prostreet_get_guest_memory", wasm)
        self.assertIn(b"prostreet_tick", wasm)

    def test_emit_manifest(self):
        tmp_json = Path("tmp_manifest_test.json")
        try:
            m = emit_build_manifest(tmp_json, 123456, "-O3", "test-toolchain", 32)
            self.assertEqual(m["pages"], INITIAL_MEMORY_BYTES // 65536)
            self.assertEqual(m["maxPages"], MAX_MEMORY_BYTES // 65536)
            self.assertEqual(m["guestEnd"], GUEST_MEMORY_SIZE)
            self.assertEqual(m["shards"], 32)
            self.assertEqual(m["functions"], 31995)
            self.assertTrue(tmp_json.is_file())
        finally:
            if tmp_json.is_file():
                tmp_json.unlink()

    def test_cli_check_and_dry_run(self):
        res = subprocess.run(
            [sys.executable, "tools/build_wasm.py", "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Sanity Check OK", res.stdout)


if __name__ == "__main__":
    unittest.main()

