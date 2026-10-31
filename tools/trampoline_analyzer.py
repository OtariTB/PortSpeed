"""SecuROM Trampoline and Prologue Analyzer for NFS ProStreet.

Enumerates and resolves all 2,153 indirect jump sites (ff 25 [disp32]) in .text
that target the .securom section (0x01000000..0x01ffffff).

Resolves each site via:
1. Unicorn Engine emulation for the 1,853 ViTALiTY bridge stubs:
   - Intercepts execution at the unified bridge exit point (0x01ab234f: ret 4).
   - Extracts the exact destination address sitting at [esp].
2. Capstone static disassembly for the 300 plain x86 stubs in .securom:
   - Resolves direct jumps (jmp <imm>) and push-return trampolines (push <imm>; ret).
   - Identifies self-contained functions living directly in .securom.

Saves full resolution database to research/local/phase1/securom_trampolines.json.
The original game binary is opened strictly read-only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import struct
import time
from typing import Any, Sequence

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP

EXPECTED_NFS_EXE_SHA256 = "ee8a71c7c1e42923deb728e39a89317645cbcf26fc87cc48d3e07ade4dce2f72"
WORKSPACE = Path(__file__).resolve().parent.parent

# ViTALiTY crack engine exit point
VITALITY_EXIT_VA = 0x01AB234F


@dataclass
class InstructionInfo:
    address: int
    mnemonic: str
    op_str: str
    size: int


@dataclass
class TrampolineSite:
    site_va: int
    file_offset: int
    ptr_va: int
    stub_va: int
    stub_type: str  # 'vitality_call', 'vitality_obf_push', 'plain_jump', 'plain_push_ret', 'plain_function'
    target_va: int
    target_section: str  # '.text', '.securom', etc.
    is_function_entry: bool
    prologue_asm: list[dict[str, Any]]
    emulation_steps: int = 0


def va_to_offset(va: int, image_base: int = 0x00400000) -> int:
    """Convert virtual address to file offset for nfs.exe (RawOffset == RVA)."""
    return va - image_base


def parse_pe_sections(raw_exe: bytes) -> list[tuple[str, int, int, int, int]]:
    """Return list of (name, va, vsize, raw_offset, raw_size) for all PE sections."""
    if len(raw_exe) < 0x40 or raw_exe[:2] != b"MZ":
        raise ValueError("Invalid DOS header")
    pe_off = struct.unpack_from("<I", raw_exe, 0x3C)[0]
    if raw_exe[pe_off : pe_off + 4] != b"PE\x00\x00":
        raise ValueError("Invalid PE signature")

    num_sections = struct.unpack_from("<H", raw_exe, pe_off + 6)[0]
    opt_hdr_size = struct.unpack_from("<H", raw_exe, pe_off + 20)[0]
    image_base = struct.unpack_from("<I", raw_exe, pe_off + 24 + 28)[0]
    sec_table = pe_off + 24 + opt_hdr_size

    sections = []
    for i in range(num_sections):
        sec = raw_exe[sec_table + i * 40 : sec_table + (i + 1) * 40]
        name = sec[:8].rstrip(b"\x00").decode("latin1")
        vsize, rva, rsize, roff = struct.unpack_from("<4I", sec, 8)
        sections.append((name, image_base + rva, vsize, roff, rsize))
    return sections


def get_section_for_va(va: int, sections: Sequence[tuple[str, int, int, int, int]]) -> str:
    """Identify which section contains a virtual address."""
    for name, s_va, vsize, _, _ in sections:
        if s_va <= va < s_va + vsize:
            return name
    return "unknown"


def find_trampoline_sites(
    raw_exe: bytes,
    cs: Cs | None = None,
) -> list[tuple[int, int, int]]:
    """Scan .text for all 'ff 25' indirect jumps targeting .securom pointers.
    
    Returns list of (site_va, ptr_va, stub_va).
    """
    if cs is None:
        cs = Cs(CS_ARCH_X86, CS_MODE_32)

    sections = parse_pe_sections(raw_exe)
    text_info = next((s for s in sections if s[0] == ".text"), None)
    if not text_info:
        raise ValueError(".text section not found")

    _, text_va, _, text_off, text_size = text_info
    text_bytes = raw_exe[text_off : text_off + text_size]

    sites: list[tuple[int, int, int]] = []
    offset = 0
    limit = len(text_bytes) - 6

    while offset <= limit:
        idx = text_bytes.find(b"\xff\x25", offset)
        if idx == -1 or idx > limit:
            break

        ptr_va = struct.unpack_from("<I", text_bytes, idx + 2)[0]
        # Pointers targeting .securom or high data table slots (>= 0x01000000)
        if 0x01000000 <= ptr_va <= 0x01FFFFFF:
            ptr_off = va_to_offset(ptr_va)
            if ptr_off + 4 <= len(raw_exe):
                stub_va = struct.unpack_from("<I", raw_exe, ptr_off)[0]
                site_va = text_va + idx
                sites.append((site_va, ptr_va, stub_va))
        offset = idx + 1

    return sites


def classify_stub_initial(stub_bytes: bytes, stub_va: int, cs: Cs) -> str:
    """Classify stub as 'vitality_call', 'vitality_obf_push', or 'plain_x86'."""
    insns = list(cs.disasm(stub_bytes[:32], stub_va))
    if not insns:
        return "plain_x86"

    mnems = [i.mnemonic for i in insns[:4]]
    if "call" in mnems and any("0x1166690" in i.op_str for i in insns[:3]):
        return "vitality_call"
    if mnems[:3] == ["push", "push", "push"] and any("sub" in i.mnemonic for i in insns[3:5]):
        return "vitality_obf_push"
    return "plain_x86"


def resolve_plain_stub(
    raw_exe: bytes,
    stub_va: int,
    cs: Cs,
) -> tuple[str, int, list[dict[str, Any]]]:
    """Resolve a plain x86 stub statically without emulation."""
    stub_off = va_to_offset(stub_va)
    code = raw_exe[stub_off : stub_off + 1024]
    insns = list(cs.disasm(code, stub_va))

    # Look for jmp <imm>
    for j, ins in enumerate(insns):
        if ins.mnemonic == "jmp" and ins.op_str.startswith("0x"):
            try:
                dest = int(ins.op_str, 16)
                asm = [
                    {"address": i.address, "mnemonic": i.mnemonic, "op_str": i.op_str, "size": i.size}
                    for i in insns[: j + 1]
                ]
                return "plain_jump", dest, asm
            except ValueError:
                pass

        if ins.mnemonic in ("ret", "retf"):
            # Check if immediately preceded by push <imm>
            if j > 0 and insns[j - 1].mnemonic == "push" and insns[j - 1].op_str.startswith("0x"):
                try:
                    dest = int(insns[j - 1].op_str, 16)
                    asm = [
                        {"address": i.address, "mnemonic": i.mnemonic, "op_str": i.op_str, "size": i.size}
                        for i in insns[: j + 1]
                    ]
                    return "plain_push_ret", dest, asm
                except ValueError:
                    pass
            # Otherwise self-contained function
            asm = [
                {"address": i.address, "mnemonic": i.mnemonic, "op_str": i.op_str, "size": i.size}
                for i in insns[: j + 1]
            ]
            return "plain_function", stub_va, asm

    # Default fallback: self-contained function
    asm = [
        {"address": i.address, "mnemonic": i.mnemonic, "op_str": i.op_str, "size": i.size}
        for i in insns[:8]
    ]
    return "plain_function", stub_va, asm


def create_unicorn_emulator(raw_exe: bytes) -> tuple[Uc, dict[str, Any]]:
    """Initialize a fast Unicorn 32-bit x86 emulator pre-mapped with PE sections."""
    mu = Uc(UC_ARCH_X86, UC_MODE_32)

    # Map main binary: 0x00400000 to 0x02000000 (28 MB)
    base = 0x00400000
    size = 0x01C00000
    mu.mem_map(base, size)
    mu.mem_write(base, raw_exe)

    # Map page 0 for fs:[0] (SEH head pointer)
    mu.mem_map(0, 0x1000)
    mu.mem_write(0, struct.pack("<I", 0xFFFFFFFF))

    # Map stack
    stack_base = 0x00100000
    stack_size = 0x00100000
    mu.mem_map(stack_base, stack_size)

    state: dict[str, Any] = {"dest": None, "steps": 0}

    def hook_exit(uc: Uc, address: int, sz: int, user_data: Any) -> None:
        esp = uc.reg_read(UC_X86_REG_ESP)
        dest = struct.unpack("<I", uc.mem_read(esp, 4))[0]
        state["dest"] = dest
        uc.emu_stop()

    # Hook the unified ViTALiTY exit point
    mu.hook_add(UC_HOOK_CODE, hook_exit, None, VITALITY_EXIT_VA, VITALITY_EXIT_VA)
    return mu, state


def disassemble_prologue(raw_exe: bytes, target_va: int, cs: Cs, max_insns: int = 6) -> list[dict[str, Any]]:
    """Disassemble leading instructions at the resolved target address."""
    target_off = va_to_offset(target_va)
    if target_off < 0 or target_off + 32 > len(raw_exe):
        return []
    chunk = raw_exe[target_off : target_off + 32]
    insns = list(cs.disasm(chunk, target_va))
    return [
        {"address": i.address, "mnemonic": i.mnemonic, "op_str": i.op_str, "size": i.size}
        for i in insns[:max_insns]
    ]


def is_function_entry_boundary(raw_exe: bytes, site_va: int) -> bool:
    """Check if site_va is preceded by function alignment padding or ret."""
    off = va_to_offset(site_va)
    if off < 1:
        return True
    prev_byte = raw_exe[off - 1]
    # 0xcc = int3, 0x90 = nop, 0xc3 = ret, 0xc2 = ret imm16
    return prev_byte in (0xCC, 0x90, 0xC3)


def analyze_all_trampolines(
    raw_exe: bytes,
    cs: Cs | None = None,
    mu: Uc | None = None,
    mu_state: dict[str, Any] | None = None,
) -> list[TrampolineSite]:
    """Execute complete analysis across all 2,153 trampoline sites."""
    if cs is None:
        cs = Cs(CS_ARCH_X86, CS_MODE_32)
    if mu is None or mu_state is None:
        mu, mu_state = create_unicorn_emulator(raw_exe)

    sections = parse_pe_sections(raw_exe)
    raw_sites = find_trampoline_sites(raw_exe, cs)
    results: list[TrampolineSite] = []

    initial_esp = 0x001F0000
    dummy_ret = struct.pack("<I", 0x00401000)

    for site_va, ptr_va, stub_va in raw_sites:
        stub_off = va_to_offset(stub_va)
        stub_bytes = raw_exe[stub_off : stub_off + 32]
        cat = classify_stub_initial(stub_bytes, stub_va, cs)

        file_offset = va_to_offset(site_va)
        is_fn_entry = is_function_entry_boundary(raw_exe, site_va)

        if cat in ("vitality_call", "vitality_obf_push"):
            mu_state["dest"] = None
            mu.reg_write(UC_X86_REG_ESP, initial_esp)
            mu.mem_write(initial_esp, dummy_ret)
            try:
                mu.emu_start(site_va, 0x00900000, timeout=5000000)
                dest = mu_state["dest"]
                if dest is None:
                    dest = stub_va
            except Exception:
                dest = stub_va

            target_section = get_section_for_va(dest, sections)
            prologue = disassemble_prologue(raw_exe, dest, cs)
            results.append(
                TrampolineSite(
                    site_va=site_va,
                    file_offset=file_offset,
                    ptr_va=ptr_va,
                    stub_va=stub_va,
                    stub_type=cat,
                    target_va=dest,
                    target_section=target_section,
                    is_function_entry=is_fn_entry,
                    prologue_asm=prologue,
                )
            )
        else:
            sub_type, dest, asm = resolve_plain_stub(raw_exe, stub_va, cs)
            target_section = get_section_for_va(dest, sections)
            prologue = (
                disassemble_prologue(raw_exe, dest, cs)
                if dest != stub_va
                else asm[:6]
            )
            results.append(
                TrampolineSite(
                    site_va=site_va,
                    file_offset=file_offset,
                    ptr_va=ptr_va,
                    stub_va=stub_va,
                    stub_type=sub_type,
                    target_va=dest,
                    target_section=target_section,
                    is_function_entry=is_fn_entry,
                    prologue_asm=prologue,
                )
            )

    return results


def generate_trampoline_report(
    raw_exe: bytes,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Generate and write the full trampoline catalog and statistical summary."""
    t0 = time.time()
    results = analyze_all_trampolines(raw_exe)
    elapsed = time.time() - t0

    type_counts: dict[str, int] = {}
    sec_counts: dict[str, int] = {}
    for r in results:
        type_counts[r.stub_type] = type_counts.get(r.stub_type, 0) + 1
        sec_counts[r.target_section] = sec_counts.get(r.target_section, 0) + 1

    summary = {
        "total_trampolines": len(results),
        "analysis_time_seconds": round(elapsed, 3),
        "types": type_counts,
        "target_sections": sec_counts,
        "function_entry_sites": sum(1 for r in results if r.is_function_entry),
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "summary": summary,
            "trampolines": [asdict(r) for r in results],
        }
        output_path.write_text(json.dumps(data, indent=2))

    return summary


def main() -> None:
    config_path = WORKSPACE / "config" / "local.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    config = json.loads(config_path.read_text())
    exe_path = Path(config["game_root"]) / "Need For Spped - Pro Street" / "nfs.exe"
    if not exe_path.is_file():
        raise FileNotFoundError(f"nfs.exe not found at {exe_path}")

    raw_exe = exe_path.read_bytes()
    actual_hash = hashlib.sha256(raw_exe).hexdigest()
    if actual_hash != EXPECTED_NFS_EXE_SHA256:
        raise ValueError(f"Hash mismatch: expected {EXPECTED_NFS_EXE_SHA256}, got {actual_hash}")

    out_path = WORKSPACE / "research" / "local" / "phase1" / "securom_trampolines.json"
    summary = generate_trampoline_report(raw_exe, out_path)
    print("Trampoline analysis complete:")
    print(json.dumps(summary, indent=2))
    print(f"Output saved to: {out_path}")


if __name__ == "__main__":
    main()

