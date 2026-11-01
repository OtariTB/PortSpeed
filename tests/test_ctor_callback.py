"""Integration tests for constructor callback 0x006f8d60 and __ehvec_ctor dispatch.

Verifies:
1. tools/lift_ctor_callback.py generates AssemblyScript and compiles ctor_callback.wasm via asc.
2. Direct execution of lifted sub_006f8d60 preserves stack and mutates object fields at +0x40, +0x44, +0x48.
3. Indirect invocation via __ehvec_ctor (sub_00401000) using function pointer 0x006f8d60.
4. Static initializer loop sub_0095b650 completes all 150 constructor calls without NULL dispatch traps.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest

WORKSPACE = Path(__file__).resolve().parent.parent


class TestCtorCallbackIntegration(unittest.TestCase):
    """End-to-end integration tests for lifted constructor callback 0x006f8d60 in WebAssembly."""

    def test_lift_and_execute_ctor_callback_wasm(self):
        """Runs tools/lift_ctor_callback.py and tests/test_ctor_callback_wasm.mjs."""
        # 1. Run lifting and compilation tool
        lift_script = WORKSPACE / "tools" / "lift_ctor_callback.py"
        self.assertTrue(lift_script.is_file(), f"lift script must exist at {lift_script}")

        res_lift = subprocess.run(
            ["python", str(lift_script)],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(WORKSPACE),
        )
        self.assertEqual(
            res_lift.returncode,
            0,
            f"tools/lift_ctor_callback.py failed ({res_lift.returncode}):\n{res_lift.stdout}\n{res_lift.stderr}",
        )

        # 2. Run Node.js WebAssembly integration harness
        test_script = WORKSPACE / "tests" / "test_ctor_callback_wasm.mjs"
        self.assertTrue(test_script.is_file(), f"test script must exist at {test_script}")

        res_node = subprocess.run(
            ["node", str(test_script)],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(WORKSPACE),
        )
        self.assertEqual(
            res_node.returncode,
            0,
            f"tests/test_ctor_callback_wasm.mjs failed ({res_node.returncode}):\n{res_node.stdout}\n{res_node.stderr}",
        )
        self.assertIn("ALL CONSTRUCTOR CALLBACK WASM INTEGRATION TESTS PASSED!", res_node.stdout)


if __name__ == "__main__":
    unittest.main()
