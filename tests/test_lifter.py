from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiments.recomp.lift_x86 import (
    LifterError,
    emit_assemblyscript_module,
    emit_c_module,
    ensure_safe_paths,
    lift_function_bytes,
)


class LifterSyntheticTests(unittest.TestCase):
    def test_lifts_synthetic_branching_x86_function_to_c_and_as(self) -> None:
        # Synthetic x86 function at 0x00401000:
        #   8b 44 24 04       mov eax, dword ptr [esp + 4]
        #   83 f8 00          cmp eax, 0
        #   74 05             je 0x0040100e
        #   83 c0 2a          add eax, 42
        #   eb 02             jmp 0x00401010
        #   33 c0             xor eax, eax
        #   c3                ret
        code = bytes.fromhex("8b44240483f800740583c02aeb0233c0c3")
        fn = lift_function_bytes("synth_add42", code, 0x00401000)

        self.assertEqual(fn.start_va, 0x00401000)
        self.assertEqual(fn.end_va, 0x00401010)
        self.assertEqual(len(fn.instructions), 7)
        self.assertEqual(fn.block_leaders, (0x00401000, 0x00401009, 0x0040100E, 0x00401010))

        c_src = emit_c_module([fn])
        self.assertIn("void synth_add42(X86Cpu *c)", c_src)
        self.assertIn("if (c->zf != 0u) goto L_0040100e;", c_src)
        self.assertIn("goto L_00401010;", c_src)

        as_src = emit_assemblyscript_module([fn])
        self.assertIn("export function synth_add42(): u32", as_src)
        self.assertIn("case 0x0040100e:", as_src)

    def test_rejects_empty_and_truncated_instructions(self) -> None:
        with self.assertRaises(LifterError):
            lift_function_bytes("empty_fn", b"", 0x00401000)

        # Truncated mov eax, [esp + 4] missing displacement byte
        with self.assertRaises(LifterError):
            lift_function_bytes("truncated_modrm", bytes.fromhex("8b4424"), 0x00401000)

        # Truncated near jump 0xE9 missing 4-byte displacement
        with self.assertRaises(LifterError):
            lift_function_bytes("truncated_jmp", bytes.fromhex("e90102"), 0x00401000)

    def test_rejects_out_of_bounds_branch_and_missing_ret(self) -> None:
        # Short jump outside function bounds
        with self.assertRaises(LifterError):
            lift_function_bytes("oob_branch", bytes.fromhex("eb20c3"), 0x00401000)

        # Function falling off end without ret or jmp
        with self.assertRaises(LifterError):
            lift_function_bytes("no_ret", bytes.fromhex("8b442404"), 0x00401000)

    def test_rejects_unsupported_opcode(self) -> None:
        # 0xCD 0x80 (int 0x80) is intentionally unsupported
        with self.assertRaises(LifterError):
            lift_function_bytes("bad_opcode", bytes.fromhex("cd80c3"), 0x00401000)

    def test_output_path_protection_refuses_overlapping_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = root / "workspace"
            game = root / "game"
            ext = root / "external_out"
            ws.mkdir()
            game.mkdir()
            ext.mkdir()
            exe = game / "nfs.exe"
            exe.write_bytes(b"MZ")

            # Output inside workspace must be rejected
            with self.assertRaises(LifterError):
                ensure_safe_paths(exe, ws / "out", ws, game)

            # Output inside protected game directory must be rejected
            with self.assertRaises(LifterError):
                ensure_safe_paths(exe, game / "out", ws, game)

            # Output parent of workspace or game must be rejected
            with self.assertRaises(LifterError):
                ensure_safe_paths(exe, root, ws, game)

            # Disjoint external directory must be accepted
            safe = ensure_safe_paths(exe, ext / "phase3", ws, game)
            self.assertEqual(safe, (ext / "phase3").resolve())

    def test_lifts_phase3a_huff_and_cip_opcodes(self) -> None:
        # Synthetic x86 function exercising Phase 3A opcodes:
        #   55                push ebp
        #   8b ec             mov ebp, esp
        #   8b 45 08          mov eax, [ebp + 8]
        #   8b 4d 0c          mov ecx, [ebp + 12]
        #   d3 e0             shl eax, cl
        #   1b c9             sbb ecx, ecx
        #   2b c1             sub eax, ecx
        #   85 c0             test eax, eax
        #   7e 02             jle 0x00402015
        #   f7 d8             neg eax
        #   5d                pop ebp
        #   c3                ret
        code = bytes.fromhex("558bec8b45088b4d0cd3e01bc92bc185c07e02f7d85dc3")
        fn = lift_function_bytes("synth_phase3a_ops", code, 0x00402000)
        self.assertEqual(len(fn.instructions), 12)
        c_src = emit_c_module([fn])
        self.assertIn("shl32_flags(c, c->eax, get_lo8(c->ecx))", c_src)
        self.assertIn("sbb32_flags(c, c->ecx, c->ecx)", c_src)
        self.assertIn("neg32_flags(c, c->eax)", c_src)
        as_src = emit_assemblyscript_module([fn])
        self.assertIn("export function synth_phase3a_ops(): u32", as_src)


if __name__ == "__main__":
    unittest.main()
