from __future__ import annotations

import struct
import unittest

from tools.clean_drm import (
    CountdownStub,
    apply_countdown_nops,
    find_countdown_stubs,
    parse_text_section,
)
from tests.test_guest_memory import build_synthetic_pe


class DrmCleanerTests(unittest.TestCase):
    def test_finds_and_nops_synthetic_countdown_stub(self) -> None:
        # Build synthetic .text with one valid 12-byte stub and regular code around it
        # dec dword ptr [0x01a61234] = ff 0d 34 12 a6 01
        # je +0x20                  = 0f 84 20 00 00 00
        stub = bytes.fromhex("ff0d3412a6010f8420000000")
        prefix = b"\x90\x90\x31\xc0"  # nop; nop; xor eax, eax
        suffix = b"\xb8\x01\x00\x00\x00\xc3"  # mov eax, 1; ret
        text_bytes = prefix + stub + suffix
        text_va = 0x00401000

        stubs = find_countdown_stubs(text_va, 0x1000, text_bytes)
        self.assertEqual(len(stubs), 1)
        s = stubs[0]
        self.assertEqual(s.va, text_va + len(prefix))
        self.assertEqual(s.offset_in_text, len(prefix))
        self.assertEqual(s.counter_address, 0x01A61234)
        self.assertEqual(s.jump_target, s.va + 12 + 0x20)
        self.assertEqual(s.original_hex, stub.hex())

        # Test nopping
        patched = apply_countdown_nops(text_bytes, stubs)
        self.assertEqual(len(patched), len(text_bytes))
        self.assertEqual(patched[: len(prefix)], prefix)
        self.assertEqual(patched[len(prefix) : len(prefix) + 12], b"\x90" * 12)
        self.assertEqual(patched[len(prefix) + 12 :], suffix)

    def test_rejects_misaligned_opcode_false_positive(self) -> None:
        # Construct synthetic code mimicking the false-positive cmp edi, 0xd followed by jne
        # 83 ff 0d = cmp edi, 0xd
        # 0f 85 a6 01 00 00 = jne +0x1a6
        false_positive = bytes.fromhex("83ff0d0f85a6010000")
        text_bytes = b"\x90" * 16 + false_positive + b"\x90" * 16
        text_va = 0x00401000

        stubs = find_countdown_stubs(text_va, 0x1000, text_bytes)
        self.assertEqual(len(stubs), 0)

    def test_parse_text_section_from_synthetic_pe(self) -> None:
        raw_text = b"\x90" * 256
        pe_image = build_synthetic_pe(
            sections=[
                (".text", 0x1000, len(raw_text), raw_text, 0x60000020),
            ],
            image_base=0x00400000,
        )
        base, va, roff, parsed_text = parse_text_section(pe_image)
        self.assertEqual(base, 0x00400000)
        self.assertEqual(va, 0x00401000)
        self.assertEqual(parsed_text, raw_text)


if __name__ == "__main__":
    unittest.main()

