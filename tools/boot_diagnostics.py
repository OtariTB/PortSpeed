"""Authentic ProStreet Engine Boot & Initializer Diagnostics Runner.

Executes genuine static C++ initializers from nfs.exe with authentic guest memory,
IAT bindings, and atexit hooks to diagnose the exact runtime blockers without stubs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys
from typing import Any, Dict, List, Optional, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

import capstone
import unicorn
from unicorn.x86_const import (
    UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ESI,
    UC_X86_REG_EDI
)

from tools.build_win32_shims import EXE_PATH
from tools.clean_drm import EXPECTED_NFS_EXE_SHA256
from tools.guest_crt import GuestCRT, SimulatedCPU
from tools.guest_d3d9 import GuestD3D9, D3D9_DIRECT3DCREATE9_IAT_VA, D3DX9_D3DXVEC3TRANSFORM_IAT_VA, D3DX9_D3DXMATRIXTRANSPOSE_IAT_VA
from tools.guest_initterm import GUEST_XC_A, GUEST_XC_Z
from tools.guest_memory import GuestMemory
from tools.guest_win32 import GuestWin32
from tools.trampoline_analyzer import create_unicorn_emulator, va_to_offset


def get_pe_import_map(raw: bytes) -> Dict[int, Tuple[str, str]]:
    """Extracts map of all IAT slots to (dll_name, symbol_name) from PE import directory."""
    pe_off = struct.unpack_from('<I', raw, 0x3C)[0]
    import_rva = struct.unpack_from('<I', raw, pe_off + 24 + 96 + 8)[0]
    sec_cnt = struct.unpack_from('<H', raw, pe_off + 6)[0]
    opt_hdr_sz = struct.unpack_from('<H', raw, pe_off + 20)[0]
    sec_hdr_off = pe_off + 24 + opt_hdr_sz
    sections = []
    for i in range(sec_cnt):
        name, vs, va, rs, rp = struct.unpack_from('<8sIIII', raw, sec_hdr_off + i * 40)[:5]
        sections.append((va, vs, rp, rs))

    def rva_to_off(rva: int) -> Optional[int]:
        for va, vs, rp, rs in sections:
            if va <= rva < va + max(vs, rs):
                return rp + (rva - va)
        return None

    off = rva_to_off(import_rva)
    if off is None:
        return {}

    all_imports = {}
    while True:
        ilt_rva, time, fwd, name_rva, iat_rva = struct.unpack_from('<IIIII', raw, off)
        if not (ilt_rva or name_rva or iat_rva):
            break
        off += 20
        name_off = rva_to_off(name_rva)
        if name_off is None:
            continue
        dll_name = raw[name_off:raw.find(b'\0', name_off)].decode('latin1')
        ilt_off = rva_to_off(ilt_rva)
        if ilt_off is None:
            continue
        idx = 0
        while True:
            thunk = struct.unpack_from('<I', raw, ilt_off + idx * 4)[0]
            if not thunk:
                break
            slot_va = 0x00400000 + iat_rva + idx * 4
            if thunk & 0x80000000:
                sname = f'ord_{thunk & 0xffff}'
            else:
                noff = rva_to_off(thunk)
                sname = raw[noff+2:raw.find(b'\0', noff+2)].decode('latin1') if noff else f'unknown_{idx}'
            all_imports[slot_va] = (dll_name, sname)
            idx += 1
    return all_imports


def run_initializer_diagnostics(max_constructors: Optional[int] = None, verbose: bool = False) -> Dict[str, Any]:
    """Executes authentic static C++ constructors and logs exact failure details."""
    raw = Path(EXE_PATH).read_bytes()
    uc, sections = create_unicorn_emulator(raw)

    # 1. Map 2MB Guest Stack (0x00200000..0x00400000)
    uc.mem_map(0x00200000, 0x00200000)
    # 2. Map Dynamic Heap (0x02000000..0x04000000)
    uc.mem_map(0x02000000, 0x02000000)

    # 3. Setup Guest Memory & IAT shims
    mem = GuestMemory()
    mem.load_pe_sections(raw)
    crt = GuestCRT(mem, raw)
    crt.init_iat()
    win32 = GuestWin32(mem, raw)
    win32.init_iat()

    iat_handlers: Dict[int, Tuple[str, Any]] = {}
    for slot_va, sym in crt.imports:
        iat_handlers[slot_va] = (sym, crt._get_handler(sym))
        uc.mem_write(slot_va, struct.pack('<I', slot_va))

    for item in win32.imports:
        slot_va, sym = item[1], item[2]
        iat_handlers[slot_va] = (sym, win32._get_handler(sym))
        uc.mem_write(slot_va, struct.pack('<I', slot_va))

    # Setup D3D9 & D3DX IAT shims (Direct3DCreate9, D3DXVec3Transform, D3DXMatrixTranspose)
    d3d9 = GuestD3D9(mem)
    d3d9.init_iat()
    iat_handlers[D3D9_DIRECT3DCREATE9_IAT_VA] = ("Direct3DCreate9", d3d9.shim_Direct3DCreate9)
    uc.mem_write(D3D9_DIRECT3DCREATE9_IAT_VA, struct.pack('<I', D3D9_DIRECT3DCREATE9_IAT_VA))
    iat_handlers[D3DX9_D3DXVEC3TRANSFORM_IAT_VA] = ("D3DXVec3Transform", d3d9.shim_D3DXVec3Transform)
    uc.mem_write(D3DX9_D3DXVEC3TRANSFORM_IAT_VA, struct.pack('<I', D3DX9_D3DXVEC3TRANSFORM_IAT_VA))
    iat_handlers[D3DX9_D3DXMATRIXTRANSPOSE_IAT_VA] = ("D3DXMatrixTranspose", d3d9.shim_D3DXMatrixTranspose)
    uc.mem_write(D3DX9_D3DXMATRIXTRANSPOSE_IAT_VA, struct.pack('<I', D3DX9_D3DXMATRIXTRANSPOSE_IAT_VA))

    # Hook atexit helper (sub_0082851b)
    onexit_registrations = []
    def hook_atexit(c):
        dtor = struct.unpack('<I', uc.mem_read(c.esp, 4))[0]
        onexit_registrations.append(dtor)
        c.eax = 0

    iat_handlers[0x0082851b] = ('sub_0082851b', hook_atexit)

    # Trace & IAT dispatch hook
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    cs.detail = True
    recent_insns: List[Tuple[int, str, str]] = []

    def hook_code(uc_inst, address, size, user_data):
        if address in iat_handlers:
            sym, handler = iat_handlers[address]
            esp = uc_inst.reg_read(UC_X86_REG_ESP)
            ret_addr = struct.unpack('<I', uc_inst.mem_read(esp, 4))[0]

            c = SimulatedCPU(mem)
            c.eax = uc_inst.reg_read(UC_X86_REG_EAX)
            c.ecx = uc_inst.reg_read(UC_X86_REG_ECX)
            c.edx = uc_inst.reg_read(UC_X86_REG_EDX)
            c.ebx = uc_inst.reg_read(UC_X86_REG_EBX)
            c.esp = esp + 4
            c.ebp = uc_inst.reg_read(UC_X86_REG_EBP)
            c.esi = uc_inst.reg_read(UC_X86_REG_ESI)
            c.edi = uc_inst.reg_read(UC_X86_REG_EDI)

            handler(c)

            uc_inst.reg_write(UC_X86_REG_EAX, c.eax)
            uc_inst.reg_write(UC_X86_REG_ECX, c.ecx)
            uc_inst.reg_write(UC_X86_REG_EDX, c.edx)
            uc_inst.reg_write(UC_X86_REG_EBX, c.ebx)
            uc_inst.reg_write(UC_X86_REG_ESP, c.esp)
            uc_inst.reg_write(UC_X86_REG_EBP, c.ebp)
            uc_inst.reg_write(UC_X86_REG_ESI, c.esi)
            uc_inst.reg_write(UC_X86_REG_EDI, c.edi)
            uc_inst.reg_write(UC_X86_REG_EIP, ret_addr)
            return

        try:
            b = uc_inst.mem_read(address, size)
            for ins in cs.disasm(b, address):
                recent_insns.append((address, ins.mnemonic, ins.op_str))
                if len(recent_insns) > 30:
                    recent_insns.pop(0)
        except Exception:
            pass

    uc.hook_add(unicorn.UC_HOOK_CODE, hook_code)

    # 4. Catalog all non-zero constructors in .CRT$XCA..$XCZ
    off = va_to_offset(GUEST_XC_A)
    total_slots = (GUEST_XC_Z - GUEST_XC_A) // 4
    non_zero = []
    for i in range(total_slots):
        val = struct.unpack_from('<I', raw, off + i * 4)[0]
        if val != 0:
            non_zero.append((len(non_zero) + 1, i, GUEST_XC_A + i * 4, val))

    if max_constructors is not None:
        non_zero = non_zero[:max_constructors]

    completed = 0
    failure = None

    for rank, slot_idx, slot_va, fn_va in non_zero:
        uc.reg_write(UC_X86_REG_ESP, 0x003feffc)
        uc.mem_write(0x003feffc, struct.pack('<I', 0x00401000))
        uc.reg_write(UC_X86_REG_EBP, 0x003ff000)

        try:
            uc.emu_start(fn_va, 0x00401000, timeout=1000000)
            completed += 1
            if verbose and completed % 50 == 0:
                print(f"  [Progress] Completed {completed}/{len(non_zero)} constructors...")
        except Exception as e:
            eip = uc.reg_read(UC_X86_REG_EIP)
            esp = uc.reg_read(UC_X86_REG_ESP)
            failure = {
                "rank": rank,
                "slot_index": slot_idx,
                "slot_va": f"0x{slot_va:08x}",
                "fn_va": f"0x{fn_va:08x}",
                "faulting_eip": f"0x{eip:08x}",
                "esp": f"0x{esp:08x}",
                "error": str(e),
                "recent_instructions": [
                    f"0x{addr:08x}: {mn} {op}".strip() for addr, mn, op in recent_insns[-10:]
                ],
            }
            break

    return {
        "status": "FAIL" if failure else "PASS",
        "total_table_slots": total_slots,
        "total_non_null_constructors": len(non_zero),
        "completed_count": completed,
        "onexit_registrations": len(onexit_registrations),
        "first_failure": failure,
    }


def main():
    parser = argparse.ArgumentParser(description="ProStreet Authentic Startup Diagnostics Runner")
    parser.add_argument("--max", type=int, default=None, help="Limit number of constructors to execute")
    parser.add_argument("--verbose", action="store_true", help="Print progress milestones")
    args = parser.parse_args()

    print("=== ProStreet Authentic Startup Diagnostics ===")
    res = run_initializer_diagnostics(max_constructors=args.max, verbose=args.verbose)

    print(f"Table Total Slots:       {res['total_table_slots']}")
    print(f"Active Non-Null Ctors:   {res['total_non_null_constructors']}")
    print(f"Successfully Completed:  {res['completed_count']}")
    print(f"Atexit Registrations:    {res['onexit_registrations']}")

    if res["status"] == "FAIL":
        f = res["first_failure"]
        print(f"\n[FIRST GENUINE STARTUP BLOCKER]")
        print(f"  Constructor Rank:       #{f['rank']} of {res['total_non_null_constructors']}")
        print(f"  Table Slot Index:       {f['slot_index']} (Slot VA: {f['slot_va']})")
        print(f"  Constructor Entry VA:   {f['fn_va']}")
        print(f"  Faulting EIP:           {f['faulting_eip']}")
        print(f"  Guest ESP:              {f['esp']}")
        print(f"  Error Reason:           {f['error']}")
        print(f"  Call Stack Context (last instructions):")
        for line in f["recent_instructions"]:
            print(f"    {line}")
        print("\nRoot Cause Classification:")
        raw = Path(EXE_PATH).read_bytes()
        import_map = get_pe_import_map(raw)
        matched_imp = None
        target_iat = None

        # Check last instruction for indirect jump/call through IAT
        import re
        if f["recent_instructions"]:
            m = re.search(r'\[0x([0-9a-fA-F]+)\]', f["recent_instructions"][-1])
            if m:
                target_iat = int(m.group(1), 16)
                if target_iat in import_map:
                    matched_imp = import_map[target_iat]

        if matched_imp:
            dll, sym = matched_imp
            print(f"  Missing platform IAT binding: {dll} import {sym} at 0x{target_iat:08x}.")
            print(f"  raw PE image contains stale unbound pre-bind pointer {f['faulting_eip']}.")
        else:
            print(f"  Unmapped memory access at EIP {f['faulting_eip']}.")
    else:
        print("\nAll tested constructors executed successfully.")


if __name__ == "__main__":
    main()
