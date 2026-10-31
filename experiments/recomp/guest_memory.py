from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

IMAGE_BASE = 0x00400000
EXPECTED_NFS_EXE_SHA256 = "ee8a71c7c1e42923deb728e39a89317645cbcf26fc87cc48d3e07ade4dce2f72"


class MemoryLoaderError(Exception):
    """Raised on invalid PE section structure or memory violation."""


@dataclass(frozen=True)
class PESection:
    name: str
    virtual_address: int
    virtual_size: int
    raw_offset: int
    raw_size: int
    flags: int

    @property
    def end_va(self) -> int:
        return self.virtual_address + self.virtual_size

    @property
    def is_readable(self) -> bool:
        return bool(self.flags & 0x40000000)

    @property
    def is_writable(self) -> bool:
        return bool(self.flags & 0x80000000)

    @property
    def is_executable(self) -> bool:
        return bool(self.flags & 0x20000000)


def is_reparse_point(path: Path) -> bool:
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if os.path.islink(path):
        return True
    file_attrs = getattr(st, "st_file_attributes", 0)
    return bool(file_attrs & 0x0400)


def parse_pe_sections(raw_exe: bytes) -> tuple[int, tuple[PESection, ...]]:
    """Parse PE image base and section table with strict bounds validation."""
    if len(raw_exe) < 0x40 or raw_exe[:2] != b"MZ":
        raise MemoryLoaderError("Invalid DOS header")
    pe_off = struct.unpack_from("<I", raw_exe, 0x3C)[0]
    if pe_off + 0x18 > len(raw_exe) or raw_exe[pe_off : pe_off + 4] != b"PE\x00\x00":
        raise MemoryLoaderError("Invalid PE header offset or signature")

    machine, num_sections = struct.unpack_from("<HH", raw_exe, pe_off + 4)
    if machine != 0x014C:  # IMAGE_FILE_MACHINE_I386
        raise MemoryLoaderError(f"Unsupported machine architecture: 0x{machine:04x}")
    if num_sections < 1 or num_sections > 96:
        raise MemoryLoaderError(f"Unreasonable section count: {num_sections}")

    opt_hdr_size = struct.unpack_from("<H", raw_exe, pe_off + 20)[0]
    opt_magic = struct.unpack_from("<H", raw_exe, pe_off + 24)[0]
    if opt_magic != 0x010B:  # PE32
        raise MemoryLoaderError(f"Unsupported optional header magic: 0x{opt_magic:04x}")

    image_base = struct.unpack_from("<I", raw_exe, pe_off + 24 + 28)[0]
    sec_table = pe_off + 24 + opt_hdr_size
    if sec_table + num_sections * 40 > len(raw_exe):
        raise MemoryLoaderError("Section table extends beyond file boundary")

    sections: list[PESection] = []
    for i in range(num_sections):
        sec_bytes = raw_exe[sec_table + i * 40 : sec_table + (i + 1) * 40]
        raw_name = sec_bytes[:8].split(b"\x00")[0]
        name = raw_name.decode("latin1", errors="replace")
        vsize, rva, rsize, roff = struct.unpack_from("<4I", sec_bytes, 8)
        flags = struct.unpack_from("<I", sec_bytes, 36)[0]

        va = image_base + rva
        if rsize > 0 and (roff + rsize > len(raw_exe)):
            raise MemoryLoaderError(f"Section {name} raw data extends beyond file bounds")

        sections.append(
            PESection(
                name=name,
                virtual_address=va,
                virtual_size=vsize,
                raw_offset=roff,
                raw_size=rsize,
                flags=flags,
            )
        )

    # Validate non-overlapping virtual address space
    sorted_secs = sorted(sections, key=lambda s: s.virtual_address)
    for a, b in zip(sorted_secs, sorted_secs[1:]):
        if a.end_va > b.virtual_address:
            raise MemoryLoaderError(f"Overlapping sections: {a.name} and {b.name}")

    return image_base, tuple(sections)


class GuestMemory:
    """Checked linear memory container for 32-bit guest x86 execution."""

    def __init__(self, size: int = 32 * 1024 * 1024) -> None:
        if size < 1024 * 1024 or size > 128 * 1024 * 1024:
            raise MemoryLoaderError(f"Unsupported guest memory size: {size}")
        self.size = size
        self.buffer = bytearray(size)
        self.sections: tuple[PESection, ...] = ()
        self.image_base: int = 0

    def check_bounds(self, va: int, length: int) -> None:
        if va < 0 or va + length > self.size:
            raise MemoryLoaderError(f"Guest access 0x{va:08x}..0x{va+length:08x} exceeds bounds (0..0x{self.size:08x})")

    def load_pe_sections(
        self,
        raw_exe: bytes,
        included_section_names: Sequence[str] = (".text", ".rdata", ".data", ".tls"),
    ) -> tuple[PESection, ...]:
        """Loads initialized section data into guest linear memory at their authentic VAs, zeroing uninitialized regions."""
        self.image_base, all_sections = parse_pe_sections(raw_exe)
        loaded = []
        for sec in all_sections:
            if sec.name in included_section_names:
                self.check_bounds(sec.virtual_address, sec.virtual_size)
                # Copy initialized raw data
                init_len = min(sec.raw_size, sec.virtual_size)
                if init_len > 0 and sec.raw_offset > 0:
                    self.buffer[sec.virtual_address : sec.virtual_address + init_len] = raw_exe[
                        sec.raw_offset : sec.raw_offset + init_len
                    ]
                # Zero uninitialized BSS region
                if sec.virtual_size > init_len:
                    self.buffer[sec.virtual_address + init_len : sec.end_va] = b"\x00" * (sec.virtual_size - init_len)
                loaded.append(sec)
        self.sections = tuple(loaded)
        return self.sections

    def read_u32(self, va: int) -> int:
        self.check_bounds(va, 4)
        return struct.unpack_from("<I", self.buffer, va)[0]

    def write_u32(self, va: int, val: int) -> None:
        self.check_bounds(va, 4)
        struct.pack_into("<I", self.buffer, va, val & 0xFFFFFFFF)

    def read_bytes(self, va: int, length: int) -> bytes:
        self.check_bounds(va, length)
        return bytes(self.buffer[va : va + length])

    def write_bytes(self, va: int, data: bytes) -> None:
        self.check_bounds(va, len(data))
        self.buffer[va : va + len(data)] = data
