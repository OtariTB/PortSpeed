"""Unit tests for Direct3D 9 Command Stream & Ring Buffer Protocol.

Validates runtime/d3d9_cmd.h and tools/guest_d3d9.py for lock-free
command serialization and ring buffer FIFO behavior.
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import unittest

from tools.guest_d3d9 import (
    D3D9_CMD_HEADER_SIZE,
    D3D9_RING_DEFAULT_CAPACITY,
    D3D9_RING_HEADER_SIZE,
    D3D9_RING_MAGIC,
    D3D9_RING_VERSION,
    D3DCommandType,
    D3DRingBuffer,
    D3DRingHeader,
    decode_clear,
    decode_draw_indexed_primitive,
    decode_draw_primitive,
    decode_present,
    decode_set_render_state,
    decode_set_viewport,
    encode_clear,
    encode_draw_indexed_primitive,
    encode_draw_primitive,
    encode_present,
    encode_set_render_state,
    encode_set_viewport,
    decode_create_vertex_buffer,
    decode_destroy_vertex_buffer,
    decode_set_stream_source,
    decode_update_vertex_buffer,
    encode_create_vertex_buffer,
    encode_destroy_vertex_buffer,
    encode_set_stream_source,
    encode_update_vertex_buffer,
    decode_create_index_buffer,
    decode_create_texture,
    decode_create_vertex_declaration,
    decode_destroy_index_buffer,
    decode_set_indices,
    decode_set_sampler_state,
    decode_set_texture,
    decode_set_vertex_declaration,
    decode_update_index_buffer,
    decode_update_texture,
    encode_create_index_buffer,
    encode_create_texture,
    encode_create_vertex_declaration,
    encode_destroy_index_buffer,
    encode_set_indices,
    encode_set_sampler_state,
    encode_set_texture,
    encode_set_vertex_declaration,
    encode_update_index_buffer,
    encode_update_texture,
)

WORKSPACE = Path(__file__).resolve().parent.parent


class TestD3D9CmdUnit(unittest.TestCase):
    """Unit tests for D3D9 command structures and ring buffer serialization."""

    def test_c_header_exists_and_contains_definitions(self) -> None:
        header_path = WORKSPACE / "runtime" / "d3d9_cmd.h"
        self.assertTrue(header_path.is_file(), "runtime/d3d9_cmd.h must exist")
        content = header_path.read_text(encoding="utf-8")

        self.assertIn("D3D9_RING_MAGIC", content)
        self.assertIn("0x39443344u", content)
        self.assertIn("d3d9_ring_header_t", content)
        self.assertIn("d3d9_cmd_header_t", content)
        self.assertIn("D3DCMD_DRAW_INDEXED_PRIMITIVE", content)
        self.assertIn("d3d9_ring_init", content)
        self.assertIn("D3DCMD_CREATE_VERTEX_BUFFER", content)
        self.assertIn("D3DCMD_UPDATE_VERTEX_BUFFER", content)
        self.assertIn("D3DCMD_SET_STREAM_SOURCE", content)
        self.assertIn("D3DCMD_DESTROY_VERTEX_BUFFER", content)
        self.assertIn("d3d9_cmd_update_vertex_buffer_t", content)
        self.assertIn("d3d9_cmd_destroy_vertex_buffer_t", content)
        self.assertIn("D3DCMD_UPDATE_INDEX_BUFFER", content)
        self.assertIn("D3DCMD_DESTROY_INDEX_BUFFER", content)
        self.assertIn("D3DCMD_CREATE_VERTEX_DECLARATION", content)
        self.assertIn("d3d9_cmd_update_index_buffer_t", content)
        self.assertIn("d3d9_cmd_destroy_index_buffer_t", content)
        self.assertIn("d3d9_vertex_element_t", content)
        self.assertIn("d3d9_cmd_create_vertex_declaration_t", content)
        self.assertIn("d3d9_cmd_set_vertex_declaration_t", content)

    def test_ring_header_packing_and_size(self) -> None:
        hdr = D3DRingHeader(capacity=1024)
        packed = hdr.pack()
        self.assertEqual(len(packed), D3D9_RING_HEADER_SIZE)
        self.assertEqual(len(packed), 64)

        unpacked = D3DRingHeader.unpack(packed)
        self.assertEqual(unpacked.magic, D3D9_RING_MAGIC)
        self.assertEqual(unpacked.version, D3D9_RING_VERSION)
        self.assertEqual(unpacked.capacity, 1024)
        self.assertEqual(unpacked.head, 0)
        self.assertEqual(unpacked.tail, 0)

    def test_command_clear_serialization(self) -> None:
        payload = encode_clear(flags=7, color=0xFF003366, z=1.0, stencil=0, count=0)
        self.assertEqual(len(payload), 20)

        decoded = decode_clear(payload)
        self.assertEqual(decoded["flags"], 7)
        self.assertEqual(decoded["color"], 0xFF003366)
        self.assertAlmostEqual(decoded["z"], 1.0, places=5)
        self.assertEqual(decoded["stencil"], 0)
        self.assertEqual(decoded["count"], 0)

    def test_command_set_render_state_serialization(self) -> None:
        payload = encode_set_render_state(state=137, value=1)  # D3DRS_MULTISAMPLEANTIALIAS = 1
        self.assertEqual(len(payload), 8)

        decoded = decode_set_render_state(payload)
        self.assertEqual(decoded["state"], 137)
        self.assertEqual(decoded["value"], 1)

    def test_command_set_viewport_serialization(self) -> None:
        payload = encode_set_viewport(x=0, y=0, width=1920, height=1080, min_z=0.0, max_z=1.0)
        self.assertEqual(len(payload), 24)

        decoded = decode_set_viewport(payload)
        self.assertEqual(decoded["x"], 0)
        self.assertEqual(decoded["y"], 0)
        self.assertEqual(decoded["width"], 1920)
        self.assertEqual(decoded["height"], 1080)
        self.assertAlmostEqual(decoded["min_z"], 0.0, places=5)
        self.assertAlmostEqual(decoded["max_z"], 1.0, places=5)

    def test_command_draw_primitive_serialization(self) -> None:
        payload = encode_draw_primitive(primitive_type=4, start_vertex=0, primitive_count=14612)
        self.assertEqual(len(payload), 12)

        decoded = decode_draw_primitive(payload)
        self.assertEqual(decoded["primitive_type"], 4)
        self.assertEqual(decoded["start_vertex"], 0)
        self.assertEqual(decoded["primitive_count"], 14612)

    def test_command_draw_indexed_primitive_serialization(self) -> None:
        payload = encode_draw_indexed_primitive(
            primitive_type=4,
            base_vertex_index=0,
            min_vertex_index=0,
            num_vertices=512,
            start_index=128,
            primitive_count=256,
        )
        self.assertEqual(len(payload), 24)

        decoded = decode_draw_indexed_primitive(payload)
        self.assertEqual(decoded["primitive_type"], 4)
        self.assertEqual(decoded["base_vertex_index"], 0)
        self.assertEqual(decoded["min_vertex_index"], 0)
        self.assertEqual(decoded["num_vertices"], 512)
        self.assertEqual(decoded["start_index"], 128)
        self.assertEqual(decoded["primitive_count"], 256)

    def test_command_present_serialization(self) -> None:
        payload = encode_present(x=0, y=0, w=1280, h=720)
        self.assertEqual(len(payload), 16)

        decoded = decode_present(payload)
        self.assertEqual(decoded["src_rect_x"], 0)
        self.assertEqual(decoded["src_rect_y"], 0)
        self.assertEqual(decoded["src_rect_w"], 1280)
        self.assertEqual(decoded["src_rect_h"], 720)

    def test_command_vertex_buffer_lifecycle_serialization(self) -> None:
        # 1. CREATE_VERTEX_BUFFER (20 bytes)
        create_payload = encode_create_vertex_buffer(
            buffer_id=7, length=4096, usage=0x208, fvf=0x142, pool=0
        )
        self.assertEqual(len(create_payload), 20)
        dec_create = decode_create_vertex_buffer(create_payload)
        self.assertEqual(dec_create["buffer_id"], 7)
        self.assertEqual(dec_create["length"], 4096)
        self.assertEqual(dec_create["usage"], 0x208)
        self.assertEqual(dec_create["fvf"], 0x142)
        self.assertEqual(dec_create["pool"], 0)

        # 2. UPDATE_VERTEX_BUFFER (12 bytes header + raw data)
        raw_verts = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c"
        update_payload = encode_update_vertex_buffer(buffer_id=7, offset=64, data=raw_verts)
        self.assertEqual(len(update_payload), 12 + len(raw_verts))
        dec_update = decode_update_vertex_buffer(update_payload)
        self.assertEqual(dec_update["buffer_id"], 7)
        self.assertEqual(dec_update["offset"], 64)
        self.assertEqual(dec_update["size"], 12)
        self.assertEqual(dec_update["data"], raw_verts)

        # 3. SET_STREAM_SOURCE (16 bytes)
        stream_payload = encode_set_stream_source(
            stream_number=0, buffer_id=7, offset=32, stride=24
        )
        self.assertEqual(len(stream_payload), 16)
        dec_stream = decode_set_stream_source(stream_payload)
        self.assertEqual(dec_stream["stream_number"], 0)
        self.assertEqual(dec_stream["buffer_id"], 7)
        self.assertEqual(dec_stream["offset"], 32)
        self.assertEqual(dec_stream["stride"], 24)

        # 4. DESTROY_VERTEX_BUFFER (4 bytes)
        destroy_payload = encode_destroy_vertex_buffer(buffer_id=7)
        self.assertEqual(len(destroy_payload), 4)
        dec_destroy = decode_destroy_vertex_buffer(destroy_payload)
        self.assertEqual(dec_destroy["buffer_id"], 7)

    def test_command_index_buffer_decl_texture_sampler_serialization(self) -> None:
        # 1. Index Buffer lifecycle
        ib_create = encode_create_index_buffer(buffer_id=12, length=2048, usage=8, fmt=101, pool=0)
        self.assertEqual(len(ib_create), 20)
        dec_ib = decode_create_index_buffer(ib_create)
        self.assertEqual(dec_ib["buffer_id"], 12)
        self.assertEqual(dec_ib["length"], 2048)
        self.assertEqual(dec_ib["format"], 101)

        ib_data = b"\x00\x00\x01\x00\x02\x00"
        ib_update = encode_update_index_buffer(buffer_id=12, offset=0, data=ib_data)
        dec_ib_upd = decode_update_index_buffer(ib_update)
        self.assertEqual(dec_ib_upd["buffer_id"], 12)
        self.assertEqual(dec_ib_upd["size"], 6)
        self.assertEqual(dec_ib_upd["data"], ib_data)

        ib_set = encode_set_indices(buffer_id=12)
        self.assertEqual(decode_set_indices(ib_set)["buffer_id"], 12)

        ib_destroy = encode_destroy_index_buffer(buffer_id=12)
        self.assertEqual(decode_destroy_index_buffer(ib_destroy)["buffer_id"], 12)

        # 2. Vertex Declaration lifecycle
        elems = [
            (0, 0, 2, 0, 0, 0),   # stream 0, offset 0, FLOAT3, POSITION0
            (0, 12, 4, 0, 10, 0), # stream 0, offset 12, D3DCOLOR, COLOR0
        ]
        decl_create = encode_create_vertex_declaration(decl_id=3, elements=elems)
        self.assertEqual(len(decl_create), 8 + 16)
        dec_decl = decode_create_vertex_declaration(decl_create)
        self.assertEqual(dec_decl["decl_id"], 3)
        self.assertEqual(dec_decl["element_count"], 2)
        self.assertEqual(dec_decl["elements"][0]["type"], 2)
        self.assertEqual(dec_decl["elements"][1]["offset"], 12)

        decl_set = encode_set_vertex_declaration(decl_id=3)
        self.assertEqual(decode_set_vertex_declaration(decl_set)["decl_id"], 3)

        # 3. Texture & Sampler lifecycle
        tex_create = encode_create_texture(texture_id=5, width=64, height=64, levels=1, usage=0, fmt=21, pool=1)
        self.assertEqual(len(tex_create), 28)
        dec_tex = decode_create_texture(tex_create)
        self.assertEqual(dec_tex["texture_id"], 5)
        self.assertEqual(dec_tex["width"], 64)
        self.assertEqual(dec_tex["format"], 21)

        tex_pixels = b"\xff\x00\x80\xff" * 4
        tex_upd = encode_update_texture(texture_id=5, level=0, pitch=8, width=2, height=2, data=tex_pixels)
        dec_tex_upd = decode_update_texture(tex_upd)
        self.assertEqual(dec_tex_upd["texture_id"], 5)
        self.assertEqual(dec_tex_upd["data"], tex_pixels)

        tex_bind = encode_set_texture(stage=0, texture_id=5)
        self.assertEqual(decode_set_texture(tex_bind), {"stage": 0, "texture_id": 5})

        samp = encode_set_sampler_state(sampler=0, stype=5, value=2)
        self.assertEqual(decode_set_sampler_state(samp), {"sampler": 0, "type": 5, "value": 2})

    def test_ring_buffer_fifo_lifecycle(self) -> None:
        # Small ring buffer (128 bytes payload)
        ring = D3DRingBuffer(capacity=128)
        self.assertEqual(ring.available_space, 127)
        self.assertEqual(ring.pending_bytes, 0)
        self.assertIsNone(ring.read_command())

        # Write CLEAR (8 byte header + 20 byte payload = 28 bytes)
        clear_bytes = encode_clear(7, 0xFF000000, 1.0, 0)
        ok = ring.write_command(D3DCommandType.CLEAR, clear_bytes)
        self.assertTrue(ok)
        self.assertEqual(ring.pending_bytes, 28)
        self.assertEqual(ring.available_space, 127 - 28)

        # Write SET_RENDER_STATE (8 byte header + 8 byte payload = 16 bytes)
        rs_bytes = encode_set_render_state(7, 1)
        ok = ring.write_command(D3DCommandType.SET_RENDER_STATE, rs_bytes)
        self.assertTrue(ok)
        self.assertEqual(ring.pending_bytes, 28 + 16)

        # Read back in FIFO order
        res1 = ring.read_command()
        self.assertIsNotNone(res1)
        cmd_type1, _, payload1 = res1
        self.assertEqual(cmd_type1, D3DCommandType.CLEAR)
        self.assertEqual(decode_clear(payload1)["color"], 0xFF000000)

        res2 = ring.read_command()
        self.assertIsNotNone(res2)
        cmd_type2, _, payload2 = res2
        self.assertEqual(cmd_type2, D3DCommandType.SET_RENDER_STATE)
        self.assertEqual(decode_set_render_state(payload2)["state"], 7)

        # Buffer is now empty
        self.assertEqual(ring.pending_bytes, 0)
        self.assertIsNone(ring.read_command())

    def test_ring_buffer_wrap_around(self) -> None:
        # Capacity 64 bytes
        ring = D3DRingBuffer(capacity=64)

        # Each command: 8 + 8 = 16 bytes
        rs_bytes = encode_set_render_state(1, 100)

        # Write 3 commands (48 bytes)
        for i in range(3):
            self.assertTrue(ring.write_command(D3DCommandType.SET_RENDER_STATE, encode_set_render_state(i, 100 + i)))

        # Read 2 commands (releases 32 bytes from front, tail moves to 32)
        r0 = ring.read_command()
        self.assertEqual(decode_set_render_state(r0[2])["state"], 0)
        r1 = ring.read_command()
        self.assertEqual(decode_set_render_state(r1[2])["state"], 1)

        # Now write 2 more commands (should wrap around the 64 byte boundary)
        self.assertTrue(ring.write_command(D3DCommandType.SET_RENDER_STATE, encode_set_render_state(3, 103)))
        self.assertTrue(ring.write_command(D3DCommandType.SET_RENDER_STATE, encode_set_render_state(4, 104)))

        # Read remaining 3 commands (index 2, 3, 4)
        r2 = ring.read_command()
        self.assertEqual(decode_set_render_state(r2[2])["state"], 2)
        r3 = ring.read_command()
        self.assertEqual(decode_set_render_state(r3[2])["state"], 3)
        r4 = ring.read_command()
        self.assertEqual(decode_set_render_state(r4[2])["state"], 4)

        self.assertIsNone(ring.read_command())
        self.assertEqual(ring.pending_bytes, 0)

    def test_ring_buffer_overflow_protection(self) -> None:
        ring = D3DRingBuffer(capacity=32)
        # Attempt to write larger than capacity
        big_payload = b"\x00" * 40
        ok = ring.write_command(D3DCommandType.NOP, big_payload)
        self.assertFalse(ok)
        self.assertEqual(ring.hdr.dropped_frames, 1)


if __name__ == "__main__":
    unittest.main()
