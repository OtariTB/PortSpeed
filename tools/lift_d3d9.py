"""Static x86-to-AssemblyScript Lifter for Direct3D 9 Functions (Substep 4.1.4).

Lifts genuine x86 functions from nfs.exe (sub_0070e150 and sub_00705d30) into
clean AssemblyScript code that compiles to WebAssembly via asc.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any, Dict, List, Set, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM, CS_OP_REG
from capstone.x86 import *

from tools.build_catalog import CatalogBuilder
from tools.build_win32_shims import EXE_PATH
from tools.clean_drm import EXPECTED_NFS_EXE_SHA256
from tools.trampoline_analyzer import va_to_offset

WORKSPACE = Path(__file__).resolve().parent.parent

REG_NAMES = {
    X86_REG_EAX: "eax",
    X86_REG_ECX: "ecx",
    X86_REG_EDX: "edx",
    X86_REG_EBX: "ebx",
    X86_REG_ESP: "esp",
    X86_REG_EBP: "ebp",
    X86_REG_ESI: "esi",
    X86_REG_EDI: "edi",
    X86_REG_AX: "ax",
    X86_REG_CX: "cx",
    X86_REG_DX: "dx",
    X86_REG_BX: "bx",
    X86_REG_AL: "al",
    X86_REG_CL: "cl",
    X86_REG_DL: "dl",
    X86_REG_BL: "bl",
    X86_REG_AH: "ah",
    X86_REG_CH: "ch",
    X86_REG_DH: "dh",
    X86_REG_BH: "bh",
}


def mem_expr(mem: Any) -> str:
    """Builds an AssemblyScript address expression from Capstone mem operand."""
    parts = []
    if mem.base != 0:
        base_reg = REG_NAMES.get(mem.base, f"r_{mem.base}")
        parts.append(base_reg)
    if mem.index != 0:
        idx_reg = REG_NAMES.get(mem.index, f"r_{mem.index}")
        scale = mem.scale
        if scale > 1:
            parts.append(f"({idx_reg} * {scale})")
        else:
            parts.append(idx_reg)
    if mem.disp != 0:
        disp = mem.disp
        if disp > 0:
            parts.append(f"0x{disp:x}")
        else:
            parts.append(f"(0 - 0x{-disp:x})")
    if not parts:
        return "0"
    return " + ".join(parts)


def read_op(op: Any) -> str:
    if op.type == CS_OP_REG:
        r = REG_NAMES[op.reg]
        if r in ("al", "cl", "dl", "bl"):
            full = "e" + r.replace("l", "x")
            return f"(<u32>({full} & 0xff))"
        if r in ("ah", "ch", "dh", "bh"):
            full = "e" + r.replace("h", "x")
            return f"(<u32>(({full} >> 8) & 0xff))"
        if r in ("ax", "cx", "dx", "bx"):
            full = "e" + r
            return f"(<u32>({full} & 0xffff))"
        return r
    elif op.type == CS_OP_IMM:
        val = op.imm & 0xFFFFFFFF
        return f"0x{val:08x}"
    elif op.type == CS_OP_MEM:
        ea = mem_expr(op.mem)
        sz = op.size
        if sz == 1:
            return f"<u32>load<u8>({ea})"
        elif sz == 2:
            return f"<u32>load<u16>({ea})"
        else:
            return f"load<u32>({ea})"
    raise ValueError(f"Unknown op type: {op.type}")


def write_op(op: Any, val_expr: str) -> str:
    if op.type == CS_OP_REG:
        r = REG_NAMES[op.reg]
        if r in ("al", "cl", "dl", "bl"):
            full = "e" + r.replace("l", "x")
            return f"{full} = ({full} & 0xffffff00) | (<u32>({val_expr}) & 0xff);"
        if r in ("ah", "ch", "dh", "bh"):
            full = "e" + r.replace("h", "x")
            return f"{full} = ({full} & 0xffff00ff) | ((<u32>({val_expr}) & 0xff) << 8);"
        if r in ("ax", "cx", "dx", "bx"):
            full = "e" + r
            return f"{full} = ({full} & 0xffff0000) | (<u32>({val_expr}) & 0xffff);"
        return f"{r} = {val_expr};"
    elif op.type == CS_OP_MEM:
        ea = mem_expr(op.mem)
        sz = op.size
        if sz == 1:
            return f"store<u8>({ea}, <u8>({val_expr}));"
        elif sz == 2:
            return f"store<u16>({ea}, <u16>({val_expr}));"
        else:
            return f"store<u32>({ea}, <u32>({val_expr}));"
    raise ValueError(f"Unknown op type: {op.type}")


def lift_function_to_as(func_dict: Dict[str, Any], raw_exe: bytes) -> str:
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    cs.detail = True

    entry = func_dict["address"]
    blocks = func_dict["blocks"]
    fname = f"sub_{entry:08x}"

    lines = [
        f"// Genuine lifted ProStreet function {fname} at 0x{entry:08x}",
        f"export function {fname}(): u32 {{",
        f"  let pc: u32 = 0x{entry:08x};",
        "  while (true) {",
        "    switch (pc) {",
    ]

    for b_start, b_end, succs, is_exit in blocks:
        lines.append(f"      case 0x{b_start:08x}: {{")
        off = va_to_offset(b_start)
        code = raw_exe[off : off + (b_end - b_start)]

        insns = list(cs.disasm(code, b_start))
        ended_with_jump = False

        for idx, ins in enumerate(insns):
            m = ins.mnemonic
            ops = ins.operands
            comm = f"// 0x{ins.address:08x}: {ins.mnemonic} {ins.op_str}"

            if m == "sub":
                lines.append(f"        {write_op(ops[0], f'sub32Flags({read_op(ops[0])}, {read_op(ops[1])})')} {comm}")
            elif m == "add":
                lines.append(f"        {write_op(ops[0], f'add32Flags({read_op(ops[0])}, {read_op(ops[1])})')} {comm}")
            elif m == "xor":
                lines.append(f"        {{ const _r: u32 = {read_op(ops[0])} ^ {read_op(ops[1])}; {write_op(ops[0], '_r')} setLogic32(_r); }} {comm}")
            elif m == "and":
                lines.append(f"        {{ const _r: u32 = {read_op(ops[0])} & {read_op(ops[1])}; {write_op(ops[0], '_r')} setLogic32(_r); }} {comm}")
            elif m == "or":
                lines.append(f"        {{ const _r: u32 = {read_op(ops[0])} | {read_op(ops[1])}; {write_op(ops[0], '_r')} setLogic32(_r); }} {comm}")
            elif m == "mov":
                lines.append(f"        {write_op(ops[0], read_op(ops[1]))} {comm}")
            elif m == "lea":
                lines.append(f"        {write_op(ops[0], f'<u32>({mem_expr(ops[1].mem)})')} {comm}")
            elif m == "push":
                lines.append(f"        push32({read_op(ops[0])}); {comm}")
            elif m == "pop":
                lines.append(f"        {write_op(ops[0], 'pop32()')} {comm}")
            elif m == "cmp":
                lines.append(f"        sub32Flags({read_op(ops[0])}, {read_op(ops[1])}); {comm}")
            elif m == "test":
                lines.append(f"        setLogic32({read_op(ops[0])} & {read_op(ops[1])}); {comm}")
            elif m == "imul":
                if len(ops) == 3:
                    lines.append(f"        {write_op(ops[0], f'<u32>(<i32>{read_op(ops[1])} * <i32>{read_op(ops[2])})')} {comm}")
                elif len(ops) == 2:
                    lines.append(f"        {write_op(ops[0], f'<u32>(<i32>{read_op(ops[0])} * <i32>{read_op(ops[1])})')} {comm}")
            elif m == "setne":
                lines.append(f"        {write_op(ops[0], '(zf == 0) ? 1 : 0')} {comm}")
            elif m == "sete":
                lines.append(f"        {write_op(ops[0], '(zf != 0) ? 1 : 0')} {comm}")
            elif m == "fld1":
                lines.append(f"        fpu_push(1.0); {comm}")
            elif m == "fstp":
                ea = mem_expr(ops[0].mem)
                lines.append(f"        store<f32>({ea}, fpu_pop()); {comm}")
            elif m == "repe cmpsb":
                lines.append(f"        repe_cmpsb(); {comm}")
            elif m == "rep movsd":
                lines.append(f"        rep_movsd(); {comm}")
            elif m == "call":
                next_va = ins.address + ins.size
                lines.append(f"        push32(0x{next_va:08x}); {comm}")
                lines.append(f"        dispatchCall({read_op(ops[0])});")
            elif m == "ret":
                if ops:
                    bytes_pop = ops[0].imm
                    lines.append(f"        pop32(); esp += {bytes_pop}; return eax; {comm}")
                else:
                    lines.append(f"        pop32(); return eax; {comm}")
                ended_with_jump = True
            elif m == "jmp":
                if ops[0].type == CS_OP_IMM:
                    dest = ops[0].imm
                    lines.append(f"        pc = 0x{dest:08x}; break; {comm}")
                    ended_with_jump = True
                else:
                    lines.append(f"        dispatchCall({read_op(ops[0])}); return eax; {comm}")
                    ended_with_jump = True
            elif m in ("je", "jne", "jb", "jae", "jbe", "ja", "jl", "jge", "jle", "jg"):
                cond_map = {
                    "je": "zf != 0",
                    "jne": "zf == 0",
                    "jb": "cf != 0",
                    "jae": "cf == 0",
                    "jbe": "(cf != 0) || (zf != 0)",
                    "ja": "(cf == 0) && (zf == 0)",
                    "jl": "sf != of_flag",
                    "jge": "sf == of_flag",
                    "jle": "(zf != 0) || (sf != of_flag)",
                    "jg": "(zf == 0) && (sf == of_flag)",
                }
                cond = cond_map[m]
                dest = ops[0].imm
                next_va = ins.address + ins.size
                lines.append(f"        if ({cond}) {{ pc = 0x{dest:08x}; }} else {{ pc = 0x{next_va:08x}; }} break; {comm}")
                ended_with_jump = True
                break
            else:
                lines.append(f"        // WARNING: unsupported {m} {ins.op_str}")

        if not ended_with_jump:
            next_b = b_end
            lines.append(f"        pc = 0x{next_b:08x}; break;")
        lines.append("      }")

    lines.extend([
        "      default:",
        "        return 0xFFFFFFFF;",
        "    }",
        "  }",
        "}\n",
    ])
    return "\n".join(lines)


AS_HEADER = """// Auto-generated by tools/lift_d3d9.py for NFS ProStreet (Substep 4.1.4)
// DO NOT COMMIT GENERATED ARTIFACTS DERIVED FROM NFS.EXE

