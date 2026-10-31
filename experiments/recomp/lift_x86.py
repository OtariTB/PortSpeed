#!/usr/bin/env python3
"""Read-only x86 static lifter for Phase D ProStreet recompilation experiments.

Translates 32-bit x86 functions from nfs.exe (or synthetic byte fixtures) into:
1. C99 source code (`prostreet_lifted.c`) targeting `x86_cpu.h`.
2. AssemblyScript source (`prostreet_lifted.ts`) compiled to WebAssembly (`prostreet_lifted.wasm`).

Follows AGENTS.md rules:
- Never modifies or executes files in the original game installation.
- Refuses symlinks/reparse points and overlapping source/output roots.
- Writes outputs derived from nfs.exe only under %LOCALAPPDATA%/NFSProStreetResearch/phase3/recomp.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

EXPECTED_NFS_EXE_SHA256 = "ee8a71c7c1e42923deb728e39a89317645cbcf26fc87cc48d3e07ade4dce2f72"
IMAGE_BASE = 0x00400000

PROSTREET_TARGETS: tuple[tuple[str, int, int], ...] = (
    ("sub_00436680", 0x00436680, 0x004366A7),  # bStringHash(const char *str)
    ("sub_004366b0", 0x004366B0, 0x004366D7),  # bStringHashInit(const char *str, uint32_t init)
    ("sub_004366e0", 0x004366E0, 0x00436713),  # bStringHashUpper(const char *str)
    ("sub_006cd550", 0x006CD550, 0x006CD69C),  # LZDecompress_JDLZ(const uint8_t *src, uint8_t *dst)
    ("sub_006cd6a0", 0x006CD6A0, 0x006CE2FC),  # HUFF_DecodeCore(const uint8_t *src_after_hdr, uint8_t *dst)
    ("sub_006cfc10", 0x006CFC10, 0x006CFC3C),  # LZDecompress_HUFF(const uint8_t *src, uint8_t *dst)
    ("sub_006cfc40", 0x006CFC40, 0x006CFC70),  # LZDecompress_RAWW(const uint8_t *src, uint8_t *dst)
    ("sub_006cfc80", 0x006CFC80, 0x006CFD93),  # LZDecompress_COMP(const uint8_t *src, uint8_t *dst)
    ("sub_006cfdb0", 0x006CFDB0, 0x006CFDEA),  # LZValidHeader(const uint8_t *src)
    ("sub_006cfdf0", 0x006CFDF0, 0x006CFE56),  # LZDecompress(const uint8_t *src, uint8_t *dst)
    ("sub_006d3e20", 0x006D3E20, 0x006D3F14),  # LZDecompressInPlace_CIP(uint8_t *buf, int32_t uncomp_size)
    ("sub_00959ca0", 0x00959CA0, 0x00959CB4),  # _initterm slot 45: static C++ registration of 0xa4af2c into 0xab08c8
)

EXTERNAL_FUNCTION_MAP: dict[int, str] = {
    0x00436680: "sub_00436680",
    0x004366B0: "sub_004366b0",
    0x004366E0: "sub_004366e0",
    0x006CD550: "sub_006cd550",
    0x006CD6A0: "sub_006cd6a0",
    0x006CFC10: "sub_006cfc10",
    0x006CFC40: "sub_006cfc40",
    0x006CFC80: "sub_006cfc80",
    0x006CFDB0: "sub_006cfdb0",
    0x006CFDF0: "sub_006cfdf0",
    0x006D3E20: "sub_006d3e20",
    0x00959CA0: "sub_00959ca0",
}

CRT_DIRECT_CALL_MAP: dict[int, tuple[str, str]] = {
    0x008287C8: ("crt_memset", "crtMemset"),
    0x008287CE: ("crt_memcpy", "crtMemcpy"),
    0x00828460: ("crt_security_check_cookie", "crtSecurityCheckCookie"),
}

CRT_IAT_CALL_MAP: dict[int, tuple[str, str]] = {
    0x00967218: ("crt_malloc", "crtMalloc"),
    0x00967214: ("crt_free", "crtFree"),
}

# Verified SecuROM inline trampoline restorations (see research/phase3-recompilation.md):
# 1. VA 0x006cde95 (8 bytes in sub_006cd6a0): 1st unrolled iteration of 5-way Huffman table lookup
#    (iterations 2-5 at 0x006cdecb, 0x006cdeee, 0x006cdf11, 0x006cdf34 are unmodified `0f b6 8c 14 18 02 00 00`).
# 2. VA 0x006cfe02 (5 bytes in sub_006cfdf0): jumps to .text 0x00538300 (`cmp eax, [0x019f07e8]; jmp 0x006cfe07`)
#    where [0x019f07e8] == 0x57574152 ("RAWW"), matching `3d 52 41 57 57` (`cmp eax, 0x57574152`) at 0x006cfdb6.
SECUROM_TRAMPOLINE_PATCHES: dict[int, tuple[bytes, bytes, str]] = {
    0x006CDE95: (
        bytes.fromhex("ff2520ae9e015644"),
        bytes.fromhex("0fb68c1418020000"),
        "Restore 1st iteration of 5-way unrolled Huffman table lookup: movzx ecx, byte ptr [esp + edx + 0x218]",
    ),
    0x006CFE02: (
        bytes.fromhex("e9f984e6ff"),
        bytes.fromhex("3d52415757"),
        "Inline .text 0x00538300 trampoline comparing eax against 'RAWW' (0x57574152): cmp eax, 0x57574152",
    ),
}

REG32_NAMES = ("eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi")
REG16_NAMES = ("ax", "cx", "dx", "bx", "sp", "bp", "si", "di")
REG8_NAMES = ("al", "cl", "dl", "bl", "ah", "ch", "dh", "bh")


class LifterError(ValueError):
    """Raised when disassembly, CFG recovery, or path validation fails."""


@dataclass(frozen=True)
class Operand:
    kind: str  # "reg32", "reg8", "imm", "mem"
    reg: str | None = None
    imm: int = 0
    size: int = 4  # 1 or 4 bytes for memory operands
    base: str | None = None
    index: str | None = None
    scale: int = 1
    disp: int = 0


@dataclass(frozen=True)
class Instruction:
    address: int
    size: int
    raw_hex: str
    mnemonic: str
    op_str: str
    operands: tuple[Operand, ...]


@dataclass(frozen=True)
class LiftedFunction:
    name: str
    start_va: int
    end_va: int
    sha256: str
    instructions: tuple[Instruction, ...]
    block_leaders: tuple[int, ...]


def is_reparse_point(path: Path) -> bool:
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if os.path.islink(path):
        return True
    file_attrs = getattr(st, "st_file_attributes", 0)
    return bool(file_attrs & 0x0400)  # FILE_ATTRIBUTE_REPARSE_POINT


def ensure_safe_paths(
    source_path: Path | None,
    output_dir: Path,
    workspace_root: Path,
    game_root: Path | None = None,
) -> Path:
    """Validate source and output paths per AGENTS.md protection rules."""
    resolved_out = output_dir.resolve()
    resolved_ws = workspace_root.resolve()

    if resolved_out == resolved_ws or resolved_ws in resolved_out.parents or resolved_out in resolved_ws.parents:
        raise LifterError(f"Refusing output directory overlapping workspace root: {resolved_out}")

    if game_root is not None:
        resolved_game = game_root.resolve()
        if is_reparse_point(game_root):
            raise LifterError(f"Refusing reparse point on game_root: {game_root}")
        if (
            resolved_out == resolved_game
            or resolved_game in resolved_out.parents
            or resolved_out in resolved_game.parents
        ):
            raise LifterError(f"Refusing output directory overlapping protected game root: {resolved_out}")

    if source_path is not None:
        if is_reparse_point(source_path):
            raise LifterError(f"Refusing symlink/reparse source file: {source_path}")
        resolved_src = source_path.resolve()
        if resolved_out == resolved_src or resolved_out in resolved_src.parents:
            raise LifterError(f"Refusing output directory overlapping source path: {resolved_out}")

    return resolved_out


def _decode_modrm_mem(code: bytes, pos: int, size: int) -> tuple[Operand, int, int]:
    if pos >= len(code):
        raise LifterError("Truncated instruction at ModR/M byte")
    modrm = code[pos]
    pos += 1
    mod = (modrm >> 6) & 0x3
    reg_num = (modrm >> 3) & 0x7
    rm = modrm & 0x7

    if mod == 3:
        if size == 1:
            return Operand(kind="reg8", reg=REG8_NAMES[rm], size=1), reg_num, pos
        if size == 2:
            return Operand(kind="reg16", reg=REG16_NAMES[rm], size=2), reg_num, pos
        return Operand(kind="reg32", reg=REG32_NAMES[rm], size=4), reg_num, pos

    base: str | None = None
    index: str | None = None
    scale = 1
    disp = 0

    if rm == 4:
        if pos >= len(code):
            raise LifterError("Truncated instruction at SIB byte")
        sib = code[pos]
        pos += 1
        scale = 1 << ((sib >> 6) & 0x3)
        idx_num = (sib >> 3) & 0x7
        base_num = sib & 0x7
        if idx_num != 4:
            index = REG32_NAMES[idx_num]
        if base_num == 5 and mod == 0:
            if pos + 4 > len(code):
                raise LifterError("Truncated 32-bit SIB displacement")
            disp = struct.unpack_from("<i", code, pos)[0]
            pos += 4
        else:
            base = REG32_NAMES[base_num]
    elif rm == 5 and mod == 0:
        if pos + 4 > len(code):
            raise LifterError("Truncated absolute disp32 operand")
        disp = struct.unpack_from("<i", code, pos)[0]
        pos += 4
    else:
        base = REG32_NAMES[rm]

    if mod == 1:
        if pos >= len(code):
            raise LifterError("Truncated disp8 operand")
        disp = struct.unpack_from("<b", code, pos)[0]
        pos += 1
    elif mod == 2:
        if pos + 4 > len(code):
            raise LifterError("Truncated disp32 operand")
        disp = struct.unpack_from("<i", code, pos)[0]
        pos += 4

    return (
        Operand(kind="mem", size=size, base=base, index=index, scale=scale, disp=disp),
        reg_num,
        pos,
    )


def _format_operand(op: Operand) -> str:
    if op.kind in ("reg32", "reg16", "reg8"):
        return str(op.reg)
    if op.kind == "imm":
        return f"0x{op.imm & 0xFFFFFFFF:x}"
    parts: list[str] = []
    if op.base:
        parts.append(op.base)
    if op.index:
        parts.append(f"{op.index}*{op.scale}" if op.scale > 1 else op.index)
    expr = " + ".join(parts)
    if op.disp != 0 or not expr:
        if expr:
            sign = "+" if op.disp > 0 else "-"
            expr = f"{expr} {sign} 0x{abs(op.disp):x}"
        else:
            expr = f"0x{op.disp & 0xFFFFFFFF:x}"
    if op.size == 1:
        prefix = "byte ptr "
    elif op.size == 2:
        prefix = "word ptr "
    else:
        prefix = "dword ptr "
    return f"{prefix}[{expr}]"


def decode_x86_bytes(code: bytes, start_va: int) -> list[Instruction]:
    """Deterministic table-driven decoder for the 32-bit x86 subset used in Phase D / Phase 3A."""
    insns: list[Instruction] = []
    pos = 0
    n = len(code)

    while pos < n:
        insn_start = pos
        addr = start_va + insn_start
        b0 = code[pos]
        pos += 1

        mnemonic: str
        ops: tuple[Operand, ...]

        if b0 == 0x90:
            mnemonic = "nop"
            ops = ()
        elif b0 == 0xC3:
            mnemonic = "ret"
            ops = ()
        elif 0x50 <= b0 <= 0x57:
            mnemonic = "push"
            ops = (Operand(kind="reg32", reg=REG32_NAMES[b0 - 0x50]),)
        elif 0x58 <= b0 <= 0x5F:
            mnemonic = "pop"
            ops = (Operand(kind="reg32", reg=REG32_NAMES[b0 - 0x58]),)
        elif 0xB8 <= b0 <= 0xBF:
            if pos + 4 > n:
                raise LifterError(f"Truncated mov r32, imm32 at 0x{addr:08x}")
            imm_val = struct.unpack_from("<I", code, pos)[0]
            pos += 4
            mnemonic = "mov"
            ops = (
                Operand(kind="reg32", reg=REG32_NAMES[b0 - 0xB8], size=4),
                Operand(kind="imm", imm=imm_val, size=4),
            )
        elif b0 in (0xA1, 0xA3):
            if pos + 4 > n:
                raise LifterError(f"Truncated mov moffs32 instruction at 0x{addr:08x}")
            disp = struct.unpack_from("<i", code, pos)[0]
            pos += 4
            mnemonic = "mov"
            if b0 == 0xA1:
                ops = (
                    Operand(kind="reg32", reg="eax", size=4),
                    Operand(kind="mem", size=4, disp=disp),
                )
            else:
                ops = (
                    Operand(kind="mem", size=4, disp=disp),
                    Operand(kind="reg32", reg="eax", size=4),
                )
        elif b0 == 0x66:
            if pos >= n:
                raise LifterError(f"Truncated 0x66 operand-size prefix at 0x{addr:08x}")
            b1 = code[pos]
            pos += 1
            if b1 == 0x39:
                rm_op, reg_num, pos = _decode_modrm_mem(code, pos, 2)
                reg_op = Operand(kind="reg16", reg=REG16_NAMES[reg_num], size=2)
                mnemonic = "cmp"
                ops = (rm_op, reg_op)
            else:
                raise LifterError(f"Unsupported 0x66 opcode 0x{b1:02x} at 0x{addr:08x}")
        elif b0 in (
            0x88,
            0x89,
            0x8A,
            0x8B,
            0x8D,
            0x01,
            0x03,
            0x0B,
            0x1B,
            0x2B,
            0x33,
            0x39,
            0x3A,
            0x3B,
            0x84,
            0x85,
        ):
            is_byte = b0 in (0x88, 0x8A, 0x3A, 0x84)
            rm_op, reg_num, pos = _decode_modrm_mem(code, pos, 1 if is_byte else 4)
            reg_op = Operand(
                kind="reg8" if is_byte else "reg32",
                reg=(REG8_NAMES if is_byte else REG32_NAMES)[reg_num],
                size=1 if is_byte else 4,
            )
            if (
                b0 == 0x8D
                and rm_op.kind == "mem"
                and rm_op.base == "esp"
                and rm_op.index is None
                and rm_op.disp == 0
                and reg_op.reg == "esp"
            ):
                mnemonic = "nop"
                ops = ()
            elif b0 == 0x8B and rm_op.kind == "reg32" and rm_op.reg == reg_op.reg:
                mnemonic = "nop"
                ops = ()
            elif b0 in (0x88, 0x89):
                mnemonic = "mov"
                ops = (rm_op, reg_op)
            elif b0 in (0x8A, 0x8B):
                mnemonic = "mov"
                ops = (reg_op, rm_op)
            elif b0 == 0x8D:
                mnemonic = "lea"
                ops = (reg_op, rm_op)
            elif b0 == 0x01:
                mnemonic = "add"
                ops = (rm_op, reg_op)
            elif b0 == 0x03:
                mnemonic = "add"
                ops = (reg_op, rm_op)
            elif b0 == 0x0B:
                mnemonic = "or"
                ops = (reg_op, rm_op)
            elif b0 == 0x1B:
                mnemonic = "sbb"
                ops = (reg_op, rm_op)
            elif b0 == 0x2B:
                mnemonic = "sub"
                ops = (reg_op, rm_op)
            elif b0 == 0x33:
                mnemonic = "xor"
                ops = (reg_op, rm_op)
            elif b0 == 0x39:
                mnemonic = "cmp"
                ops = (rm_op, reg_op)
            elif b0 in (0x3A, 0x3B):
                mnemonic = "cmp"
                ops = (reg_op, rm_op)
            else:
                mnemonic = "test"
                ops = (rm_op, reg_op)
        elif b0 in (0x80, 0x81, 0x83):
            is_byte = b0 == 0x80
            rm_op, subop, pos = _decode_modrm_mem(code, pos, 1 if is_byte else 4)
            if b0 in (0x80, 0x83):
                if pos >= n:
                    raise LifterError(f"Truncated immediate at 0x{addr:08x}")
                imm_val = struct.unpack_from("<b", code, pos)[0] if b0 == 0x83 else code[pos]
                if b0 == 0x83:
                    imm_val &= 0xFFFFFFFF
                pos += 1
            else:
                if pos + 4 > n:
                    raise LifterError(f"Truncated imm32 at 0x{addr:08x}")
                imm_val = struct.unpack_from("<I", code, pos)[0]
                pos += 4
            subop_map = {0: "add", 1: "or", 4: "and", 5: "sub", 7: "cmp"}
            if subop not in subop_map:
                raise LifterError(f"Unsupported group-1 subopcode {subop} at 0x{addr:08x}")
            mnemonic = subop_map[subop]
            ops = (rm_op, Operand(kind="imm", imm=imm_val, size=1 if is_byte else 4))
        elif b0 in (0xC6, 0xC7):
            is_byte = b0 == 0xC6
            rm_op, subop, pos = _decode_modrm_mem(code, pos, 1 if is_byte else 4)
            if subop != 0:
                raise LifterError(f"Unsupported 0x{b0:02x} subopcode {subop} at 0x{addr:08x}")
            if is_byte:
                if pos >= n:
                    raise LifterError(f"Truncated imm8 at 0x{addr:08x}")
                imm_val = code[pos]
                pos += 1
            else:
                if pos + 4 > n:
                    raise LifterError(f"Truncated imm32 at 0x{addr:08x}")
                imm_val = struct.unpack_from("<I", code, pos)[0]
                pos += 4
            mnemonic = "mov"
            ops = (rm_op, Operand(kind="imm", imm=imm_val, size=1 if is_byte else 4))
        elif b0 in (0xC1, 0xD1, 0xD3):
            rm_op, subop, pos = _decode_modrm_mem(code, pos, 4)
            if subop == 4:
                mnemonic = "shl"
            elif subop == 5:
                mnemonic = "shr"
            else:
                raise LifterError(f"Unsupported shift subopcode {subop} at 0x{addr:08x}")
            if b0 == 0xC1:
                if pos >= n:
                    raise LifterError(f"Truncated shift count at 0x{addr:08x}")
                count = code[pos]
                pos += 1
                ops = (rm_op, Operand(kind="imm", imm=count, size=1))
            elif b0 == 0xD1:
                ops = (rm_op, Operand(kind="imm", imm=1, size=1))
            else:
                ops = (rm_op, Operand(kind="reg8", reg="cl", size=1))
        elif b0 == 0xF6:
            rm_op, subop, pos = _decode_modrm_mem(code, pos, 1)
            if subop != 0 or pos >= n:
                raise LifterError(f"Unsupported 0xF6 subopcode {subop} at 0x{addr:08x}")
            imm_val = code[pos]
            pos += 1
            mnemonic = "test"
            ops = (rm_op, Operand(kind="imm", imm=imm_val, size=1))
        elif b0 == 0xF7:
            rm_op, subop, pos = _decode_modrm_mem(code, pos, 4)
            if subop == 0:
                if pos + 4 > n:
                    raise LifterError(f"Truncated test rm32, imm32 at 0x{addr:08x}")
                imm_val = struct.unpack_from("<I", code, pos)[0]
                pos += 4
                mnemonic = "test"
                ops = (rm_op, Operand(kind="imm", imm=imm_val, size=4))
            elif subop == 3:
                mnemonic = "neg"
                ops = (rm_op,)
            else:
                raise LifterError(f"Unsupported 0xF7 subopcode {subop} at 0x{addr:08x}")
        elif b0 == 0xA8:
            if pos >= n:
                raise LifterError(f"Truncated test al, imm8 at 0x{addr:08x}")
            imm_val = code[pos]
            pos += 1
            mnemonic = "test"
            ops = (Operand(kind="reg8", reg="al", size=1), Operand(kind="imm", imm=imm_val, size=1))
        elif b0 in (0x0D, 0x25, 0x3D, 0xA9):
            if pos + 4 > n:
                raise LifterError(f"Truncated eax imm32 instruction at 0x{addr:08x}")
            imm_val = struct.unpack_from("<I", code, pos)[0]
            pos += 4
            mnemonic = {0x0D: "or", 0x25: "and", 0x3D: "cmp", 0xA9: "test"}[b0]
            ops = (Operand(kind="reg32", reg="eax", size=4), Operand(kind="imm", imm=imm_val, size=4))
        elif 0x70 <= b0 <= 0x7F or b0 == 0xEB:
            if pos >= n:
                raise LifterError(f"Truncated rel8 branch at 0x{addr:08x}")
            rel = struct.unpack_from("<b", code, pos)[0]
            pos += 1
            target = (start_va + pos + rel) & 0xFFFFFFFF
            jcc_map = {
                0x72: "jb",
                0x73: "jae",
                0x74: "je",
                0x75: "jne",
                0x77: "ja",
                0x78: "js",
                0x79: "jns",
                0x7C: "jl",
                0x7D: "jge",
                0x7E: "jle",
                0xEB: "jmp",
            }
            if b0 not in jcc_map:
                raise LifterError(f"Unsupported short branch 0x{b0:02x} at 0x{addr:08x}")
            mnemonic = jcc_map[b0]
            ops = (Operand(kind="imm", imm=target, size=4),)
        elif b0 in (0xE8, 0xE9):
            if pos + 4 > n:
                raise LifterError(f"Truncated rel32 branch/call at 0x{addr:08x}")
            rel = struct.unpack_from("<i", code, pos)[0]
            pos += 4
            target = (start_va + pos + rel) & 0xFFFFFFFF
            mnemonic = "call" if b0 == 0xE8 else "jmp"
            ops = (Operand(kind="imm", imm=target, size=4),)
        elif b0 == 0xFF:
            rm_op, subop, pos = _decode_modrm_mem(code, pos, 4)
            if subop == 2:
                mnemonic = "call"
                ops = (rm_op,)
            else:
                raise LifterError(f"Unsupported 0xFF subopcode {subop} at 0x{addr:08x}")
        elif b0 == 0x0F:
            if pos >= n:
                raise LifterError(f"Truncated 0x0F opcode at 0x{addr:08x}")
            b1 = code[pos]
            pos += 1
            if b1 in (0xB6, 0xBE):
                rm_op, reg_num, pos = _decode_modrm_mem(code, pos, 1)
                reg_op = Operand(kind="reg32", reg=REG32_NAMES[reg_num], size=4)
                mnemonic = "movzx" if b1 == 0xB6 else "movsx"
                ops = (reg_op, rm_op)
            elif b1 == 0x94:
                rm_op, _, pos = _decode_modrm_mem(code, pos, 1)
                mnemonic = "sete"
                ops = (rm_op,)
            elif 0x80 <= b1 <= 0x8F:
                if pos + 4 > n:
                    raise LifterError(f"Truncated jcc rel32 at 0x{addr:08x}")
                rel = struct.unpack_from("<i", code, pos)[0]
                pos += 4
                target = (start_va + pos + rel) & 0xFFFFFFFF
                jcc32_map = {
                    0x82: "jb",
                    0x83: "jae",
                    0x84: "je",
                    0x85: "jne",
                    0x87: "ja",
                    0x88: "js",
                    0x89: "jns",
                    0x8C: "jl",
                    0x8D: "jge",
                    0x8E: "jle",
                }
                if b1 not in jcc32_map:
                    raise LifterError(f"Unsupported near branch 0x0F 0x{b1:02x} at 0x{addr:08x}")
                mnemonic = jcc32_map[b1]
                ops = (Operand(kind="imm", imm=target, size=4),)
            else:
                raise LifterError(f"Unsupported opcode 0x0F 0x{b1:02x} at 0x{addr:08x}")
        else:
            raise LifterError(f"Unsupported opcode 0x{b0:02x} at 0x{addr:08x}")

        raw_slice = code[insn_start:pos]
        op_str = ", ".join(_format_operand(o) for o in ops)
        insns.append(
            Instruction(
                address=addr,
                size=pos - insn_start,
                raw_hex=raw_slice.hex(),
                mnemonic=mnemonic,
                op_str=op_str,
                operands=ops,
            )
        )

    return insns


BRANCH_MNEMONICS = ("jmp", "je", "jne", "ja", "jae", "jb", "js", "jns", "jl", "jge", "jle")


def discover_basic_blocks(insns: Sequence[Instruction], start_va: int, end_va: int) -> tuple[int, ...]:
    if not insns:
        raise LifterError("Cannot lift empty instruction sequence")

    valid_addrs = {insn.address for insn in insns}
    leaders: set[int] = {start_va}

    for idx, insn in enumerate(insns):
        if insn.mnemonic in BRANCH_MNEMONICS:
            target = insn.operands[0].imm
            if insn.mnemonic == "jmp" and target in EXTERNAL_FUNCTION_MAP:
                if idx + 1 < len(insns):
                    leaders.add(insns[idx + 1].address)
                continue
            if target < start_va or target > end_va or target not in valid_addrs:
                raise LifterError(
                    f"Branch at 0x{insn.address:08x} targets invalid address 0x{target:08x} "
                    f"(valid range 0x{start_va:08x}..0x{end_va:08x})"
                )
            leaders.add(target)
            if idx + 1 < len(insns):
                leaders.add(insns[idx + 1].address)
        elif insn.mnemonic == "ret":
            if idx + 1 < len(insns):
                leaders.add(insns[idx + 1].address)

    if insns[-1].mnemonic not in ("ret", "jmp"):
        raise LifterError(f"Function ending at 0x{insns[-1].address:08x} does not end with ret or unconditional jmp")

    return tuple(sorted(leaders))


def lift_function_bytes(name: str, code: bytes, start_va: int) -> LiftedFunction:
    if not code:
        raise LifterError(f"Empty code buffer for {name}")
    end_va = start_va + len(code) - 1
    insns = decode_x86_bytes(code, start_va)
    decoded_len = sum(i.size for i in insns)
    if decoded_len != len(code):
        raise LifterError(f"Decoded length {decoded_len} != input length {len(code)} for {name}")
    leaders = discover_basic_blocks(insns, start_va, end_va)
    digest = hashlib.sha256(code).hexdigest()
    return LiftedFunction(
        name=name,
        start_va=start_va,
        end_va=end_va,
        sha256=digest,
        instructions=tuple(insns),
        block_leaders=leaders,
    )


def _c_addr_expr(op: Operand) -> str:
    terms: list[str] = []
    if op.base:
        terms.append(f"c->{op.base}")
    if op.index:
        terms.append(f"(c->{op.index} * {op.scale}u)" if op.scale > 1 else f"c->{op.index}")
    if op.disp != 0 or not terms:
        disp_u32 = op.disp & 0xFFFFFFFF
        terms.append(f"0x{disp_u32:08x}u")
    return " + ".join(terms)


def _c_read_op(op: Operand) -> str:
    if op.kind == "reg32":
        return f"c->{op.reg}"
    if op.kind == "reg16":
        full16 = {
            "ax": "eax",
            "cx": "ecx",
            "dx": "edx",
            "bx": "ebx",
            "sp": "esp",
            "bp": "ebp",
            "si": "esi",
            "di": "edi",
        }[str(op.reg)]
        return f"get_lo16(c->{full16})"
    if op.kind == "reg8":
        if op.reg in ("al", "cl", "dl", "bl"):
            full = {"al": "eax", "cl": "ecx", "dl": "edx", "bl": "ebx"}[str(op.reg)]
            return f"get_lo8(c->{full})"
        if op.reg in ("ah", "ch", "dh", "bh"):
            full = {"ah": "eax", "ch": "ecx", "dh": "edx", "bh": "ebx"}[str(op.reg)]
            return f"get_hi8(c->{full})"
        raise LifterError(f"Unsupported 8-bit register {op.reg}")
    if op.kind == "imm":
        if op.size == 1:
            mask = 0xFF
        elif op.size == 2:
            mask = 0xFFFF
        else:
            mask = 0xFFFFFFFF
        return f"0x{op.imm & mask:x}u"
    if op.kind == "mem":
        addr = _c_addr_expr(op)
        if op.size == 1:
            return f"rd8(c, {addr})"
        if op.size == 2:
            return f"rd16(c, {addr})"
        return f"rd32(c, {addr})"
    raise LifterError(f"Unknown operand kind {op.kind}")


def _c_write_op(op: Operand, val_expr: str) -> str:
    if op.kind == "reg32":
        return f"c->{op.reg} = (uint32_t)({val_expr});"
    if op.kind == "reg8":
        if op.reg in ("al", "cl", "dl", "bl"):
            full = {"al": "eax", "cl": "ecx", "dl": "edx", "bl": "ebx"}[str(op.reg)]
            return f"c->{full} = set_lo8(c->{full}, (uint8_t)({val_expr}));"
        if op.reg in ("ah", "ch", "dh", "bh"):
            full = {"ah": "eax", "ch": "ecx", "dh": "edx", "bh": "ebx"}[str(op.reg)]
            return f"c->{full} = set_hi8(c->{full}, (uint8_t)({val_expr}));"
        raise LifterError(f"Unsupported 8-bit register {op.reg}")
    if op.kind == "mem":
        addr = _c_addr_expr(op)
        if op.size == 1:
            return f"wr8(c, {addr}, (uint8_t)({val_expr}));"
        return f"wr32(c, {addr}, (uint32_t)({val_expr}));"
    raise LifterError(f"Cannot write to operand kind {op.kind}")


def emit_c_function(fn: LiftedFunction) -> str:
    lines: list[str] = [
        f"/* Lifted from {fn.name} (VA 0x{fn.start_va:08x}..0x{fn.end_va:08x}, sha256={fn.sha256[:16]}...) */",
        f"void {fn.name}(X86Cpu *c) {{",
    ]
    leaders = set(fn.block_leaders)
    for insn in fn.instructions:
        if insn.address in leaders:
            lines.append(f"L_{insn.address:08x}: ;")
        comment = f"/* 0x{insn.address:08x}: {insn.mnemonic} {insn.op_str} */"
        m = insn.mnemonic
        ops = insn.operands
        if m == "nop":
            lines.append(f"    {comment}")
        elif m == "mov":
            lines.append(f"    {_c_write_op(ops[0], _c_read_op(ops[1]))} {comment}")
        elif m == "movzx":
            lines.append(f"    {_c_write_op(ops[0], f'(uint32_t)(uint8_t)({_c_read_op(ops[1])})')} {comment}")
        elif m == "movsx":
            lines.append(f"    {_c_write_op(ops[0], f'(uint32_t)(int32_t)(int8_t)({_c_read_op(ops[1])})')} {comment}")
        elif m == "sete":
            lines.append(f"    {_c_write_op(ops[0], '(c->zf != 0u) ? 1u : 0u')} {comment}")
        elif m == "lea":
            lines.append(f"    {_c_write_op(ops[0], _c_addr_expr(ops[1]))} {comment}")
        elif m == "push":
            lines.append(f"    push32(c, {_c_read_op(ops[0])}); {comment}")
        elif m == "pop":
            lines.append(f"    {_c_write_op(ops[0], 'pop32(c)')} {comment}")
        elif m == "add":
            lines.append(f"    {_c_write_op(ops[0], f'add32_flags(c, {_c_read_op(ops[0])}, {_c_read_op(ops[1])})')} {comment}")
        elif m == "sub":
            if ops[0].size == 1:
                lines.append(
                    f"    {_c_write_op(ops[0], f'sub8_flags(c, (uint8_t){_c_read_op(ops[0])}, (uint8_t){_c_read_op(ops[1])})')} {comment}"
                )
            else:
                lines.append(
                    f"    {_c_write_op(ops[0], f'sub32_flags(c, {_c_read_op(ops[0])}, {_c_read_op(ops[1])})')} {comment}"
                )
        elif m == "sbb":
            lines.append(f"    {_c_write_op(ops[0], f'sbb32_flags(c, {_c_read_op(ops[0])}, {_c_read_op(ops[1])})')} {comment}")
        elif m == "neg":
            lines.append(f"    {_c_write_op(ops[0], f'neg32_flags(c, {_c_read_op(ops[0])})')} {comment}")
        elif m in ("or", "and", "xor"):
            op_sym = {"or": "|", "and": "&", "xor": "^"}[m]
            if ops[0].size == 1:
                lines.append(
                    f"    {{ uint8_t _r = (uint8_t)({_c_read_op(ops[0])} {op_sym} {_c_read_op(ops[1])}); "
                    f"{_c_write_op(ops[0], '_r')} set_logic8(c, _r); }} {comment}"
                )
            else:
                lines.append(
                    f"    {{ uint32_t _r = (uint32_t)({_c_read_op(ops[0])} {op_sym} {_c_read_op(ops[1])}); "
                    f"{_c_write_op(ops[0], '_r')} set_logic32(c, _r); }} {comment}"
                )
        elif m == "shl":
            if ops[1].kind == "imm":
                cnt = ops[1].imm & 0x1F
                lines.append(
                    f"    {{ uint32_t _v = {_c_read_op(ops[0])}; uint32_t _r = _v << {cnt}u; "
                    f"c->cf = (_v >> ({32 - cnt}u)) & 1u; {_c_write_op(ops[0], '_r')} "
                    f"c->zf = (_r == 0u); c->sf = (_r >> 31) & 1u; }} {comment}"
                )
            else:
                lines.append(
                    f"    {_c_write_op(ops[0], f'shl32_flags(c, {_c_read_op(ops[0])}, {_c_read_op(ops[1])})')} {comment}"
                )
        elif m == "shr":
            if ops[1].kind == "imm":
                cnt = ops[1].imm & 0x1F
                lines.append(
                    f"    {{ uint32_t _v = {_c_read_op(ops[0])}; uint32_t _r = _v >> {cnt}u; "
                    f"c->cf = (_v >> ({cnt - 1}u)) & 1u; {_c_write_op(ops[0], '_r')} "
                    f"c->zf = (_r == 0u); c->sf = (_r >> 31) & 1u; }} {comment}"
                )
            else:
                lines.append(
                    f"    {_c_write_op(ops[0], f'shr32_flags(c, {_c_read_op(ops[0])}, {_c_read_op(ops[1])})')} {comment}"
                )
        elif m == "cmp":
            if ops[0].size == 1:
                lines.append(
                    f"    (void)sub8_flags(c, (uint8_t){_c_read_op(ops[0])}, (uint8_t){_c_read_op(ops[1])}); {comment}"
                )
            elif ops[0].size == 2:
                lines.append(
                    f"    (void)sub16_flags(c, (uint16_t){_c_read_op(ops[0])}, (uint16_t){_c_read_op(ops[1])}); {comment}"
                )
            else:
                lines.append(f"    (void)sub32_flags(c, {_c_read_op(ops[0])}, {_c_read_op(ops[1])}); {comment}")
        elif m == "test":
            if ops[0].size == 1:
                lines.append(
                    f"    set_logic8(c, (uint8_t)({_c_read_op(ops[0])} & {_c_read_op(ops[1])})); {comment}"
                )
            else:
                lines.append(
                    f"    set_logic32(c, (uint32_t)({_c_read_op(ops[0])} & {_c_read_op(ops[1])})); {comment}"
                )
        elif m == "call":
            next_va = insn.address + insn.size
            if ops[0].kind == "imm":
                target = ops[0].imm
                if target in EXTERNAL_FUNCTION_MAP:
                    callee = EXTERNAL_FUNCTION_MAP[target]
                    lines.append(f"    push32(c, 0x{next_va:08x}u); {callee}(c); {comment}")
                elif target in CRT_DIRECT_CALL_MAP:
                    c_helper = CRT_DIRECT_CALL_MAP[target][0]
                    lines.append(f"    {c_helper}(c); {comment}")
                else:
                    raise LifterError(f"Unsupported direct call target 0x{target:08x} at 0x{insn.address:08x}")
            elif ops[0].kind == "mem" and ops[0].base is None and ops[0].index is None:
                iat_addr = ops[0].disp & 0xFFFFFFFF
                if iat_addr in CRT_IAT_CALL_MAP:
                    c_helper = CRT_IAT_CALL_MAP[iat_addr][0]
                    lines.append(f"    {c_helper}(c); {comment}")
                else:
                    raise LifterError(f"Unsupported IAT call [0x{iat_addr:08x}] at 0x{insn.address:08x}")
            else:
                raise LifterError(f"Unsupported indirect call at 0x{insn.address:08x}")
        elif m == "jmp":
            target = ops[0].imm
            if target < fn.start_va or target > fn.end_va:
                if target in EXTERNAL_FUNCTION_MAP:
                    callee = EXTERNAL_FUNCTION_MAP[target]
                    lines.append(f"    {callee}(c); return; {comment}")
                else:
                    raise LifterError(f"Unsupported external tail-jmp target 0x{target:08x}")
            else:
                lines.append(f"    goto L_{target:08x}; {comment}")
        elif m in ("je", "jne", "ja", "jae", "jb", "js", "jns", "jl", "jge", "jle"):
            cond = {
                "je": "c->zf != 0u",
                "jne": "c->zf == 0u",
                "ja": "(c->cf == 0u) && (c->zf == 0u)",
                "jae": "c->cf == 0u",
                "jb": "c->cf != 0u",
                "js": "c->sf != 0u",
                "jns": "c->sf == 0u",
                "jl": "c->sf != c->of",
                "jge": "c->sf == c->of",
                "jle": "(c->zf != 0u) || (c->sf != c->of)",
            }[m]
            lines.append(f"    if ({cond}) goto L_{ops[0].imm:08x}; {comment}")
        elif m == "ret":
            lines.append(f"    (void)pop32(c); return; {comment}")
        else:
            raise LifterError(f"Unhandled mnemonic {m}")
    lines.append("}")
    return "\n".join(lines)


def emit_c_module(functions: Sequence[LiftedFunction], header_path: str = "x86_cpu.h") -> str:
    parts = [
        "/* Auto-generated by experiments/recomp/lift_x86.py — DO NOT COMMIT PROPRIETARY OUTPUT */",
        f'#include "{header_path}"',
        "",
    ]
    for fn in functions:
        parts.append(f"void {fn.name}(X86Cpu *c);")
    parts.append("")
    for fn in functions:
        parts.append(emit_c_function(fn))
        parts.append("")
    return "\n".join(parts)


def _as_addr_expr(op: Operand) -> str:
    terms: list[str] = []
    if op.base:
        terms.append(op.base)
    if op.index:
        terms.append(f"({op.index} * {op.scale})" if op.scale > 1 else op.index)
    if op.disp != 0 or not terms:
        disp_u32 = op.disp & 0xFFFFFFFF
        terms.append(f"0x{disp_u32:08x}")
    return "(" + " + ".join(terms) + ")"


def _as_read_op(op: Operand) -> str:
    if op.kind == "reg32":
        return str(op.reg)
    if op.kind == "reg16":
        full16 = {
            "ax": "eax",
            "cx": "ecx",
            "dx": "edx",
            "bx": "ebx",
            "sp": "esp",
            "bp": "ebp",
            "si": "esi",
            "di": "edi",
        }[str(op.reg)]
        return f"(<u16>({full16} & 0xffff))"
    if op.kind == "reg8":
        if op.reg in ("al", "cl", "dl", "bl"):
            full = {"al": "eax", "cl": "ecx", "dl": "edx", "bl": "ebx"}[str(op.reg)]
            return f"(<u8>({full} & 0xff))"
        if op.reg in ("ah", "ch", "dh", "bh"):
            full = {"ah": "eax", "ch": "ecx", "dh": "edx", "bh": "ebx"}[str(op.reg)]
            return f"(<u8>(({full} >>> 8) & 0xff))"
        raise LifterError(f"Unsupported 8-bit register {op.reg}")
    if op.kind == "imm":
        if op.size == 1:
            return f"(<u8>0x{op.imm & 0xFF:02x})"
        if op.size == 2:
            return f"(<u16>0x{op.imm & 0xFFFF:04x})"
        return f"(<u32>0x{op.imm & 0xFFFFFFFF:08x})"
    if op.kind == "mem":
        addr = _as_addr_expr(op)
        if op.size == 1:
            return f"load<u8>({addr})"
        if op.size == 2:
            return f"load<u16>({addr})"
        return f"load<u32>({addr})"
    raise LifterError(f"Unknown operand kind {op.kind}")


def _as_write_op(op: Operand, val_expr: str) -> str:
    if op.kind == "reg32":
        return f"{op.reg} = <u32>({val_expr});"
    if op.kind == "reg8":
        if op.reg in ("al", "cl", "dl", "bl"):
            full = {"al": "eax", "cl": "ecx", "dl": "edx", "bl": "ebx"}[str(op.reg)]
            return f"{full} = ({full} & 0xffffff00) | (<u32>(<u8>({val_expr})));"
        if op.reg in ("ah", "ch", "dh", "bh"):
            full = {"ah": "eax", "ch": "ecx", "dh": "edx", "bh": "ebx"}[str(op.reg)]
            return f"{full} = ({full} & 0xffff00ff) | ((<u32>(<u8>({val_expr}))) << 8);"
        raise LifterError(f"Unsupported 8-bit register {op.reg}")
    if op.kind == "mem":
        addr = _as_addr_expr(op)
        if op.size == 1:
            return f"store<u8>({addr}, <u8>({val_expr}));"
        return f"store<u32>({addr}, <u32>({val_expr}));"
    raise LifterError(f"Cannot write to operand kind {op.kind}")


def emit_assemblyscript_function(fn: LiftedFunction) -> str:
    leaders = list(fn.block_leaders)
    leader_set = set(leaders)

    blocks: list[tuple[int, list[Instruction]]] = []
    cur_leader = leaders[0]
    cur_insns: list[Instruction] = []
    for insn in fn.instructions:
        if insn.address in leader_set and cur_insns:
            blocks.append((cur_leader, cur_insns))
            cur_leader = insn.address
            cur_insns = []
        cur_insns.append(insn)
    if cur_insns:
        blocks.append((cur_leader, cur_insns))

    lines: list[str] = [
        f"// Lifted from {fn.name} (VA 0x{fn.start_va:08x}..0x{fn.end_va:08x}, sha256={fn.sha256[:16]}...)",
        f"export function {fn.name}(): u32 {{",
        f"  let pc: u32 = 0x{fn.start_va:08x};",
        "  while (true) {",
        "    switch (pc) {",
    ]

    for block_idx, (leader_addr, block_insns) in enumerate(blocks):
        next_leader = blocks[block_idx + 1][0] if block_idx + 1 < len(blocks) else 0
        lines.append(f"      case 0x{leader_addr:08x}: {{")
        ended_with_jump_or_ret = False

        for insn in block_insns:
            m = insn.mnemonic
            ops = insn.operands
            comment = f"// 0x{insn.address:08x}: {insn.mnemonic} {insn.op_str}"
            if m == "nop":
                lines.append(f"        {comment}")
            elif m == "mov":
                lines.append(f"        {_as_write_op(ops[0], _as_read_op(ops[1]))} {comment}")
            elif m == "movzx":
                lines.append(f"        {_as_write_op(ops[0], f'<u32>(<u8>({_as_read_op(ops[1])}))')} {comment}")
            elif m == "movsx":
                lines.append(f"        {_as_write_op(ops[0], f'<u32>(<i32>(<i8>({_as_read_op(ops[1])})))')} {comment}")
            elif m == "sete":
                lines.append(f"        {_as_write_op(ops[0], '(zf != 0) ? 1 : 0')} {comment}")
            elif m == "lea":
                lines.append(f"        {_as_write_op(ops[0], _as_addr_expr(ops[1]))} {comment}")
            elif m == "push":
                lines.append(f"        push32({_as_read_op(ops[0])}); {comment}")
            elif m == "pop":
                lines.append(f"        {_as_write_op(ops[0], 'pop32()')} {comment}")
            elif m == "add":
                lines.append(f"        {_as_write_op(ops[0], f'add32Flags({_as_read_op(ops[0])}, {_as_read_op(ops[1])})')} {comment}")
            elif m == "sub":
                if ops[0].size == 1:
                    lines.append(
                        f"        {_as_write_op(ops[0], f'sub8Flags({_as_read_op(ops[0])}, {_as_read_op(ops[1])})')} {comment}"
                    )
                else:
                    lines.append(
                        f"        {_as_write_op(ops[0], f'sub32Flags({_as_read_op(ops[0])}, {_as_read_op(ops[1])})')} {comment}"
                    )
            elif m == "sbb":
                lines.append(
                    f"        {_as_write_op(ops[0], f'sbb32Flags({_as_read_op(ops[0])}, {_as_read_op(ops[1])})')} {comment}"
                )
            elif m == "neg":
                lines.append(
                    f"        {_as_write_op(ops[0], f'neg32Flags({_as_read_op(ops[0])})')} {comment}"
                )
            elif m in ("or", "and", "xor"):
                op_sym = {"or": "|", "and": "&", "xor": "^"}[m]
                if ops[0].size == 1:
                    lines.append(
                        f"        {{ const r8: u8 = <u8>({_as_read_op(ops[0])} {op_sym} {_as_read_op(ops[1])}); "
                        f"{_as_write_op(ops[0], 'r8')} setLogic8(r8); }} {comment}"
                    )
                else:
                    lines.append(
                        f"        {{ const r32: u32 = <u32>({_as_read_op(ops[0])} {op_sym} {_as_read_op(ops[1])}); "
                        f"{_as_write_op(ops[0], 'r32')} setLogic32(r32); }} {comment}"
                    )
            elif m == "shl":
                if ops[1].kind == "imm":
                    cnt = ops[1].imm & 0x1F
                    lines.append(
                        f"        {{ const v: u32 = {_as_read_op(ops[0])}; const r: u32 = v << {cnt}; "
                        f"cf = (v >>> {32 - cnt}) & 1; {_as_write_op(ops[0], 'r')} "
                        f"zf = (r == 0) ? 1 : 0; sf = (r >>> 31) & 1; }} {comment}"
                    )
                else:
                    lines.append(
                        f"        {_as_write_op(ops[0], f'shl32Flags({_as_read_op(ops[0])}, <u32>{_as_read_op(ops[1])})')} {comment}"
                    )
            elif m == "shr":
                if ops[1].kind == "imm":
                    cnt = ops[1].imm & 0x1F
                    lines.append(
                        f"        {{ const v: u32 = {_as_read_op(ops[0])}; const r: u32 = v >>> {cnt}; "
                        f"cf = (v >>> {cnt - 1}) & 1; {_as_write_op(ops[0], 'r')} "
                        f"zf = (r == 0) ? 1 : 0; sf = (r >>> 31) & 1; }} {comment}"
                    )
                else:
                    lines.append(
                        f"        {_as_write_op(ops[0], f'shr32Flags({_as_read_op(ops[0])}, <u32>{_as_read_op(ops[1])})')} {comment}"
                    )
            elif m == "cmp":
                if ops[0].size == 1:
                    lines.append(f"        sub8Flags({_as_read_op(ops[0])}, {_as_read_op(ops[1])}); {comment}")
                elif ops[0].size == 2:
                    lines.append(f"        sub16Flags({_as_read_op(ops[0])}, {_as_read_op(ops[1])}); {comment}")
                else:
                    lines.append(f"        sub32Flags({_as_read_op(ops[0])}, {_as_read_op(ops[1])}); {comment}")
            elif m == "test":
                if ops[0].size == 1:
                    lines.append(
                        f"        setLogic8(<u8>({_as_read_op(ops[0])} & {_as_read_op(ops[1])})); {comment}"
                    )
                else:
                    lines.append(
                        f"        setLogic32(<u32>({_as_read_op(ops[0])} & {_as_read_op(ops[1])})); {comment}"
                    )
            elif m == "call":
                next_va = insn.address + insn.size
                if ops[0].kind == "imm":
                    target = ops[0].imm
                    if target in EXTERNAL_FUNCTION_MAP:
                        callee = EXTERNAL_FUNCTION_MAP[target]
                        lines.append(f"        push32(0x{next_va:08x}); {callee}(); {comment}")
                    elif target in CRT_DIRECT_CALL_MAP:
                        as_helper = CRT_DIRECT_CALL_MAP[target][1]
                        lines.append(f"        {as_helper}(); {comment}")
                    else:
                        raise LifterError(f"Unsupported direct call target 0x{target:08x} at 0x{insn.address:08x}")
                elif ops[0].kind == "mem" and ops[0].base is None and ops[0].index is None:
                    iat_addr = ops[0].disp & 0xFFFFFFFF
                    if iat_addr in CRT_IAT_CALL_MAP:
                        as_helper = CRT_IAT_CALL_MAP[iat_addr][1]
                        lines.append(f"        {as_helper}(); {comment}")
                    else:
                        raise LifterError(f"Unsupported IAT call [0x{iat_addr:08x}] at 0x{insn.address:08x}")
                else:
                    raise LifterError(f"Unsupported indirect call at 0x{insn.address:08x}")
            elif m == "jmp":
                target = ops[0].imm
                if target < fn.start_va or target > fn.end_va:
                    if target in EXTERNAL_FUNCTION_MAP:
                        callee = EXTERNAL_FUNCTION_MAP[target]
                        lines.append(f"        return {callee}(); {comment}")
                        ended_with_jump_or_ret = True
                    else:
                        raise LifterError(f"Unsupported external tail-jmp target 0x{target:08x}")
                else:
                    lines.append(f"        pc = 0x{target:08x}; break; {comment}")
                    ended_with_jump_or_ret = True
            elif m in ("je", "jne", "ja", "jae", "jb", "js", "jns", "jl", "jge", "jle"):
                cond = {
                    "je": "zf != 0",
                    "jne": "zf == 0",
                    "ja": "(cf == 0) && (zf == 0)",
                    "jae": "cf == 0",
                    "jb": "cf != 0",
                    "js": "sf != 0",
                    "jns": "sf == 0",
                    "jl": "sf != of_flag",
                    "jge": "sf == of_flag",
                    "jle": "(zf != 0) || (sf != of_flag)",
                }[m]
                lines.append(
                    f"        if ({cond}) {{ pc = 0x{ops[0].imm:08x}; }} else {{ pc = 0x{next_leader:08x}; }} break; {comment}"
                )
                ended_with_jump_or_ret = True
            elif m == "ret":
                lines.append(f"        pop32(); return eax; {comment}")
                ended_with_jump_or_ret = True
            else:
                raise LifterError(f"Unhandled mnemonic {m}")

        if not ended_with_jump_or_ret:
            lines.append(f"        pc = 0x{next_leader:08x}; break;")
        lines.append("      }")

    lines.extend(
        [
            "      default:",
            "        unreachable();",
            "    }",
            "  }",
            "}",
        ]
    )
    return "\n".join(lines)


def emit_assemblyscript_module(functions: Sequence[LiftedFunction]) -> str:
    header = """// Auto-generated by experiments/recomp/lift_x86.py — DO NOT COMMIT PROPRIETARY OUTPUT

