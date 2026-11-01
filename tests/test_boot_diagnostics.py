"""Unit and Integration Tests for ProStreet Authentic Startup Diagnostics."""
from __future__ import annotations

import unittest
from pathlib import Path

from tools.boot_diagnostics import run_initializer_diagnostics
from tools.build_win32_shims import EXE_PATH

WORKSPACE = Path(__file__).resolve().parent.parent


class TestBootDiagnostics(unittest.TestCase):
    """Validates the authentic startup diagnostics and constructor execution."""

    def test_constructors_through_280_pass_with_d3dx_shims(self):
        """Verifies that Constructor #274 advances past D3DXMatrixTranspose and D3DXVec3Transform."""
        res = run_initializer_diagnostics(max_constructors=280)
        self.assertEqual(res["total_table_slots"], 2811)
        self.assertEqual(res["total_non_null_constructors"], 280)
        self.assertEqual(res["completed_count"], 280)
        self.assertEqual(res["status"], "PASS")
        self.assertIsNone(res["first_failure"])


if __name__ == "__main__":
    unittest.main()
