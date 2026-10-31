from __future__ import annotations

import json
from pathlib import Path
import struct
import unittest

from tools.guest_memory import (
    GuestMemory,
    MemoryLoaderError,
    PESection,
    parse_pe_sections,
    IMAGE_BASE,
    GUEST_MEMORY_LIMIT,
    HEAP_START,
    STACK_TOP,
)


def build_synthetic_pe(
    sections: list[tuple[str, int, int, bytes, int]],
    image_base: int = 0x00400000,
) -> bytes:
    """Build a minimal valid PE32 byte image with specified sections (name, rva, vsize, raw_data, flags)."""
    # DOS Header
    dos = bytearray(0x80)
    dos[:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, 0x80)

    # PE Signature
    pe_sig = b"PE\x00\x00"

    # COFF Header (20 bytes)
    machine = 0x014C
    num_sections = len(sections)
    time_date = 0
    sym_ptr = 0
    num_syms = 0
    opt_hdr_size = 224
    characteristics = 0x0102
    coff = struct.pack(
        "<HHIIIHH", machine, num_sections, time_date, sym_ptr, num_syms, opt_hdr_size, characteristics
    )

    # Optional Header PE32 (224 bytes)
    opt = bytearray(opt_hdr_size)
    opt[0:2] = struct.pack("<H", 0x010B)  # PE32
    struct.pack_into("<I", opt, 28, image_base)  # ImageBase
    struct.pack_into("<I", opt, 32, 0x1000)  # SectionAlignment
    struct.pack_into("<I", opt, 36, 0x200)  # FileAlignment

    hdr_end = 0x80 + len(pe_sig) + len(coff) + opt_hdr_size + num_sections * 40
    raw_start = (hdr_end + 0x1FF) & ~0x1FF

    sec_entries = bytearray()
    raw_blobs = bytearray(raw_start - hdr_end)

    cur_raw = raw_start
    for name, rva, vsize, raw_data, flags in sections:
        sec_name = name.encode("latin1")[:8].ljust(8, b"\x00")
        rsize = len(raw_data)
        sec_entries.extend(
            struct.pack(
                "<8sIIIIIIHHI",
                sec_name,
                vsize,
                rva,
                rsize,
                cur_raw if rsize > 0 else 0,
                0,
                0,
                0,
                0,
                flags,
            )
        )
        if rsize > 0:
            raw_blobs.extend(raw_data)
            aligned_rsize = (rsize + 0x1FF) & ~0x1FF
            raw_blobs.extend(b"\x00" * (aligned_rsize - rsize))
            cur_raw += aligned_rsize

    return bytes(dos + pe_sig + coff + opt + sec_entries + raw_blobs)


