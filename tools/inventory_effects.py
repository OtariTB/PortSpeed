"""Inventory and structure analyzer for the 34 D3DX9 Effect resources in nfs.exe.

Phase 4.2 Research Tool: Extracts RT_RCDATA effect binaries from .rsrc,
analyzes container headers, parameters, techniques, passes, and shader bytecode tokens.
"""
from __future__ import annotations

import os
from pathlib import Path
import struct
import sys
from typing import Any, Dict, List, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from tools.build_win32_shims import EXE_PATH

SHADER_TOKENS = {
    0xFFFE0200: "vs_2_0",
    0xFFFE0300: "vs_3_0",
    0xFFFF0200: "ps_2_0",
    0xFFFF0300: "ps_3_0",
}


def parse_pe_resources(data: bytes) -> List[Tuple[str, int, int, int]]:
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    num_sections = struct.unpack_from("<H", data, pe_off + 6)[0]
    opt_hdr_size = struct.unpack_from("<H", data, pe_off + 20)[0]
    sec_table = pe_off + 24 + opt_hdr_size

    rsrc_rva, rsrc_off = 0, 0
    for i in range(num_sections):
        sec = data[sec_table + i * 40 : sec_table + (i + 1) * 40]
        name = sec[:8].decode("latin1").rstrip("\x00")
        if name == ".rsrc":
            rsrc_rva = struct.unpack_from("<I", sec, 12)[0]
            rsrc_off = struct.unpack_from("<I", sec, 20)[0]
            break

    def parse_dir(dir_off: int) -> List[Tuple[int, int]]:
        named_entries, id_entries = struct.unpack_from("<HH", data, dir_off + 12)
        entries = []
        entry_table = dir_off + 16
        for i in range(named_entries + id_entries):
            name_id, data_off = struct.unpack_from("<II", data, entry_table + i * 8)
            entries.append((name_id, data_off))
        return entries

    rcdata_entries = []
    for type_id, type_data_off in parse_dir(rsrc_off):
        if type_id == 10:  # RT_RCDATA
            name_dir_off = rsrc_off + (type_data_off & 0x7FFFFFFF)
            for res_name_id, res_data_off in parse_dir(name_dir_off):
                name_off = rsrc_off + (res_name_id & 0x7FFFFFFF)
                n_len = struct.unpack_from("<H", data, name_off)[0]
                r_name = data[name_off + 2 : name_off + 2 + n_len * 2].decode("utf-16le", errors="replace")
                lang_dir_off = rsrc_off + (res_data_off & 0x7FFFFFFF)
                for lang_id, leaf_off in parse_dir(lang_dir_off):
                    data_rva, data_size, _, _ = struct.unpack_from("<4I", data, rsrc_off + leaf_off)
                    file_off = data_rva - rsrc_rva + rsrc_off
                    rcdata_entries.append((r_name, data_size, data_rva, file_off))

    return rcdata_entries


def analyze_effect_header(fx_bytes: bytes) -> Dict[str, Any]:
    """Parses standard D3DX9 Effect binary container header.

    Structure:
    - offset 0x00: Magic (0xFEFF0901)
    - offset 0x04: Header size or total parameters offset
    - offset 0x08: Flags / version
    - offset 0x0c: Parameter count
    - offset 0x10: Technique count
    """
    magic = struct.unpack_from("<I", fx_bytes, 0)[0]
    words = struct.unpack_from("<8I", fx_bytes, 0)

    # Count shader model tokens
    counts = {"vs_2_0": 0, "vs_3_0": 0, "ps_2_0": 0, "ps_3_0": 0}
    for pos in range(0, len(fx_bytes) - 4, 4):
        val = struct.unpack_from("<I", fx_bytes, pos)[0]
        if val in SHADER_TOKENS:
            counts[SHADER_TOKENS[val]] += 1

    return {
        "magic": f"0x{magic:08x}",
        "raw_words": [f"0x{w:08x}" for w in words],
        "shader_counts": counts,
    }


def main():
    data = EXE_PATH.read_bytes()
    entries = parse_pe_resources(data)

    print(f"Total Embedded D3DX9 Effect Resources: {len(entries)}")
    print(f"{'#':2} {'Resource Name':26} {'Size (B)':8} {'Magic':10} {'VS2':4} {'PS2':4} {'VS3':4} {'PS3':4}")
    print("-" * 72)

    total_bytes = 0
    for idx, (name, size, rva, file_off) in enumerate(entries):
        total_bytes += size
        fx = data[file_off : file_off + size]
        info = analyze_effect_header(fx)
        sc = info["shader_counts"]
        print(f"{idx+1:2} {name:26} {size:8} {info['magic']:10} {sc['vs_2_0']:4} {sc['ps_2_0']:4} {sc['vs_3_0']:4} {sc['ps_3_0']:4}")

    print("-" * 72)
    print(f"Total Size of 34 Effects: {total_bytes} bytes ({total_bytes / 1024:.2f} KB)")


if __name__ == "__main__":
    main()
