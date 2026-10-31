import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from geometry import parse_geometry_directory, parse_solid, decompress_and_parse_part
from tpk import FormatError
from fixture_tpk import chunk


def _build_synthetic_solid(part_hash=0x11223344, name=b'240SX_SYNTH_A\0'):
    # 0x00134011: aligned payload starts at offset 0x10 inside 0x80134010
    hdr_payload = bytearray(216)
    struct.pack_into('<I', hdr_payload, 0x10, part_hash)
    struct.pack_into('<H', hdr_payload, 0x14, 1)  # 1 triangle
    struct.pack_into('<3f', hdr_payload, 0x20, -1.0, -1.0, 0.0)
    struct.pack_into('<3f', hdr_payload, 0x30, 1.0, 1.0, 1.0)
    struct.pack_into('<16f', hdr_payload, 0x40, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    hdr_payload[0xb8:0xb8 + len(name)] = name
    c_011 = chunk(0x00134011, bytes(hdr_payload))

    c_012 = chunk(0x00134012, struct.pack('<II', 0x039cbe0b, 0))
    c_013 = chunk(0x00134013, struct.pack('<II', 0xd6d6080a, 0))

    # Build 0x80134100 children ensuring exact 16/128/32-byte alignment relative to solid buffer start
    out = bytearray(struct.pack('<II', 0x80134010, 0))
    out += c_011 + c_012 + c_013
    mesh_container_pos = len(out)
    out += struct.pack('<II', 0x80134100, 0)

    # 1. 0x00134900 (16-byte aligned payload at (q + 0x17) & ~0x0f)
    q = len(out)
    al = (q + 0x17) & ~0x0f
    pad = al - (q + 8)
    m900 = bytearray(pad + 56)
    struct.pack_into('<I', m900, pad + 16, 1)  # 1 submesh
    struct.pack_into('<I', m900, pad + 40, 1)  # 1 triangle
    struct.pack_into('<I', m900, pad + 48, 3)  # 3 vertices
    out += chunk(0x00134900, bytes(m900))

    # 2. 0x00134b02 (128-byte aligned payload at (q + 0x87) & ~0x7f)
    q = len(out)
    al = (q + 0x87) & ~0x7f
    pad = al - (q + 8)
    mb02 = bytearray(pad + 128)
    struct.pack_into('<I', mb02, pad + 0x00, 0)  # idx_start = 0
    mb02[pad + 0x1c:pad + 0x21] = bytes([0, 0xff, 0xff, 0xff, 0xff])
    struct.pack_into('<I', mb02, pad + 0x24, 0xd6d6080a)
    struct.pack_into('<I', mb02, pad + 0x2c, 3)  # 3 indices
    struct.pack_into('<I', mb02, pad + 0x4c, 96)  # 3 * 32 bytes
    struct.pack_into('<H', mb02, pad + 0x52, 32)  # stride = 32
    out += chunk(0x00134b02, bytes(mb02))

    # 3. 0x00134b01 (128-byte aligned payload at (q + 0x87) & ~0x7f)
    q = len(out)
    al = (q + 0x87) & ~0x7f
    pad = al - (q + 8)
    verts = bytearray(pad)
    for vx, vy, vz in ((-3277, 0, 0), (3277, 0, 0), (0, 3277, 3277)):
        v = bytearray(32)
        struct.pack_into('<6h', v, 0, vx, vy, vz, 3277, 0, 0)
        v[12:16] = bytes([255, 255, 255, 255])
        struct.pack_into('<4h', v, 16, 0, 0, 32767, 32767)
        verts += v
    out += chunk(0x00134b01, bytes(verts))

    # 4. 0x00134b03 (32-byte aligned payload at (q + 0x27) & ~0x1f)
    q = len(out)
    al = (q + 0x27) & ~0x1f
    pad = al - (q + 8)
    ib = bytes(pad) + struct.pack('<4H', 0, 1, 2, 0)
    out += chunk(0x00134b03, ib)

    struct.pack_into('<I', out, mesh_container_pos + 4, len(out) - mesh_container_pos - 8)
    struct.pack_into('<I', out, 4, len(out) - 8)
    return bytes(out)


def _jdlz_literal_compress(raw):
    hdr = bytearray(18)
    hdr[:4] = b'JDLZ'
    hdr[4] = 2
    hdr[5] = 0x10
    struct.pack_into('<I', hdr, 8, len(raw))
    body = bytearray()
    for off in range(0, len(raw), 8):
        body += raw[off:off + 8]
        if off + 8 < len(raw):
            body += b'\x00'
    stream = bytes(hdr + body)
    stream = stream[:12] + struct.pack('<I', len(stream)) + stream[16:]
    while len(stream) % 4 != 0:
        stream += b'\x00'
    return stream


def _build_synthetic_geometry_bin():
    solid = _build_synthetic_solid()
    jdlz = _jdlz_literal_compress(solid)
    cip = struct.pack('<6I', 0x55441122, len(solid), 24 + len(jdlz), 0, 0, 0) + jdlz

    info = bytearray(144)
    struct.pack_into('<I', info, 12, 1)
    c_002 = chunk(0x00134002, bytes(info))
    c_003 = chunk(0x00134003, struct.pack('<II', 0x11223344, 0))
    # foff is right after 0x80134000(8) + 0x80134001(8 + len(c_002) + len(c_003) + 32)
    foff = 8 + 8 + len(c_002) + len(c_003) + 32
    c_004 = chunk(0x00134004, struct.pack('<6I', 0x11223344, foff, len(cip), len(solid), 0x200, 0))
    dir_chunk = chunk(0x80134001, c_002 + c_003 + c_004)
    return chunk(0x80134000, dir_chunk + cip)


class GeometryTests(unittest.TestCase):
    def test_synthetic_solid_and_geometry_container(self):
        geom_bin = _build_synthetic_geometry_bin()
        entries = parse_geometry_directory(geom_bin)
        self.assertEqual(len(entries), 1)
        mesh = decompress_and_parse_part(geom_bin, entries[0])
        self.assertEqual(mesh.name, '240SX_SYNTH_A')
        self.assertEqual((mesh.num_tris, mesh.num_verts, len(mesh.submeshes)), (1, 3, 1))
        self.assertEqual(mesh.submeshes[0].indices, [0, 1, 2])
        self.assertAlmostEqual(mesh.submeshes[0].positions[0][0], -1.0, places=4)
        self.assertAlmostEqual(mesh.submeshes[0].normals[0][2], 1.0, places=4)

    def test_rejects_malformed_and_truncated_geometry(self):
        geom_bin = _build_synthetic_geometry_bin()
        for cut in (0, 7, 16, 48, len(geom_bin) - 1):
            with self.assertRaises(FormatError):
                parse_geometry_directory(geom_bin[:cut])
        solid = bytearray(_build_synthetic_solid())
        with self.assertRaises(FormatError):
            parse_solid(bytes(solid), expected_hash=0xdeadbeef)


if __name__ == '__main__':
    unittest.main()
