"""Targeted Regression Tests for SecuROM Trampoline Resolution in tools/lift_catalog.py.

Validates:
1. Resolved direct calls: remapped to confirmed target function and preserves PUSH32(ret_addr).
2. Resolved direct jumps: inter-function tail jumps remapped to confirmed target in DISPATCH_TAIL.
3. Missing targets: trampolines pointing to targets absent from the catalog are not redirected.
4. Unknown call targets: explicitly dispatched via DISPATCH_CALL, never silently skipped.
5. Unchanged normal calls: calls to confirmed non-trampoline functions remain direct sub_XXXX calls.
6. Chained trampolines: multi-hop trampoline links resolve iteratively to final target.
7. Authentic database loading: default initialization loads verified securom_trampolines.json.
"""
from __future__ import annotations

import struct
import unittest
from pathlib import Path
import sys

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from tools.lift_catalog import FunctionLifter


class TestSecuROMTrampolineResolution(unittest.TestCase):
    """Test suite validating SecuROM trampoline resolution in the static lifter."""

    def setUp(self) -> None:
        self.image_base = 0x00400000
        # Create a mock raw_exe buffer large enough to cover test addresses (e.g. 0x00401000..0x00403000)
        # In nfs.exe, va_to_offset is va - image_base
        self.raw_exe = bytearray(0x10000)

        # Mock catalog with confirmed functions
        self.confirmed_fn1 = 0x00500000
        self.confirmed_fn2 = 0x00600000
        self.test_caller_va = 0x00401000

        self.catalog = {
            "image_base": self.image_base,
            "code_start": 0x00401000,
            "code_end": 0x00967000,
            "functions": [
                {"address": self.test_caller_va, "blocks": [[self.test_caller_va, self.test_caller_va + 0x20, [], True]]},
                {"address": self.confirmed_fn1, "blocks": [[self.confirmed_fn1, self.confirmed_fn1 + 0x10, [], True]]},
                {"address": self.confirmed_fn2, "blocks": [[self.confirmed_fn2, self.confirmed_fn2 + 0x10, [], True]]},
            ],
        }

        # Mock trampoline mappings
        self.trampoline_site = 0x00401d20
        self.missing_target_site = 0x00401e00
        self.unconfirmed_target = 0x00777777
        self.chained_site1 = 0x00402100
        self.chained_site2 = 0x00402200

        self.trampoline_data = {
            "trampolines": [
                {"site_va": self.trampoline_site, "target_va": self.confirmed_fn1},
                {"site_va": self.missing_target_site, "target_va": self.unconfirmed_target},
                {"site_va": self.chained_site1, "target_va": self.chained_site2},
                {"site_va": self.chained_site2, "target_va": self.confirmed_fn2},
            ]
        }

        self.flifter = FunctionLifter(
            raw_exe=bytes(self.raw_exe),
            catalog=self.catalog,
            enable_lregs=True,
            enable_flagabi=False,
            trampoline_data=self.trampoline_data,
        )

    def _write_insns(self, va: int, code: bytes) -> None:
        """Write raw instructions into mock executable buffer at RVA."""
        offset = va - self.image_base
        self.raw_exe[offset : offset + len(code)] = code
        self.flifter.raw_exe = bytes(self.raw_exe)

    def test_resolved_direct_call(self) -> None:
        """A direct call to a SecuROM trampoline site must resolve to confirmed target."""
        va = self.test_caller_va
        rel = self.trampoline_site - (va + 5)
        # call trampoline_site; ret
        code = b"\xE8" + struct.pack("<i", rel) + b"\xC3"
        self._write_insns(va, code)

        c_code = self.flifter.lift_function(va, enable_lregs=True)

        # 1. Authentic return address must be pushed to guest stack
        self.assertIn(f"PUSH32(0x{va + 5:08x}u);", c_code)
        # 2. Must resolve through trampoline mapping to confirmed function
        self.assertIn(f"Resolved SecuROM trampoline call 0x{self.trampoline_site:08x} -> 0x{self.confirmed_fn1:08x}", c_code)
        self.assertIn(f"sub_{self.confirmed_fn1:08x}(c);", c_code)
        # 3. Must not call unmapped site
        self.assertNotIn(f"sub_{self.trampoline_site:08x}(c);", c_code)

    def test_resolved_direct_jmp(self) -> None:
        """An inter-function jump to a SecuROM trampoline site must resolve to confirmed target."""
        va = self.test_caller_va
        rel = self.trampoline_site - (va + 5)
        # jmp trampoline_site
        code = b"\xE9" + struct.pack("<i", rel)
        self._write_insns(va, code)

        c_code = self.flifter.lift_function(va, enable_lregs=True)

        # Must resolve to confirmed function in DISPATCH_TAIL
        self.assertIn(f"Resolved SecuROM trampoline jmp 0x{self.trampoline_site:08x} -> 0x{self.confirmed_fn1:08x}", c_code)
        self.assertIn(f"DISPATCH_TAIL(c, 0x{self.confirmed_fn1:08x}u);", c_code)
        self.assertNotIn(f"DISPATCH_TAIL(c, 0x{self.trampoline_site:08x}u);", c_code)

    def test_missing_target_not_redirected(self) -> None:
        """A trampoline whose target is absent from the catalog must NOT redirect."""
        va = self.test_caller_va
        rel = self.missing_target_site - (va + 5)
        code = b"\xE8" + struct.pack("<i", rel) + b"\xC3"
        self._write_insns(va, code)

        c_code = self.flifter.lift_function(va, enable_lregs=True)

        # Target 0x00777777 is unconfirmed in catalog, so redirect is aborted
        self.assertNotIn(f"sub_{self.unconfirmed_target:08x}(c);", c_code)
        self.assertNotIn(f"Resolved SecuROM trampoline", c_code)
        # Explicit fallback dispatch to original destination preserves execution
        self.assertIn(f"DISPATCH_CALL(c, 0x{self.missing_target_site:08x}u);", c_code)

    def test_unknown_call_target_dispatched_explicitly(self) -> None:
        """An unknown call destination must be explicitly dispatched via DISPATCH_CALL."""
        va = self.test_caller_va
        unknown_target = 0x00888888
        rel = unknown_target - (va + 5)
        code = b"\xE8" + struct.pack("<i", rel) + b"\xC3"
        self._write_insns(va, code)

        c_code = self.flifter.lift_function(va, enable_lregs=True)

        self.assertIn(f"DISPATCH_CALL(c, 0x{unknown_target:08x}u);", c_code)
        self.assertIn(f"PUSH32(0x{va + 5:08x}u);", c_code)

    def test_unchanged_normal_call(self) -> None:
        """Normal calls to confirmed catalog functions must remain direct without redirection."""
        va = self.test_caller_va
        rel = self.confirmed_fn2 - (va + 5)
        code = b"\xE8" + struct.pack("<i", rel) + b"\xC3"
        self._write_insns(va, code)

        c_code = self.flifter.lift_function(va, enable_lregs=True)

        self.assertIn(f"sub_{self.confirmed_fn2:08x}(c);", c_code)
        self.assertNotIn("Resolved SecuROM trampoline", c_code)
        self.assertIn(f"PUSH32(0x{va + 5:08x}u);", c_code)

    def test_chained_trampoline_resolution(self) -> None:
        """Chained trampolines (A -> B -> C) must resolve iteratively to final target."""
        va = self.test_caller_va
        rel = self.chained_site1 - (va + 5)
        code = b"\xE8" + struct.pack("<i", rel) + b"\xC3"
        self._write_insns(va, code)

        c_code = self.flifter.lift_function(va, enable_lregs=True)

        # Chained site 1 (0x00402100) -> site 2 (0x00402200) -> confirmed_fn2 (0x00600000)
        self.assertIn(f"sub_{self.confirmed_fn2:08x}(c);", c_code)
        self.assertIn(f"Resolved SecuROM trampoline call 0x{self.chained_site1:08x} -> 0x{self.confirmed_fn2:08x}", c_code)

    def test_authentic_database_loading(self) -> None:
        """Default initialization must load verified research/local/phase1/securom_trampolines.json."""
        default_lifter = FunctionLifter(
            raw_exe=b"\x00" * 0x1000,
            catalog=self.catalog,
            enable_lregs=False,
            enable_flagabi=False,
        )
        self.assertGreater(len(default_lifter.trampoline_map), 2000, "Should load all 2,153 trampolines from database")
        # Check known site from database (e.g. site 4201760 = 0x00401d20)
        self.assertIn(0x00401d20, default_lifter.trampoline_map)


if __name__ == "__main__":
    unittest.main()