class GuestMemoryTests(unittest.TestCase):
    def test_loads_synthetic_pe_sections_with_data_and_bss(self) -> None:
        init_data = b"HelloGuestMemory1234"
        raw_pe = build_synthetic_pe(
            [
                (".text", 0x1000, 0x1000, b"\x90\xC3", 0x60000020),
                (".rdata", 0x2000, 0x1000, b"CONSTANTS", 0x40000040),
                (".data", 0x3000, 0x2000, init_data, 0xC0000040),  # vsize > rsize: has BSS
            ],
            image_base=0x00400000,
        )

        mem = GuestMemory(size=16 * 1024 * 1024)
        secs = mem.load_pe_sections(raw_pe, [".text", ".rdata", ".data"])

        self.assertEqual(len(secs), 3)
        self.assertEqual(mem.image_base, 0x00400000)

        # Check .text instruction
        self.assertEqual(mem.read_bytes(0x00401000, 2), b"\x90\xC3")

        # Check .rdata string
        self.assertEqual(mem.read_bytes(0x00402000, 9), b"CONSTANTS")

        # Check .data initialized portion
        self.assertEqual(mem.read_bytes(0x00403000, len(init_data)), init_data)

        # Check .data uninitialized BSS portion is explicitly zeroed
        bss_slice = mem.read_bytes(0x00403000 + len(init_data), 64)
        self.assertEqual(bss_slice, b"\x00" * 64)

        # Check read_u32 and write_u32
        mem.write_u32(0x00403100, 0xAABBCCDD)
        self.assertEqual(mem.read_u32(0x00403100), 0xAABBCCDD)

    def test_rejects_out_of_bounds_access(self) -> None:
        mem = GuestMemory(size=1 * 1024 * 1024)
        with self.assertRaises(MemoryLoaderError):
            mem.check_bounds(1024 * 1024 - 2, 4)

        with self.assertRaises(MemoryLoaderError):
            mem.read_u32(1024 * 1024)

        with self.assertRaises(MemoryLoaderError):
            mem.write_u32(1024 * 1024, 0x12345678)

    def test_rejects_corrupt_dos_and_pe_headers(self) -> None:
        with self.assertRaises(MemoryLoaderError):
            parse_pe_sections(b"NOT_MZ")

        bad_dos = bytearray(0x80)
        bad_dos[:2] = b"MZ"
        struct.pack_into("<I", bad_dos, 0x3C, 0x80)
        # Missing PE signature at 0x80
        with self.assertRaises(MemoryLoaderError):
            parse_pe_sections(bytes(bad_dos))

    def test_rejects_overlapping_sections(self) -> None:
        # Construct raw PE with overlapping virtual ranges
        raw_pe = build_synthetic_pe(
            [
                (".sec1", 0x1000, 0x2000, b"AAAA", 0x40000040),
                (".sec2", 0x2000, 0x1000, b"BBBB", 0x40000040),  # 0x1000 + 0x2000 = 0x3000 > 0x2000
            ]
        )
        with self.assertRaises(MemoryLoaderError):
            parse_pe_sections(raw_pe)

    def test_helper_reads_and_writes(self) -> None:
        mem = GuestMemory(size=4 * 1024 * 1024)
        mem.write_u8(0x00200000, 0xAB)
        self.assertEqual(mem.read_u8(0x00200000), 0xAB)

        mem.write_u16(0x00200002, 0x1234)
        self.assertEqual(mem.read_u16(0x00200002), 0x1234)

        mem.write_u64(0x00200010, 0x0123456789ABCDEF)
        self.assertEqual(mem.read_u64(0x00200010), 0x0123456789ABCDEF)

        # Floating point
        struct.pack_into("<f", mem.buffer, 0x00200020, 3.14159)
        self.assertAlmostEqual(mem.read_f32(0x00200020), 3.14159, places=5)

        struct.pack_into("<d", mem.buffer, 0x00200030, 2.718281828459)
        self.assertAlmostEqual(mem.read_f64(0x00200030), 2.718281828459, places=10)

        # C-string read
        mem.write_bytes(0x00200040, b"Hello ProStreet!\x00")
        self.assertEqual(mem.read_cstring(0x00200040), "Hello ProStreet!")

        # VirtualAlloc on heap
        h1 = mem.virtual_alloc(0, 0x1000)
        self.assertEqual(h1, HEAP_START)
        self.assertEqual(mem.read_bytes(h1, 16), b"\x00" * 16)


class TestGuestMemoryIntegration(unittest.TestCase):
    """Integration test verifying loading genuine nfs.exe PE sections into 1:1 memory."""

    @classmethod
    def setUpClass(cls) -> None:
        workspace = Path(__file__).resolve().parent.parent
        cfg_path = workspace / "config" / "local.json"
        if not cfg_path.is_file():
            raise unittest.SkipTest("Config not found")

        cfg = json.loads(cfg_path.read_text())
        cls.exe_path = Path(cfg["game_root"]) / "Need For Spped - Pro Street" / "nfs.exe"
        if not cls.exe_path.is_file():
            raise unittest.SkipTest("nfs.exe not found")

        cls.raw_exe = cls.exe_path.read_bytes()

    def test_load_real_prostreet_pe_sections(self) -> None:
        mem = GuestMemory(size=64 * 1024 * 1024)
        secs = mem.load_pe_sections(self.raw_exe)

        # Verify 10 sections loaded
        self.assertEqual(len(secs), 10)
        self.assertEqual(mem.image_base, 0x00400000)

        # Verify .text entry point 0x00828c25 (mainCRTStartup)
        entry_va = 0x00828c25
        entry_bytes = mem.read_bytes(entry_va, 5)
        # In MSVC 8.0 mainCRTStartup: call __security_init_cookie (E8 XX XX XX XX)
        self.assertEqual(entry_bytes[0], 0xE8)

        # Verify .rdata export name string
        rdata_slice = mem.read_bytes(0x00967000, 0x000e3000)
        self.assertIn(b"ProStreet08Release.exe", rdata_slice)

        # Verify C++ static initializers table __xc_a at 0x00967608..0x0096a1f4
        # Table contains 2,811 4-byte slots with 960 non-null function pointers
        table_start = 0x00967608
        table_end = 0x0096a1f4
        non_null_count = 0
        for va in range(table_start, table_end, 4):
            ptr = mem.read_u32(va)
            if ptr != 0:
                non_null_count += 1
                # Must reside inside .text (0x00401000..0x00967000)
                self.assertTrue(0x00401000 <= ptr < 0x00967000, f"Initializer 0x{ptr:08x} outside .text")

        self.assertEqual(non_null_count, 960, "Must find exactly 960 C++ static initializers")

        # Verify .data BSS region is zeroed
        # .data raw size is 0x5c6000, virt size 0x5c6000
        data_sec = next(s for s in secs if s.name == ".data")
        self.assertEqual(data_sec.virtual_address, 0x00a4a000)


if __name__ == "__main__":
    unittest.main()
