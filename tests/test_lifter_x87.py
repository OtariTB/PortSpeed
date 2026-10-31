"""Unit and Integration Tests for x87 FPU Static Recompilation Lifter.

Validates translation of all x87 floating-point instructions (load/store, arithmetic,
comparisons, transcendentals, stack management, and status/control words) into C99
targeting runtime/cpu.h.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from tools.lift_catalog import InstructionLifter, FunctionLifter

WORKSPACE = Path(__file__).resolve().parent.parent


class TestLifterX87Unit(unittest.TestCase):
    """Synthetic unit tests for x87 FPU instruction lifting."""

    def setUp(self) -> None:
        self.cs = Cs(CS_ARCH_X86, CS_MODE_32)
        self.cs.detail = True
        self.lifter = InstructionLifter(self.cs)

    def _lift_bytes(self, code_hex: str, va: int = 0x00401000) -> list[str]:
        raw = bytes.fromhex(code_hex)
        ins = list(self.cs.disasm(raw, va))[0]
        return self.lifter.lift_instruction(ins)

    # ----------------------------------------------------------------------
    # FPU Loads & Constants
    # ----------------------------------------------------------------------
    def test_lift_fld_st_and_mem(self) -> None:
        # fld st(0): D9 C0
        self.assertIn("FPUSH(ST(0));", "\n".join(self._lift_bytes("d9c0")))

        # fld st(1): D9 C1
        self.assertIn("FPUSH(ST(1));", "\n".join(self._lift_bytes("d9c1")))

        # fld dword ptr [esp + 4]: D9 44 24 04
        self.assertIn("FPUSH((double)MRF32(c->esp+0x4u));", "\n".join(self._lift_bytes("d9442404")))

        # fld qword ptr [esp + 8]: DD 44 24 08
        self.assertIn("FPUSH(MRF64(c->esp+0x8u));", "\n".join(self._lift_bytes("dd442408")))

    def test_lift_fild_integer(self) -> None:
        # fild dword ptr [esp + 4]: DB 44 24 04
        self.assertIn("FPUSH((double)(int32_t)MR32(c->esp+0x4u));", "\n".join(self._lift_bytes("db442404")))

    def test_lift_fld_constants(self) -> None:
        # fldz: D9 EE
        self.assertIn("FPUSH(0.0);", "\n".join(self._lift_bytes("d9ee")))

        # fld1: D9 E8
        self.assertIn("FPUSH(1.0);", "\n".join(self._lift_bytes("d9e8")))

        # fldpi: D9 EB
        self.assertIn("FPUSH(3.14159265358979323846);", "\n".join(self._lift_bytes("d9eb")))

    # ----------------------------------------------------------------------
    # FPU Stores & Integer Conversions
    # ----------------------------------------------------------------------
    def test_lift_fst_fstp(self) -> None:
        # fstp dword ptr [esp + 4]: D9 5C 24 04
        stmts = self._lift_bytes("d95c2404")
        joined = "\n".join(stmts)
        self.assertIn("MRF32(c->esp+0x4u) = (float)ST(0);", joined)
        self.assertIn("FPOP();", joined)

        # fst qword ptr [esp + 8]: DD 54 24 08
        self.assertIn("MRF64(c->esp+0x8u) = ST(0);", "\n".join(self._lift_bytes("dd542408")))

    def test_lift_fistp_fisttp(self) -> None:
        # fistp dword ptr [esp + 4]: DB 5C 24 04
        stmts = self._lift_bytes("db5c2404")
        joined = "\n".join(stmts)
        self.assertIn("MR32(c->esp+0x4u) = x86_cvt_i32(x87_round(c->fcw, ST(0)));", joined)
        self.assertIn("FPOP();", joined)

        # fisttp dword ptr [esp + 4]: DB 4C 24 04
        tt_stmts = self._lift_bytes("db4c2404")
        self.assertIn("MR32(c->esp+0x4u) = x86_cvt_i32(trunc(ST(0)));", "\n".join(tt_stmts))

    # ----------------------------------------------------------------------
    # FPU Arithmetic
    # ----------------------------------------------------------------------
    def test_lift_fadd_faddp(self) -> None:
        # fadd dword ptr [esp + 4]: D8 44 24 04
        self.assertIn("X87R2(_d, _s, _d + _s)", "\n".join(self._lift_bytes("d8442404")))

        # faddp st(1), st(0): DE C1
        addp_stmts = self._lift_bytes("dec1")
        joined = "\n".join(addp_stmts)
        self.assertIn("ST(1) = X87R2(_d, _s, _d + _s);", joined)
        self.assertIn("FPOP();", joined)

    def test_lift_fsub_fsubr_fsubp(self) -> None:
        # fsub st(0), st(1): D8 E1
        self.assertIn("X87R2(_d, _s, _d - _s)", "\n".join(self._lift_bytes("d8e1")))

        # fsubr st(0), st(1): D8 E9
        self.assertIn("X87R2(_d, _s, _s - _d)", "\n".join(self._lift_bytes("d8e9")))

        # fsubp st(1), st(0): DE E9
        subp_stmts = self._lift_bytes("dee9")
        joined = "\n".join(subp_stmts)
        self.assertIn("ST(1) = X87R2(_d, _s, _d - _s);", joined)
        self.assertIn("FPOP();", joined)

    def test_lift_fmul_fmulp_fdiv(self) -> None:
        # fmul dword ptr [esp + 4]: D8 4C 24 04
        self.assertIn("X87R2(_d, _s, _d * _s)", "\n".join(self._lift_bytes("d84c2404")))

        # fmulp st(1), st(0): DE C9
        mulp_stmts = self._lift_bytes("dec9")
        joined = "\n".join(mulp_stmts)
        self.assertIn("ST(1) = X87R2(_d, _s, _d * _s);", joined)
        self.assertIn("FPOP();", joined)

        # fdiv st(0), st(1): D8 F1
        self.assertIn("X87R2(_d, _s, _d / _s)", "\n".join(self._lift_bytes("d8f1")))

    # ----------------------------------------------------------------------
    # FPU Comparisons
    # ----------------------------------------------------------------------
    def test_lift_fcom_fcomp_fcompp(self) -> None:
        # fcomp st(1): D8 D9
        comp_stmts = self._lift_bytes("d8d9")
        joined = "\n".join(comp_stmts)
        self.assertIn("fcompare(c, ST(0), ST(1));", joined)
        self.assertIn("FPOP();", joined)

        # fcompp: DE D9
        compp_stmts = self._lift_bytes("ded9")
        joined = "\n".join(compp_stmts)
        self.assertIn("fcompare(c, ST(0), ST(1));", joined)
        self.assertEqual(joined.count("FPOP();"), 2)

    def test_lift_fcomi_fcomip(self) -> None:
        # fcomi st(0), st(1): DB F1
        self.assertIn("FCOMI(ST(0), ST(1));", "\n".join(self._lift_bytes("dbf1")))

        # fcomip st(0), st(1): DF F1
        comip_stmts = self._lift_bytes("dff1")
        joined = "\n".join(comip_stmts)
        self.assertIn("FCOMI(ST(0), ST(1));", joined)
        self.assertIn("FPOP();", joined)

    # ----------------------------------------------------------------------
    # Transcendentals & Math
    # ----------------------------------------------------------------------
    def test_lift_transcendentals(self) -> None:
        # fabs: D9 E1
        self.assertIn("ST(0) = fabs(ST(0));", "\n".join(self._lift_bytes("d9e1")))

        # fchs: D9 E0
        self.assertIn("ST(0) = -ST(0);", "\n".join(self._lift_bytes("d9e0")))

        # fsqrt: D9 FA
        self.assertIn("X87R(x87_r1(_a, sqrt(_a)))", "\n".join(self._lift_bytes("d9fa")))

        # fsin: D9 FE
        self.assertIn("ST(0) = sin(ST(0));", "\n".join(self._lift_bytes("d9fe")))

        # fcos: D9 FF
        self.assertIn("ST(0) = cos(ST(0));", "\n".join(self._lift_bytes("d9ff")))

        # fsincos: D9 FB
        sincos_stmts = self._lift_bytes("d9fb")
        joined = "\n".join(sincos_stmts)
        self.assertIn("FPUSH(cos(ST(0)));", joined)
        self.assertIn("ST(1) = sin(ST(1));", joined)

    # ----------------------------------------------------------------------
    # Stack Operations & Control Words
    # ----------------------------------------------------------------------
    def test_lift_fxch(self) -> None:
        # fxch st(1): D9 C9
        self.assertIn("double _t = ST(0); ST(0) = ST(1); ST(1) = _t;", "\n".join(self._lift_bytes("d9c9")))

    def test_lift_control_and_status_words(self) -> None:
        # fnstsw ax: DF E0
        self.assertIn("c->eax = (c->eax & 0xffff0000u) | (uint32_t)fsw_get(c);", "\n".join(self._lift_bytes("dfe0")))

        # fnstcw [esp + 4]: D9 7C 24 04
        self.assertIn("MR16(c->esp+0x4u) = c->fcw;", "\n".join(self._lift_bytes("d97c2404")))

        # fldcw [esp + 4]: D9 6C 24 04
        self.assertIn("c->fcw = MR16(c->esp+0x4u);", "\n".join(self._lift_bytes("d96c2404")))

    def test_lift_fcmov(self) -> None:
        # fcmove st(0), st(1): DA C9
        self.assertIn("if (c->zf) ST(0) = ST(1);", "\n".join(self._lift_bytes("dac9")))


class TestLifterX87Integration(unittest.TestCase):
    """Integration test lifting real x87 functions from nfs.exe."""

    catalog_path = WORKSPACE / "research" / "local" / "phase1" / "catalog.json"

    def setUp(self) -> None:
        if not self.catalog_path.is_file():
            self.skipTest("Catalog not available")
        cfg_path = WORKSPACE / "config" / "local.json"
        if not cfg_path.is_file():
            self.skipTest("Config not available")
        cfg = json.loads(cfg_path.read_text())
        self.exe_path = Path(cfg["game_root"]) / "Need For Spped - Pro Street" / "nfs.exe"
        if not self.exe_path.is_file():
            self.skipTest("Game executable not available")

        self.raw_exe = self.exe_path.read_bytes()
        self.catalog = json.loads(self.catalog_path.read_text())
        self.flifter = FunctionLifter(self.raw_exe, self.catalog)

    def test_lift_real_x87_function(self) -> None:
        # Search for a function containing fld and fstp in the first 500 functions
        cs = Cs(CS_ARCH_X86, CS_MODE_32)
        target_entry = None
        for f in self.catalog["functions"][:500]:
            b0 = f["blocks"][0]
            code = self.flifter.read_bytes(b0[0], b0[1] - b0[0])
            has_fld = any(i.mnemonic == "fld" for i in cs.disasm(code, b0[0]))
            if has_fld:
                target_entry = f["address"]
                break

        self.assertIsNotNone(target_entry, "Should find at least one x87 function in catalog")
        c_code = self.flifter.lift_function(target_entry)
        self.assertIn(f"void sub_{target_entry:08x}(CPU *c)", c_code)
        self.assertIn("FPUSH", c_code)


if __name__ == "__main__":
    unittest.main()
