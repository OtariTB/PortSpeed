"""Synthetic tests only: never requires or creates original game content."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from pe_headers import inspect_pe
from recon import inventory, validate_paths, WORKSPACE


def synthetic_pe(is64=False):
    data = bytearray(1024)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    opt = 0x98
    size = 240 if is64 else 224
    struct.pack_into('<HHIIIHH', data, 0x84, 0x8664 if is64 else 0x14c, 1, 0, 0, 0, size, 2)
    struct.pack_into('<H', data, opt, 0x20b if is64 else 0x10b)
    struct.pack_into('<I', data, opt + 60, 512)
    directory = opt + (112 if is64 else 96)
    struct.pack_into('<I', data, directory - 4, 16)
    struct.pack_into('<II', data, directory + 8, 0x1000, 40)
    struct.pack_into('<8sIIIIIIHHI', data, opt + size, b'.idata', 512, 0x1000, 512, 512, 0, 0, 0, 0, 0)
    struct.pack_into('<IIIII', data, 512, 0, 0, 0, 0x1040, 0)
    data[576:589] = b'EXAMPLE.dll\0\0\0'
    return data


class ReconTests(unittest.TestCase):
    def test_pe32_and_pe64_imports(self):
        for is64 in (False, True):
            result = inspect_pe(synthetic_pe(is64))
            self.assertEqual(result['bits'], 64 if is64 else 32)
            self.assertEqual(result['imports'], ['EXAMPLE.dll'])
            self.assertEqual(result['warnings'], [])

    def test_truncated(self):
        data = synthetic_pe()
        for length in (0, 2, 63, 130, 180, 400):
            with self.assertRaises(ValueError):
                inspect_pe(data[:length])

    def test_bad_import_rva(self):
        data = synthetic_pe()
        struct.pack_into('<I', data, 524, 0x90000000)
        self.assertTrue(inspect_pe(data)['warnings'])

    def test_delay_imports(self):
        data = synthetic_pe()
        struct.pack_into('<II', data, 0x98 + 96 + 13 * 8, 0x1080, 64)
        struct.pack_into('<IIIIIIII', data, 640, 1, 0x1040, 0, 0, 0, 0, 0, 0)
        self.assertEqual(inspect_pe(data)['delay_imports'], ['EXAMPLE.dll'])

    def test_inventory_preserves_bytes_and_reports_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'unknown.bin'
            original = bytes(range(256))
            p.write_bytes(original)
            before = p.stat().st_mtime_ns
            result = inventory(Path(temp), True)
            self.assertEqual(p.read_bytes(), original)
            self.assertEqual(p.stat().st_mtime_ns, before)
            self.assertEqual(result['files'][0]['sha256'], hashlib.sha256(original).hexdigest())
            self.assertEqual(result['errors'], [])

    def test_output_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            for output in (source, source / 'report', source.parent, WORKSPACE / 'tools'):
                with self.assertRaises(ValueError):
                    validate_paths(source, output)
            validate_paths(source, WORKSPACE / 'research/local/test-output')


if __name__ == '__main__':
    unittest.main()
