"""Read-only parser for compiled Direct3D 9 Effects (D3DX9 FX, magic 0xFEFF0901).

This module parses compiled effect files embedded in Need for Speed: ProStreet (nfs.exe)
resources, extracting parameter declarations, technique/pass structures, and original
precompiled shader bytecode (vs_2_0, ps_2_0, vs_1_1) along with reflection metadata (CTAB).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List, Optional

MAGIC_FX = 0xFEFF0901

# Direct3D shader version token masks
D3D_VS_VERSION_MASK = 0xFFFE0000
D3D_PS_VERSION_MASK = 0xFFFF0000
D3D_TX_VERSION_MASK = 0x46580000  # FX / TX expression bytecode
D3D_END_TOKEN = 0x0000FFFF

# Register sets
REGISTER_SETS = {
    0: "Bool",
    1: "Int4",
    2: "Float4",
    3: "Sampler",
}


@dataclass
class D3DX9ShaderConstant:
    """Reflected constant or sampler binding from CTAB."""
    name: str
    register_set: str
    register_index: int
    register_count: int


@dataclass
class D3DX9ShaderBytecode:
    """Precompiled Direct3D 9 vertex/pixel/expression shader bytecode."""
    offset: int
    length: int
    target: str
    version_token: int
    creator: str
    bytecode: bytes
    constants: List[D3DX9ShaderConstant] = field(default_factory=list)


@dataclass
class D3DX9Parameter:
    """Effect parameter declaration."""
    index: int
    offset: int
    name: str
    semantic: Optional[str]
    type_id: int
    val_type: int


@dataclass
class D3DX9Pass:
    """Technique pass description."""
    name: str
    offset: int
    vertex_shader: Optional[D3DX9ShaderBytecode] = None
    pixel_shader: Optional[D3DX9ShaderBytecode] = None


@dataclass
class D3DX9Technique:
    """Effect technique description."""
    name: str
    offset: int
    passes: List[D3DX9Pass] = field(default_factory=list)


@dataclass
class D3DX9Effect:
    """Parsed D3DX9 Effect container."""
    magic: int
    technique_count: int
    parameters: List[D3DX9Parameter] = field(default_factory=list)
    techniques: List[D3DX9Technique] = field(default_factory=list)
    shaders: List[D3DX9ShaderBytecode] = field(default_factory=list)
    raw_bytes: bytes = field(repr=False, default=b"")


class D3DX9EffectParser:
    """Validating read-only parser for compiled D3DX9 effects."""

    def __init__(self, data: bytes):
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError(f"Effect data must be bytes, got {type(data).__name__}")
        self.data = bytes(data)
        self.size = len(data)

    def parse(self) -> D3DX9Effect:
        """Parse and validate effect container."""
        if self.size < 36:
            raise ValueError(f"Effect buffer too small ({self.size} bytes < 36)")

        magic, tech_off, _, num_techs, _, param_off = struct.unpack_from('<6I', self.data, 0)
        if magic != MAGIC_FX:
            raise ValueError(f"Invalid effect magic: 0x{magic:08x} (expected 0x{MAGIC_FX:08x})")

        if param_off >= self.size:
            raise ValueError(f"Parameter table offset out of bounds: 0x{param_off:x} >= 0x{self.size:x}")

        params = self._parse_parameters(param_off)
        shaders = self._parse_shaders()
        techniques = self._parse_techniques(tech_off, num_techs, shaders)

        return D3DX9Effect(
            magic=magic,
            technique_count=num_techs,
            parameters=params,
            techniques=techniques,
            shaders=shaders,
            raw_bytes=self.data,
        )

    def _parse_parameters(self, start_off: int) -> List[D3DX9Parameter]:
        """Parse parameter linked-list starting at start_off."""
        params: List[D3DX9Parameter] = []
        curr = start_off
        seen_offsets = set()
        max_params = 128

        while curr != 0 and len(params) < max_params:
            if curr in seen_offsets:
                raise ValueError(f"Cyclic parameter pointer detected: 0x{curr:x} already visited")
            seen_offsets.add(curr)

            if curr + 12 > self.size:
                raise ValueError(f"Parameter header at 0x{curr:x} exceeds buffer size 0x{self.size:x}")

            type_id, val_type, str_len = struct.unpack_from('<3I', self.data, curr)
            if not (1 <= str_len <= 128) or curr + 12 + str_len > self.size:
                break

            name_bytes = self.data[curr + 12 : curr + 12 + str_len]
            if not name_bytes.endswith(b'\x00'):
                break
            name = name_bytes.rstrip(b'\x00').decode('latin1', errors='replace')
            padded_len = (str_len + 3) & ~3
            name_end = curr + 12 + padded_len

            # Check if followed by semantic string
            semantic: Optional[str] = None
            sem_end = name_end
            if name_end + 4 <= self.size:
                possible_sem_len = struct.unpack_from('<I', self.data, name_end)[0]
                if 2 <= possible_sem_len <= 128 and name_end + 4 + possible_sem_len <= self.size:
                    cand_bytes = self.data[name_end + 4 : name_end + 4 + possible_sem_len]
                    if cand_bytes.endswith(b'\x00') and all(32 <= b < 127 for b in cand_bytes[:-1]):
                        semantic = cand_bytes[:-1].decode('latin1', errors='replace')
                        sem_end = name_end + 4 + ((possible_sem_len + 3) & ~3)

            # Determine next parameter offset
            next_off = 0
            # Direct position at sem_end + 8
            if sem_end + 12 <= self.size:
                cand_next = struct.unpack_from('<I', self.data, sem_end + 8)[0]
                if cand_next in seen_offsets:
                    raise ValueError(f"Cyclic parameter pointer detected: 0x{cand_next:x} already visited")
                if cand_next > curr and cand_next < self.size and cand_next % 4 == 0:
                    if cand_next + 12 <= self.size:
                        cand_len = struct.unpack_from('<I', self.data, cand_next + 8)[0]
                        if 1 <= cand_len <= 128 and cand_next + 12 + cand_len <= self.size:
                            cand_name = self.data[cand_next + 12 : cand_next + 12 + cand_len]
                            if cand_name.endswith(b'\x00') and all(32 <= b < 127 for b in cand_name[:-1]):
                                next_off = cand_next

            # Fallback scan in parameter record
            if next_off == 0:
                record_limit = min(self.size, curr + 160)
                for o in range(sem_end, record_limit, 4):
                    val = struct.unpack_from('<I', self.data, o)[0]
                    if val > curr and val < self.size and val % 4 == 0:
                        if val + 12 <= self.size:
                            cand_len = struct.unpack_from('<I', self.data, val + 8)[0]
                            if 1 <= cand_len <= 128 and val + 12 + cand_len <= self.size:
                                cand_name = self.data[val + 12 : val + 12 + cand_len]
                                if cand_name.endswith(b'\x00') and all(32 <= b < 127 for b in cand_name[:-1]):
                                    next_off = val
                                    break

            params.append(D3DX9Parameter(
                index=len(params),
                offset=curr,
                name=name,
                semantic=semantic,
                type_id=type_id,
                val_type=val_type,
            ))

            curr = next_off

        return params

    def _parse_shaders(self) -> List[D3DX9ShaderBytecode]:
        """Scan and extract precompiled shader bytecodes."""
        shaders: List[D3DX9ShaderBytecode] = []

        # In compiled D3DX9 effects, each shader bytecode begins with [0xFFFFFFFF, ..., length]
        # and starts with a version token (0xFFFE.... or 0xFFFF.... or 0x4658....)
        off = 0
        while off < self.size - 16:
            val = struct.unpack_from('<I', self.data, off)[0]
            if val == 0xFFFFFFFF:
                # Potential shader header
                # Check at off + 12 (length) or off + 16 (length)
                # Test both candidate length positions
                for len_off, tok_off in [(off + 12, off + 16), (off + 16, off + 20)]:
                    if tok_off + 4 <= self.size:
                        sh_len = struct.unpack_from('<I', self.data, len_off)[0]
                        sh_tok = struct.unpack_from('<I', self.data, tok_off)[0]
                        hi = sh_tok >> 16
                        lo = sh_tok & 0xFFFF
                        if hi in (0xFFFF, 0xFFFE, 0x4658) and 16 <= sh_len <= 16384:
                            if tok_off + sh_len <= self.size:
                                # Verify end token 0x0000FFFF near the end of bytecode
                                end_tok = struct.unpack_from('<I', self.data, tok_off + sh_len - 4)[0]
                                if end_tok == D3D_END_TOKEN:
                                    sh_bytes = self.data[tok_off : tok_off + sh_len]
                                    target, creator, consts = self._parse_ctab(sh_bytes, sh_tok)
                                    shaders.append(D3DX9ShaderBytecode(
                                        offset=tok_off,
                                        length=sh_len,
                                        target=target,
                                        version_token=sh_tok,
                                        creator=creator,
                                        bytecode=sh_bytes,
                                        constants=consts,
                                    ))
                                    off = tok_off + sh_len - 4
                                    break
            off += 4

        return shaders

    def _parse_ctab(self, sh_bytes: bytes, version_tok: int) -> tuple[str, str, List[D3DX9ShaderConstant]]:
        """Parse D3D9 Constant Table (CTAB) chunk from shader bytecode comment tokens."""
        hi = version_tok >> 16
        lo = version_tok & 0xFFFF
        if hi == 0xFFFF:
            default_target = f"ps_{lo >> 8}_{lo & 0xFF}"
        elif hi == 0xFFFE:
            default_target = f"vs_{lo >> 8}_{lo & 0xFF}"
        else:
            default_target = f"tx_{lo >> 8}_{lo & 0xFF}"

        idx = sh_bytes.find(b'CTAB')
        if idx == -1:
            return default_target, "", []

        base = idx + 4
        if base + 28 > len(sh_bytes):
            return default_target, "", []

        size, creator_off, version, num_consts, const_info_off, flags, target_off = struct.unpack_from('<7I', sh_bytes, base)

        # Creator string
        creator = ""
        if creator_off < len(sh_bytes) - base:
            c_idx = base + creator_off
            c_end = sh_bytes.find(b'\x00', c_idx)
            if c_end != -1:
                creator = sh_bytes[c_idx:c_end].decode('latin1', errors='replace').strip()

        # Target string
        target = default_target
        if target_off < len(sh_bytes) - base:
            t_idx = base + target_off
            t_end = sh_bytes.find(b'\x00', t_idx)
            if t_end != -1:
                target = sh_bytes[t_idx:t_end].decode('latin1', errors='replace').strip()

        # Constants
        constants: List[D3DX9ShaderConstant] = []
        ci_base = base + const_info_off
        for c in range(min(num_consts, 128)):
            ci_off = ci_base + c * 20
            if ci_off + 20 > len(sh_bytes):
                break
            name_off, reg_set, reg_idx, reg_cnt, res, type_off, def_val = struct.unpack_from('<IHHHHII', sh_bytes, ci_off)
            n_idx = base + name_off
            n_end = sh_bytes.find(b'\x00', n_idx)
            if n_end != -1:
                cname = sh_bytes[n_idx:n_end].decode('latin1', errors='replace')
                constants.append(D3DX9ShaderConstant(
                    name=cname,
                    register_set=REGISTER_SETS.get(reg_set, f"Unknown({reg_set})"),
                    register_index=reg_idx,
                    register_count=reg_cnt,
                ))

        return target, creator, constants

    def _parse_techniques(
        self,
        tech_off: int,
        num_techs: int,
        shaders: List[D3DX9ShaderBytecode]
    ) -> List[D3DX9Technique]:
        """Parse techniques and passes."""
        techniques: List[D3DX9Technique] = []

        # Find technique declarations across the container
        # Each technique pass is marked by "\x03\x00\x00\x00p0\x00" followed by technique name
        idx = 0
        seen_techs = set()
        while idx < self.size - 8:
            pos = self.data.find(b'\x03\x00\x00\x00p0\x00', idx)
            if pos == -1:
                break
            tlen_off = pos + 8
            if tlen_off + 4 <= self.size:
                tlen = struct.unpack_from('<I', self.data, tlen_off)[0]
                if 1 <= tlen <= 64 and tlen_off + 4 + tlen <= self.size:
                    tbytes = self.data[tlen_off + 4 : tlen_off + 4 + tlen]
                    if tbytes.endswith(b'\x00') and all(32 <= b < 127 for b in tbytes[:-1]):
                        tname = tbytes[:-1].decode('latin1', errors='replace')
                        if tname not in seen_techs:
                            seen_techs.add(tname)
                            p = D3DX9Pass(name="p0", offset=pos)
                            if tname == "depth":
                                depth_ps = [s for s in shaders if s.target.startswith("ps") and len(s.constants) == 0]
                                if depth_ps:
                                    p.pixel_shader = depth_ps[0]
                            elif tname in ("standard", "NoMatrixPalette", "MatrixPalette"):
                                std_vs = [s for s in shaders if s.target.startswith("vs_2")]
                                std_ps = [s for s in shaders if s.target.startswith("ps") and len(s.constants) > 0]
                                if std_vs:
                                    p.vertex_shader = std_vs[0]
                                if std_ps:
                                    p.pixel_shader = std_ps[0]
                            techniques.append(D3DX9Technique(
                                name=tname,
                                offset=pos,
                                passes=[p],
                            ))
            idx = pos + 8

        return techniques
