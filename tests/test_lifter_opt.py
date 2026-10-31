"""Tests for Lifter Optimization: Dead-Flag Elimination (FLAGABI) & Local Register Promotion (LREGS)."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

from tools.lift_catalog import (
    InstructionLifter,
    FunctionLifter,
    get_insn_flag_def_use,
    compute_flag_liveness,
    F_CF,
    F_PF,
    F_AF,
    F_ZF,
    F_SF,
    F_OF,
    F_ALL,
)


class TestFlagAbiUnit(unittest.TestCase):
    """Unit tests for instruction-level flag def/use and backward CFG dataflow."""

    def setUp(self) -> None:
        self.cs = Cs(CS_ARCH_X86, CS_MODE_32)
        self.cs.detail = True

    def _disasm_one(self, code_hex: str):
        raw = bytes.fromhex(code_hex)
        return next(self.cs.disasm(raw, 0x00401000))

    def test_flag_def_use_arithmetic_and_logic(self) -> None:
        # add eax, ebx (01 d8)
        ins = self._disasm_one("01d8")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, 0)

        # sub eax, 5 (83 e8 05)
        ins = self._disasm_one("83e805")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, 0)

        # adc eax, edx (11 d0)
        ins = self._disasm_one("11d0")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, F_CF)

        # sbb ecx, 1 (83 d9 01)
        ins = self._disasm_one("83d901")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, F_CF)

        # inc eax (40) - preserves CF
        ins = self._disasm_one("40")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL & ~F_CF)
        self.assertEqual(u, 0)

        # dec ecx (49) - preserves CF
        ins = self._disasm_one("49")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL & ~F_CF)
        self.assertEqual(u, 0)

        # and eax, ebx (21 d8)
        ins = self._disasm_one("21d8")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, 0)

        # cmp eax, 10 (83 f8 0a)
        ins = self._disasm_one("83f80a")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, 0)

        # test eax, eax (85 c0)
        ins = self._disasm_one("85c0")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, 0)

    def test_flag_def_use_conditions_and_branches(self) -> None:
        # je (74 05)
        ins = self._disasm_one("7405")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_ZF)

        # jne (75 05)
        ins = self._disasm_one("7505")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_ZF)

        # jb / jc (72 05)
        ins = self._disasm_one("7205")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_CF)

        # ja (77 05)
        ins = self._disasm_one("7705")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_CF | F_ZF)

        # jl (7c 05)
        ins = self._disasm_one("7c05")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_SF | F_OF)

        # jg (7f 05)
        ins = self._disasm_one("7f05")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_ZF | F_SF | F_OF)

        # sete al (0f 94 c0)
        ins = self._disasm_one("0f94c0")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_ZF)

        # cmovbe eax, ebx (0f 46 c3)
        ins = self._disasm_one("0f46c3")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_CF | F_ZF)

    def test_flag_def_use_calls_and_stack(self) -> None:
        # call (e8 00 00 00 00)
        ins = self._disasm_one("e800000000")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, 0)

        # pushfd (9c)
        ins = self._disasm_one("9c")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, 0)
        self.assertEqual(u, F_ALL)

        # popfd (9d)
        ins = self._disasm_one("9d")
        d, u = get_insn_flag_def_use(ins)
        self.assertEqual(d, F_ALL)
        self.assertEqual(u, 0)

    def test_compute_flag_liveness_straight_line(self) -> None:
        # Straight line block:
        # 0x00401000: add eax, 1  (05 01 00 00 00)
        # 0x00401005: cmp eax, 10 (83 f8 0a)
        # 0x00401008: je 0x00401010 (74 06)
        # 0x0040100a: ret (c3)
        code = bytes.fromhex("050100000083f80a7406c3")
        insns = list(self.cs.disasm(code, 0x00401000))
        blocks = [(0x00401000, 0x0040100B, [], True)]
        insns_by_block = {0x00401000: insns}

        live_after = compute_flag_liveness(blocks, insns_by_block, returns_flags=False)

        # ret has live_after = 0
        self.assertEqual(live_after[0x0040100A], 0)
        # je uses ZF, but its live_after is 0 (exit)
        self.assertEqual(live_after[0x00401008], 0)
        # cmp defines all flags, preceding je uses ZF -> live_after must be F_ZF!
        self.assertEqual(live_after[0x00401005], F_ZF)
        # add defines all flags, cmp overwrites all flags -> live_after of add must be 0 (DEAD FLAGS!)
        self.assertEqual(live_after[0x00401000], 0)

    def test_compute_flag_liveness_branching_cfg(self) -> None:
        # CFG with conditional branch:
        # B0: 0x00401000..0x00401008: cmp eax, 0; je B2; succs = [0x00401008, 0x00401010]
        # B1: 0x00401008..0x00401009: ret; succs = [] (exit)
        # B2: 0x00401010..0x00401011: ret; succs = [] (exit)
        code_b0 = bytes.fromhex("83f8007406") # cmp eax, 0; je 0x0040100a
        code_b1 = bytes.fromhex("c3")         # ret
        code_b2 = bytes.fromhex("c3")         # ret

        insns_b0 = list(self.cs.disasm(code_b0, 0x00401000))
        insns_b1 = list(self.cs.disasm(code_b1, 0x00401008))
        insns_b2 = list(self.cs.disasm(code_b2, 0x00401010))

        blocks = [
            (0x00401000, 0x00401005, [0x00401008, 0x00401010], False),
            (0x00401008, 0x00401009, [], True),
            (0x00401010, 0x00401011, [], True),
        ]
        insns_by_block = {
            0x00401000: insns_b0,
            0x00401008: insns_b1,
            0x00401010: insns_b2,
        }

        live_after = compute_flag_liveness(blocks, insns_by_block)
        # cmp before je must have F_ZF
        self.assertEqual(live_after[0x00401000], F_ZF)


class TestLregsUnit(unittest.TestCase):
    """Unit tests for Local Register Promotion (LREGS) code generation."""

    def setUp(self) -> None:
        self.cs = Cs(CS_ARCH_X86, CS_MODE_32)
        self.cs.detail = True
        self.lifter_noreg = InstructionLifter(self.cs, use_rg=False)
        self.lifter_rg = InstructionLifter(self.cs, use_rg=True)

    def _disasm_one(self, code_hex: str):
        return next(self.cs.disasm(bytes.fromhex(code_hex), 0x00401000))

    def test_register_access_uses_rg_macro_when_enabled(self) -> None:
        # mov eax, ebx (89 d8)
        ins = self._disasm_one("89d8")

        stmts_no = self.lifter_noreg.lift_instruction(ins)
        self.assertIn("c->eax = (uint32_t)(c->ebx);", stmts_no[0])

        stmts_rg = self.lifter_rg.lift_instruction(ins)
        self.assertIn("RG_(eax) = (uint32_t)(RG_(ebx));", stmts_rg[0])

    def test_memory_ea_uses_rg_macro(self) -> None:
        # mov eax, [esp + ecx*4 + 0x10] (8b 44 8c 10)
        ins = self._disasm_one("8b448c10")

        stmts_rg = self.lifter_rg.lift_instruction(ins)
        self.assertIn("RG_(eax)", stmts_rg[0])
        self.assertIn("RG_(esp)", stmts_rg[0])
        self.assertIn("RG_(ecx)*4", stmts_rg[0])

    def test_flag_macros_use_cur_fmask(self) -> None:
        # add eax, 1 (83 c0 01)
        ins = self._disasm_one("83c001")

        self.lifter_rg.cur_fmask = 0x00
        stmts_dead = self.lifter_rg.lift_instruction(ins)
        self.assertIn("FLAGS_ADD_M", stmts_dead[0])
        self.assertIn("0x00u", stmts_dead[0])

        self.lifter_rg.cur_fmask = F_ZF
        stmts_zf = self.lifter_rg.lift_instruction(ins)
        self.assertIn("FLAGS_ADD_M", stmts_zf[0])
        self.assertIn("0x08u", stmts_zf[0])


class TestLifterOptIntegration(unittest.TestCase):
    """Integration test verifying full function recompilation with FLAGABI and LREGS."""

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
        self.flifter = FunctionLifter(self.raw_exe, self.catalog)

    def test_lift_function_with_lregs_and_flagabi(self) -> None:
        # Find a non-trivial function in catalog with multiple blocks
        target = None
        for f in self.catalog["functions"][:200]:
            if len(f["blocks"]) >= 3:
                target = f["address"]
                break

        self.assertIsNotNone(target, "Should find multi-block function in catalog")

        c_code = self.flifter.lift_function(target, enable_lregs=True, enable_flagabi=True)

        # Check signature and LREGS prologue
        self.assertIn(f"void sub_{target:08x}(CPU *c) {{", c_code)
        self.assertIn("LR_ENTER;", c_code)

        # Check that RG_ is used
        self.assertTrue("RG_(" in c_code or "return;" in c_code)

        # Check that LR_STORE is emitted before returns or terminal points
        self.assertIn("LR_STORE;", c_code)

    def test_lift_function_with_lregs_false(self) -> None:
        target = self.catalog["functions"][0]["address"]
        c_code = self.flifter.lift_function(target, enable_lregs=False, enable_flagabi=True)

        self.assertNotIn("LR_ENTER;", c_code)
        self.assertIn(f"void sub_{target:08x}(CPU *c) {{", c_code)


if __name__ == "__main__":
    unittest.main()
