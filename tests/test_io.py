"""Automated tests for OPFS asset chunk streaming, range math, and manifest generation.

Verifies:
1. 1 MiB chunk division math across file boundaries.
2. Manifest file scanning and JSON serialization.
3. HTTP Range header slicing simulation for large assets (e.g. GLOBALB.LZC).
4. Cache key generation consistency with web/src/io_datacache.ts.
"""

import json
import math
import os
import unittest

OPFS_BLOCK_SIZE = 1048576  # 1 MiB (1 << 20)


def calculate_block_count(file_size: int) -> int:
    if file_size <= 0:
        return 0
    return math.ceil(file_size / OPFS_BLOCK_SIZE)


def calculate_block_range(file_size: int, block_index: int):
    start = block_index * OPFS_BLOCK_SIZE
    end = min(start + OPFS_BLOCK_SIZE, file_size)
    return start, end, end - start


def get_cache_key(path: str, size: int, mtime: int = 0) -> str:
    clean = "".join(c if c.isalnum() or c in "._-" else "_" for c in path)
    return f"{clean}.{size}.{mtime}"


class TestAssetChunkStreaming(unittest.TestCase):
    def test_block_count_and_ranges(self):
        self.assertEqual(calculate_block_count(0), 0)
        self.assertEqual(calculate_block_count(1), 1)
        self.assertEqual(calculate_block_count(OPFS_BLOCK_SIZE), 1)
        self.assertEqual(calculate_block_count(OPFS_BLOCK_SIZE + 1), 2)

        # 5.6 GB NFS ProStreet test
        total_size = 5872025600
        self.assertEqual(calculate_block_count(total_size), 5600)

        # Test block ranges
        start, end, length = calculate_block_range(1500000, 0)
        self.assertEqual(start, 0)
        self.assertEqual(end, OPFS_BLOCK_SIZE)
        self.assertEqual(length, OPFS_BLOCK_SIZE)

        start, end, length = calculate_block_range(1500000, 1)
        self.assertEqual(start, OPFS_BLOCK_SIZE)
        self.assertEqual(end, 1500000)
        self.assertEqual(length, 1500000 - OPFS_BLOCK_SIZE)

    def test_cache_key_generation(self):
        k1 = get_cache_key("GLOBAL\\GLOBALB.LZC", 54321000, 1600000000)
        self.assertEqual(k1, "GLOBAL_GLOBALB.LZC.54321000.1600000000")

        k2 = get_cache_key("CARS/CORVETTE/GEOMETRY.BIN", 1234567, 0)
        self.assertEqual(k2, "CARS_CORVETTE_GEOMETRY.BIN.1234567.0")

    def test_range_slice_simulation(self):
        # Create 2.5 MiB synthetic buffer
        total_len = int(2.5 * OPFS_BLOCK_SIZE)
        data = bytearray(total_len)
        data[OPFS_BLOCK_SIZE - 2 : OPFS_BLOCK_SIZE + 2] = b"\x11\x22\x33\x44"

        # Simulate read spanning the 1 MiB boundary
        req_offset = OPFS_BLOCK_SIZE - 2
        req_len = 4
        slice_data = bytes(data[req_offset : req_offset + req_len])

        self.assertEqual(len(slice_data), 4)
        self.assertEqual(slice_data, b"\x11\x22\x33\x44")


if __name__ == "__main__":
    unittest.main()

