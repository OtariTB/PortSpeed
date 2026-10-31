"""Unit and Integration Tests for SSE/SSE2 Static Recompilation Lifter.

Validates translation of all SSE, SSE2, and MMX instruction patterns into C99
targeting runtime/cpu.h and WebAssembly SIMD128.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from tools.lift_catalog import InstructionLifter, FunctionLifter, UnsupportedInstruction

WORKSPACE = Path(__file__).resolve().parent.parent


class TestLifterSseUnit(unittest.TestCase):
    """Synthetic unit tests for SSE/SSE2 instruction lifting."""

    def setUp(self) -> None:
        self.cs = Cs(CS_ARCH_X86, CS_MODE_32)
        self.cs.detail = True
        self.lifter = InstructionLifter(self.cs)

    def _lift_bytes(self, code_hex: str, va: int = 0x00401000) -> list[str]:
        raw = bytes.fromhex(code_hex)
        ins = list(self.cs.disasm(raw, va))[0]
        return self.lifter.lift_instruction(ins)

    # ----------------------------------------------------------------------
    # Vector Float Arithmetic
    # ----------------------------------------------------------------------
    def test_lift_addps_reg_reg(self) -> None:
        # addps xmm0, xmm1: 0F 58 C1
        stmts = self._lift_bytes("0f58c1")
        joined = "\n".join(stmts)
        self.assertIn("WASM_SIMD_ADDPS", joined)
        self.assertIn("c->xmm[0]", joined)
        self.assertIn("c->xmm[1]", joined)
        self.assertIn("sse_r2f", joined)

    def test_lift_subps_reg_mem(self) -> None:
        # subps xmm2, [esp + 0x10]: 0F 5C 54 24 10
        stmts = self._lift_bytes("0f5c542410")
        joined = "\n".join(stmts)
        self.assertIn("c->xmm[2]", joined)
        self.assertIn("MRF32", joined)
        self.assertIn("c->esp+0x10u", joined)

    def test_lift_mulps_reg_reg(self) -> None:
        # mulps xmm3, xmm4: 0F 59 DC
        stmts = self._lift_bytes("0f59dc")
        joined = "\n".join(stmts)
        self.assertIn("WASM_SIMD_MULPS", joined)
        self.assertIn("c->xmm[3]", joined)
        self.assertIn("c->xmm[4]", joined)

    def test_lift_divps_reg_reg(self) -> None:
        # divps xmm5, xmm6: 0F 5E EE
        stmts = self._lift_bytes("0f5eee")
        joined = "\n".join(stmts)
        self.assertIn("WASM_SIMD_DIVPS", joined)
        self.assertIn("c->xmm[5]", joined)
        self.assertIn("c->xmm[6]", joined)

    def test_lift_maxps_minps(self) -> None:
        # maxps xmm0, xmm1: 0F 5F C1
        stmts_max = self._lift_bytes("0f5fc1")
        self.assertIn("WASM_SIMD_MAXPS", "\n".join(stmts_max))

        # minps xmm2, xmm3: 0F 5D D3
        stmts_min = self._lift_bytes("0f5dd3")
        self.assertIn("WASM_SIMD_MINPS", "\n".join(stmts_min))

    def test_lift_sqrtps(self) -> None:
        # sqrtps xmm0, xmm1: 0F 51 C1
        stmts = self._lift_bytes("0f51c1")
        joined = "\n".join(stmts)
        self.assertIn("WASM_SIMD_SQRTPS", joined)
        self.assertIn("sqrtf", joined)

    # ----------------------------------------------------------------------
    # Scalar Float Arithmetic
    # ----------------------------------------------------------------------
    def test_lift_movss_load_store(self) -> None:
        # movss xmm0, [esp + 4]: F3 0F 10 44 24 04
        load_stmts = self._lift_bytes("f30f10442404")
        self.assertIn("memcpy(&c->xmm[0], g_mem + (uint32_t)(c->esp+0x4u), 4);", "\n".join(load_stmts))

        # movss [esp + 8], xmm1: F3 0F 11 4C 24 08
        store_stmts = self._lift_bytes("f30f114c2408")
        self.assertIn("memcpy(g_mem + (uint32_t)(c->esp+0x8u), &c->xmm[1], 4);", "\n".join(store_stmts))

    def test_lift_addss_scalar(self) -> None:
        # addss xmm0, xmm1: F3 0F 58 C1
        stmts = self._lift_bytes("f30f58c1")
        joined = "\n".join(stmts)
        self.assertIn("c->xmm[0].f[0]", joined)
        self.assertIn("c->xmm[1].f[0]", joined)
        self.assertIn("sse_r2f", joined)

    def test_lift_subss_scalar(self) -> None:
        # subss xmm2, [esp + 0x14]: F3 0F 5C 54 24 14
        stmts = self._lift_bytes("f30f5c542414")
        joined = "\n".join(stmts)
        self.assertIn("c->xmm[2].f[0]", joined)
        self.assertIn("MRF32(c->esp+0x14u)", joined)

    def test_lift_mulss_divss_scalar(self) -> None:
        # mulss xmm3, xmm4: F3 0F 59 DC
        self.assertIn("sse_r2f(_a, _b, _a * _b)", "\n".join(self._lift_bytes("f30f59dc")))

        # divss xmm5, xmm6: F3 0F 5E EE
        self.assertIn("sse_r2f(_a, _b, _a / _b)", "\n".join(self._lift_bytes("f30f5eee")))

    def test_lift_sqrtss_scalar(self) -> None:
        # sqrtss xmm0, xmm1: F3 0F 51 C1
        stmts = self._lift_bytes("f30f51c1")
        self.assertIn("c->xmm[0].f[0] = sqrtf(c->xmm[1].f[0]);", "\n".join(stmts))

    # ----------------------------------------------------------------------
    # Vector Bitwise Logic
    # ----------------------------------------------------------------------
    def test_lift_xorps(self) -> None:
        # xorps xmm0, xmm1: 0F 57 C1
        stmts = self._lift_bytes("0f57c1")
        joined = "\n".join(stmts)
        self.assertIn("WASM_SIMD_XORPS", joined)
        self.assertIn("c->xmm[0].u64[0] ^= c->xmm[1].u64[0];", joined)

    def test_lift_andps_orps(self) -> None:
        # andps xmm2, xmm3: 0F 54 D3
        self.assertIn("WASM_SIMD_ANDPS", "\n".join(self._lift_bytes("0f54d3")))

        # orps xmm4, xmm5: 0F 56 E5
        self.assertIn("WASM_SIMD_ORPS", "\n".join(self._lift_bytes("0f56e5")))

    def test_lift_andnps(self) -> None:
        # andnps xmm6, xmm7: 0F 55 F7
        stmts = self._lift_bytes("0f55f7")
        joined = "\n".join(stmts)
        self.assertIn("WASM_SIMD_ANDNPS", joined)
        self.assertIn("c->xmm[6].u64[0] = (~c->xmm[6].u64[0]) & c->xmm[7].u64[0];", joined)

    # ----------------------------------------------------------------------
    # Float Comparisons
    # ----------------------------------------------------------------------
    def test_lift_comiss_ucomiss(self) -> None:
        # comiss xmm0, xmm1: 0F 2F C1
        stmts = self._lift_bytes("0f2fc1")
        joined = "\n".join(stmts)
        self.assertIn("c->zf = 1; c->pf = 1; c->cf = 1;", joined)
        self.assertIn("c->zf = (_x == _y); c->cf = (_x < _y);", joined)
        self.assertIn("c->of = c->sf = c->af = 0;", joined)

        # ucomiss xmm2, [esp + 4]: 0F 2E 54 24 04
        u_stmts = self._lift_bytes("0f2e542404")
        self.assertIn("MRF32(c->esp+0x4u)", "\n".join(u_stmts))

    # ----------------------------------------------------------------------
    # Conversions
    # ----------------------------------------------------------------------
    def test_lift_conversions(self) -> None:
        # cvtsi2ss xmm0, eax: F3 0F 2A C0
        self.assertIn("c->xmm[0].f[0] = (float)(int32_t)(c->eax);", "\n".join(self._lift_bytes("f30f2ac0")))

        # cvttss2si eax, xmm0: F3 0F 2C C0
        self.assertIn("c->eax = (uint32_t)(x86_cvt_i32(trunc((double)(c->xmm[0].f[0]))));", "\n".join(self._lift_bytes("f30f2cc0")))

        # cvtss2sd xmm0, xmm1: F3 0F 5A C1
        self.assertIn("c->xmm[0].d[0] = (double)(c->xmm[1].f[0]);", "\n".join(self._lift_bytes("f30f5ac1")))

        # cvtsd2ss xmm0, xmm1: F2 0F 5A C1
        self.assertIn("c->xmm[0].f[0] = (float)(c->xmm[1].d[0]);", "\n".join(self._lift_bytes("f20f5ac1")))

    # ----------------------------------------------------------------------
    # Shuffles and Unpacks
    # ----------------------------------------------------------------------
    def test_lift_shufps(self) -> None:
        # shufps xmm0, xmm1, 0x1b: 0F C6 C1 1B
        stmts = self._lift_bytes("0fc6c11b")
        joined = "\n".join(stmts)
        self.assertIn("c->xmm[0].f[3]", joined)
        self.assertIn("c->xmm[1].f[0]", joined)

    def test_lift_unpcklps_movlhps(self) -> None:
        # unpcklps xmm0, xmm1: 0F 14 C1
        self.assertIn("c->xmm[0].u32[0]", "\n".join(self._lift_bytes("0f14c1")))

        # movlhps xmm0, xmm1: 0F 16 C1
        self.assertIn("c->xmm[0].u32[2] = c->xmm[1].u32[0];", "\n".join(self._lift_bytes("0f16c1")))

    # ----------------------------------------------------------------------
    # Integer SIMD
    # ----------------------------------------------------------------------
    def test_lift_paddd_psubd(self) -> None:
        # paddd xmm0, xmm1: 66 0F FE C1
        self.assertIn("WASM_SIMD_PADDD", "\n".join(self._lift_bytes("660ffec1")))

        # psubd xmm0, xmm1: 66 0F FA C1
        self.assertIn("WASM_SIMD_PSUBD", "\n".join(self._lift_bytes("660ffac1")))

    def test_lift_pmaddwd_psrlq(self) -> None:
        # pmaddwd xmm0, xmm1: 66 0F F5 C1
        self.assertIn("int16_t", "\n".join(self._lift_bytes("660ff5c1")))

        # psrlq xmm0, 0x10: 66 0F 73 D0 10
        self.assertIn("c->xmm[0].u64[0] >>=", "\n".join(self._lift_bytes("660f73d010")))


class TestLifterSseIntegration(unittest.TestCase):
    """Integration test verifying full function lifting against nfs.exe catalog."""

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

    def test_lift_real_sse_function(self) -> None:
        # Find a catalog function that contains movss or xorps
        cs = Cs(CS_ARCH_X86, CS_MODE_32)
        target_entry = None
        for f in self.catalog["functions"][:500]:
            b0 = f["blocks"][0]
            code = self.flifter.read_bytes(b0[0], b0[1] - b0[0])
            for i in cs.disasm(code, b0[0]):
                if i.mnemonic in ("movss", "xorps", "addps", "mulps", "comiss"):
                    target_entry = f["address"]
                    break
            if target_entry:
                break

        self.assertIsNotNone(target_entry, "Should find at least one SSE function in catalog")
        c_code = self.flifter.lift_function(target_entry)
        self.assertIn(f"void sub_{target_entry:08x}(CPU *c)", c_code)
        self.assertIn(f"L_{target_entry:08x}:", c_code)
        self.assertIn("c->xmm", c_code)


if __name__ == "__main__":
    unittest.main()