export let eax: u32 = 0;
export let ecx: u32 = 0;
export let edx: u32 = 0;
export let ebx: u32 = 0;
export let esp: u32 = 0x000ff000;
export let ebp: u32 = 0;
export let esi: u32 = 0;
export let edi: u32 = 0;

export let zf: u32 = 0;
export let cf: u32 = 0;
export let sf: u32 = 0;
export let of_flag: u32 = 0;
export let heapPtr: u32 = 0x00300000;

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
function sbb32Flags(a: u32, b: u32): u32 {
  const borrow: u64 = <u64>(cf & 1);
  const full: u64 = <u64>a - <u64>b - borrow;
  const res: u32 = <u32>full;
  cf = ((full >>> 32) != 0) ? 1 : 0;
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
function neg32Flags(a: u32): u32 {
  const res: u32 = 0 - a;
  cf = (a != 0) ? 1 : 0;
  zf = (res == 0) ? 1 : 0;
  sf = (res >>> 31) & 1;
  of_flag = (a == 0x80000000) ? 1 : 0;
  return res;
}

@inline
function shl32Flags(v: u32, count: u32): u32 {
  const cnt: u32 = count & 0x1f;
  if (cnt == 0) return v;
  const r: u32 = v << cnt;
  cf = (v >>> (32 - cnt)) & 1;
  zf = (r == 0) ? 1 : 0;
  sf = (r >>> 31) & 1;
  return r;
}

@inline
function shr32Flags(v: u32, count: u32): u32 {
  const cnt: u32 = count & 0x1f;
  if (cnt == 0) return v;
  const r: u32 = v >>> cnt;
  cf = (v >>> (cnt - 1)) & 1;
  zf = (r == 0) ? 1 : 0;
  sf = (r >>> 31) & 1;
  return r;
}

@inline
function crtMemset(): void {
  const dst: u32 = load<u32>(esp);
  const val: u8 = <u8>(load<u32>(esp + 4) & 0xff);
  const count: u32 = load<u32>(esp + 8);
  memory.fill(dst, val, count);
  eax = dst;
}

@inline
function crtMemcpy(): void {
  const dst: u32 = load<u32>(esp);
  const src: u32 = load<u32>(esp + 4);
  const count: u32 = load<u32>(esp + 8);
  memory.copy(dst, src, count);
  eax = dst;
}

@inline
function crtMalloc(): void {
  const sz: u32 = load<u32>(esp);
  const aligned: u32 = (heapPtr + 15) & ~15;
  eax = aligned;
  heapPtr = aligned + ((sz + 15) & ~15);
}

@inline
function crtFree(): void {
  // bump allocator; resetCpu reclaims heapPtr
}

@inline
function crtSecurityCheckCookie(): void {
  if (ecx != load<u32>(0x00a8be00)) {
    unreachable();
  }
}

export function resetCpu(stackPtr: u32): void {
  eax = 0;
  ecx = 0;
  edx = 0;
  ebx = 0;
  esp = stackPtr;
  ebp = 0;
  esi = 0;
  edi = 0;
  zf = 0;
  cf = 0;
  sf = 0;
  of_flag = 0;
  heapPtr = 0x00300000;
  store<u32>(0x00a8be00, 0xbb40e64e); // .data __security_cookie
  store<u32>(0x00abafd0, 0x00000000); // .data HUFF_DecodeCore global state
}

export function callGuestFunction(funcVa: u32): u32 {
  switch (funcVa) {
    case 0x00436680: return sub_00436680();
    case 0x004366b0: return sub_004366b0();
    case 0x004366e0: return sub_004366e0();
    case 0x006cd550: return sub_006cd550();
    case 0x006cd6a0: return sub_006cd6a0();
    case 0x006cfc10: return sub_006cfc10();
    case 0x006cfc40: return sub_006cfc40();
    case 0x006cfc80: return sub_006cfc80();
    case 0x006cfdb0: return sub_006cfdb0();
    case 0x006cfdf0: return sub_006cfdf0();
    case 0x006d3e20: return sub_006d3e20();
    case 0x00959ca0: return sub_00959ca0();
    default: {
      unreachable();
      return 0;
    }
  }
}

export function prepareCdecl0(stackPtr: u32): void {
  resetCpu(stackPtr);
  push32(0xdeadbeef); // synthetic return address
}

export function prepareCdecl1(arg0: u32, stackPtr: u32): void {
  resetCpu(stackPtr);
  push32(arg0);
  push32(0xdeadbeef); // synthetic return address
}

export function prepareCdecl2(arg0: u32, arg1: u32, stackPtr: u32): void {
  resetCpu(stackPtr);
  push32(arg1);
  push32(arg0);
  push32(0xdeadbeef); // synthetic return address
}

export function prepareCdecl4(arg0: u32, arg1: u32, arg2: u32, arg3: u32, stackPtr: u32): void {
  resetCpu(stackPtr);
  push32(arg3);
  push32(arg2);
  push32(arg1);
  push32(arg0);
  push32(0xdeadbeef); // synthetic return address
}
"""
    parts = [header]
    for fn in functions:
        parts.append(emit_assemblyscript_function(fn))
        parts.append("")
    return "\n".join(parts)


def read_prostreet_functions(
    exe_path: Path,
    targets: Iterable[tuple[str, int, int]] = PROSTREET_TARGETS,
) -> list[LiftedFunction]:
    if is_reparse_point(exe_path):
        raise LifterError(f"Refusing symlink/reparse executable: {exe_path}")
    raw_exe = exe_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_exe).hexdigest()
    if actual_sha256 != EXPECTED_NFS_EXE_SHA256:
        raise LifterError(
            f"Unexpected nfs.exe SHA-256: {actual_sha256} (expected {EXPECTED_NFS_EXE_SHA256})"
        )

    lifted: list[LiftedFunction] = []
    for name, start_va, end_va in targets:
        file_offset = start_va - IMAGE_BASE
        length = end_va - start_va + 1
        if file_offset < 0 or file_offset + length > len(raw_exe):
            raise LifterError(f"Target {name} range 0x{start_va:08x}..0x{end_va:08x} out of bounds")
        code_buf = bytearray(raw_exe[file_offset : file_offset + length])
        for patch_va, (expected_bytes, restored_bytes, _desc) in SECUROM_TRAMPOLINE_PATCHES.items():
            if start_va <= patch_va <= end_va:
                rel_off = patch_va - start_va
                actual_slice = bytes(code_buf[rel_off : rel_off + len(expected_bytes)])
                if actual_slice != expected_bytes:
                    raise LifterError(
                        f"SecuROM trampoline mismatch at 0x{patch_va:08x}: "
                        f"expected {expected_bytes.hex()}, got {actual_slice.hex()}"
                    )
                code_buf[rel_off : rel_off + len(expected_bytes)] = restored_bytes
        lifted.append(lift_function_bytes(name, bytes(code_buf), start_va))
    return lifted


def compile_assemblyscript_to_wasm(
    ts_path: Path,
    wasm_path: Path,
    workspace_root: Path,
) -> None:
    asc_cmd = workspace_root / "web" / "node_modules" / ".bin" / ("asc.cmd" if os.name == "nt" else "asc")
    if not asc_cmd.exists():
        raise LifterError(f"AssemblyScript compiler not found at {asc_cmd}")
    cmd = [
        str(asc_cmd),
        str(ts_path),
        "--outFile",
        str(wasm_path),
        "--optimize",
        "--runtime",
        "stub",
        "--initialMemory",
        "512",  # 512 pages = 32 MiB linear memory (covers guest VAs up to 0x02000000, including .data and .securom)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise LifterError(f"asc compilation failed ({res.returncode}):\n{res.stdout}\n{res.stderr}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lift ProStreet x86 target functions to C99 and WebAssembly.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/local.json"),
        help="Path to local.json containing game_root",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("LOCALAPPDATA", "")) / "NFSProStreetResearch" / "phase3" / "recomp",
        help="External output directory for generated C/TS/WASM files",
    )
    args = parser.parse_args(argv)

    workspace_root = Path(__file__).resolve().parents[2]
    cfg_path = (workspace_root / args.config).resolve() if not args.config.is_absolute() else args.config.resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    game_root = Path(cfg["game_root"])
    exe_path = game_root / "Need For Spped - Pro Street" / "nfs.exe"

    out_dir = ensure_safe_paths(exe_path, args.output_dir, workspace_root, game_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    functions = read_prostreet_functions(exe_path)

    c_path = out_dir / "prostreet_lifted.c"
    ts_path = out_dir / "prostreet_lifted.ts"
    wasm_path = out_dir / "prostreet_lifted.wasm"
    manifest_path = out_dir / "lifted_manifest.json"

    header_src = (Path(__file__).resolve().parent / "x86_cpu.h").read_text(encoding="utf-8")
    (out_dir / "x86_cpu.h").write_text(header_src, encoding="utf-8")
    c_path.write_text(emit_c_module(functions, "x86_cpu.h"), encoding="utf-8")
    ts_path.write_text(emit_assemblyscript_module(functions), encoding="utf-8")

    compile_assemblyscript_to_wasm(ts_path, wasm_path, workspace_root)

    manifest = {
        "sourceExecutable": "Need For Spped - Pro Street/nfs.exe",
        "sourceSha256": EXPECTED_NFS_EXE_SHA256,
        "outputDir": str(out_dir),
        "cFile": str(c_path),
        "tsFile": str(ts_path),
        "wasmFile": str(wasm_path),
        "wasmSize": wasm_path.stat().st_size,
        "wasmSha256": hashlib.sha256(wasm_path.read_bytes()).hexdigest(),
        "functions": [
            {
                "name": fn.name,
                "startVa": f"0x{fn.start_va:08x}",
                "endVa": f"0x{fn.end_va:08x}",
                "byteLength": fn.end_va - fn.start_va + 1,
                "instructionCount": len(fn.instructions),
                "basicBlockCount": len(fn.block_leaders),
                "sha256": fn.sha256,
            }
            for fn in functions
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
