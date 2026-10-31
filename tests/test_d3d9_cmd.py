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