@external("env", "dispatchCall")
declare function dispatchCall(targetVa: u32): void;

export let eax: u32 = 0;
export let ecx: u32 = 0;
export let edx: u32 = 0;
export let ebx: u32 = 0;
export let esp: u32 = 0x003fe000;
export let ebp: u32 = 0;
export let esi: u32 = 0;
export let edi: u32 = 0;

export let zf: u32 = 0;
export let cf: u32 = 0;
export let sf: u32 = 0;
export let of_flag: u32 = 0;

let fpu_st0: f32 = 0.0;

@inline
function push32(val: u32): void {
  esp -= 4;
  store<u32>(esp, val);
}

@inline
function pop32(): u32 {
  const val = load<u32>(esp);
  esp += 4;
  return val;
}

@inline
function setLogic8(res: u8): void {
  cf = 0;
  of_flag = 0;
  zf = (res == 0) ? 1 : 0;
  sf = (<u32>res >>> 7) & 1;
}

@inline
function setLogic32(res: u32): void {
  cf = 0;
  of_flag = 0;
  zf = (res == 0) ? 1 : 0;
  sf = (res >>> 31) & 1;
}

@inline
function sub8Flags(a: u8, b: u8): u8 {
  const res: u8 = a - b;
  cf = (a < b) ? 1 : 0;
  zf = (res == 0) ? 1 : 0;
  sf = (<u32>res >>> 7) & 1;
  of_flag = (<u32>((a ^ b) & (a ^ res)) >>> 7) & 1;
  return res;
}

