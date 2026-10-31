"""Inspect and disassemble vs_2_0 in IDI_STANDARD_FX."""
import struct
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from tools.build_win32_shims import EXE_PATH
from tools.inventory_effects import parse_pe_resources
from tools.d3dx9_effect import D3DX9EffectParser


def disassemble_d3d9(bytecode: bytes):
    # D3D9 tokenized shader instruction opcodes
    OPCODES = {
        0: "nop",
        1: "mov",
        2: "add",
        3: "sub",
        4: "mad",
        5: "mul",
        6: "rcp",
        7: "rsq",
        8: "dp3",
        9: "dp4",
        10: "min",
        11: "max",
        12: "slt",
        13: "sge",
        14: "exp",
        15: "log",
        16: "lit",
        17: "dst",
        18: "lrp",
        19: "frc",
        20: "m4x4",
        21: "m4x3",
        22: "m3x4",
        23: "m3x3",
        24: "m3x2",
        25: "call",
        26: "callnz",
        27: "loop",
        28: "ret",
        29: "endloop",
        30: "label",
        31: "dcl",
        32: "pow",
        33: "crs",
        34: "sgn",
        35: "abs",
        36: "nrm",
        37: "sincos",
        38: "rep",
        39: "endrep",
        40: "if",
        41: "ifc",
        42: "else",
        43: "endif",
        44: "break",
        45: "breakc",
        46: "mova",
        47: "defb",
        48: "defi",
        81: "def",
    }

    # Register types
    REG_TYPES = {
        0: "r",       # Temp
        1: "v",       # Input
        2: "c",       # Const float
        3: "addr/a0", # Address
        4: "t",       # Texture coord
        5: "raster/o",# Rasterizer output / oPos, etc
        6: "oColor",  # Output color
        7: "oDepth",  # Output depth
        8: "s",       # Sampler
        9: "constint",# Const int
        10: "o",      # Output (VS 3.0 / PS 3.0)
    }

    words = [struct.unpack_from('<I', bytecode, i)[0] for i in range(0, len(bytecode), 4)]
    print(f"Header token: 0x{words[0]:08x}")
    idx = 1
    instructions = []

    while idx < len(words):
        token = words[idx]
        if token == 0x0000FFFF:
            instructions.append("end")
            break

        # Check comment token 0xFFFE....
        if (token & 0xFFFF0000) == 0x0000FFFE or (token & 0x0000FFFF) == 0xFFFE:
            comment_len = (token >> 16) & 0xFFFF
            idx += 1 + comment_len
            continue

        opcode = token & 0x0000FFFF
        op_name = OPCODES.get(opcode, f"op_{opcode}")
        inst_len = (token >> 24) & 0x0F  # in shader model 2_0, token length is often in bits 24..27

        # Let's collect tokens for this instruction
        inst_tokens = [token]
        # In SM 2.0, if length is 0, we inspect destination and sources
        # Let's inspect words following opcode
        idx += 1
        instructions.append((op_name, opcode, token))

    return instructions, words


def main():
    data = EXE_PATH.read_bytes()
    entries = parse_pe_resources(data)
    entry = [e for e in entries if e[0] == 'IDI_STANDARD_FX'][0]
    fx = data[entry[3] : entry[3] + entry[1]]

    parser = D3DX9EffectParser(fx)
    effect = parser.parse()

    vs20 = [s for s in effect.shaders if s.target == 'vs_2_0'][0]
    print(f"Selected VS 2.0 at offset 0x{vs20.offset:04x}, length {vs20.length} bytes")
    print(f"Creator: {vs20.creator}")
    print(f"Constants ({len(vs20.constants)}):")
    for c in vs20.constants:
        print(f"  {c.name}: {c.register_set}[{c.register_index}..{c.register_index+c.register_count-1}]")

    # Raw words
    words = [struct.unpack_from('<I', vs20.bytecode, i)[0] for i in range(0, len(vs20.bytecode), 4)]
    print(f"\nTotal 32-bit words: {len(words)}")
    for i, w in enumerate(words):
        print(f"  [{i:02d}] 0x{i*4:03x}: 0x{w:08x}")


if __name__ == "__main__":
    main()