@inline
function sub16Flags(a: u16, b: u16): u16 {
  const res: u16 = a - b;
  cf = (a < b) ? 1 : 0;
  zf = (res == 0) ? 1 : 0;
  sf = (<u32>res >>> 15) & 1;
  of_flag = (<u32>((a ^ b) & (a ^ res)) >>> 15) & 1;
  return res;
}

@inline
function sub32Flags(a: u32, b: u32): u32 {
  const res: u32 = a - b;
  cf = (a < b) ? 1 : 0;
  zf = (res == 0) ? 1 : 0;
  sf = (res >>> 31) & 1;
  of_flag = (((a ^ b) & (a ^ res)) >>> 31) & 1;
  return res;
}

@inline
function add32Flags(a: u32, b: u32): u32 {
  const res: u32 = a + b;
  cf = (res < a) ? 1 : 0;
  zf = (res == 0) ? 1 : 0;
  sf = (res >>> 31) & 1;
  of_flag = ((~(a ^ b) & (a ^ res)) >>> 31) & 1;
  return res;
}

@inline
function repe_cmpsb(): void {
  while (ecx > 0) {
    const b1: u8 = load<u8>(esi);
    const b2: u8 = load<u8>(edi);
    esi += 1;
    edi += 1;
    ecx -= 1;
    sub8Flags(b1, b2);
    if (zf == 0) break;
  }
}

@inline
function rep_movsd(): void {
  while (ecx > 0) {
    store<u32>(edi, load<u32>(esi));
    esi += 4;
    edi += 4;
    ecx -= 1;
  }
}

@inline
function fpu_push(v: f32): void {
  fpu_st0 = v;
}

@inline
function fpu_pop(): f32 {
  return fpu_st0;
}

export function setupCpu(initEsp: u32, initEcx: u32, initEbx: u32, initEbp: u32): void {
  eax = 0;
  ecx = initEcx;
  edx = 0;
  ebx = initEbx;
  esp = initEsp;
  ebp = initEbp;
  esi = 0;
  edi = 0;
  zf = 0;
  cf = 0;
  sf = 0;
  of_flag = 0;
  fpu_st0 = 0.0;
}

export function callGuestFunction(funcVa: u32): u32 {
  switch (funcVa) {
    case 0x0070e150: return sub_0070e150();
    case 0x00705d30: return sub_00705d30();
    default: {
      return 0xFFFFFFFF;
    }
  }
}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Lift genuine ProStreet D3D9 functions to AssemblyScript & WebAssembly.")
    parser.add_argument("--outdir", type=Path, default=None)
    args = parser.parse_args()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA environment variable not set")

    outdir = args.outdir or (Path(local_app_data) / "NFSProStreetResearch" / "phase4" / "d3d9")
    outdir.mkdir(parents=True, exist_ok=True)

    if not EXE_PATH.is_file():
        raise FileNotFoundError(f"nfs.exe not found at {EXE_PATH}")

    raw_exe = EXE_PATH.read_bytes()
    exe_sha = hashlib.sha256(raw_exe).hexdigest()
    if exe_sha != EXPECTED_NFS_EXE_SHA256:
        raise ValueError(f"nfs.exe SHA-256 mismatch: {exe_sha}")

    builder = CatalogBuilder(raw_exe, {})
    targets = [0x0070e150, 0x00705d30]
    func_info: List[Dict[str, Any]] = []

    ts_parts = [AS_HEADER]

    for va in targets:
        f_dict, _ = builder.disassemble_function(va, set(targets))
        as_code = lift_function_to_as(f_dict, raw_exe)
        ts_parts.append(as_code)

        blocks = f_dict["blocks"]
        byte_len = max(b[1] for b in blocks) - min(b[0] for b in blocks)
        func_info.append({
            "name": f"sub_{va:08x}",
            "address": f"0x{va:08x}",
            "block_count": len(blocks),
            "byte_length": byte_len,
        })

    ts_path = outdir / "d3d9_lifted.ts"
    wasm_path = outdir / "d3d9_lifted.wasm"
    manifest_path = outdir / "lifted_manifest.json"

    ts_content = "\n".join(ts_parts)
    ts_path.write_text(ts_content, encoding="utf-8")
    print(f"Written AssemblyScript: {ts_path} ({len(ts_content)} bytes)")

    asc_cmd = WORKSPACE / "web" / "node_modules" / ".bin" / ("asc.cmd" if os.name == "nt" else "asc")
    if not asc_cmd.is_file():
        raise FileNotFoundError(f"AssemblyScript compiler not found at {asc_cmd}")

    cmd = [
        str(asc_cmd),
        str(ts_path),
        "-o",
        str(wasm_path),
        "--optimize",
        "--runtime",
        "stub",
        "--initialMemory",
        "1024",  # 64 MiB linear memory
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print("asc stdout:\n", res.stdout)
        print("asc stderr:\n", res.stderr)
        raise RuntimeError(f"asc compilation failed with code {res.returncode}")

    wasm_bytes = wasm_path.read_bytes()
    wasm_sha = hashlib.sha256(wasm_bytes).hexdigest()
    print(f"Compiled WebAssembly: {wasm_path} ({len(wasm_bytes)} bytes, sha256={wasm_sha[:16]}...)")

    manifest = {
        "source": str(EXE_PATH),
        "source_sha256": exe_sha,
        "wasm_path": str(wasm_path),
        "wasm_sha256": wasm_sha,
        "wasm_bytes": len(wasm_bytes),
        "functions": func_info,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
