import struct
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from archive_headers import big4_index,jdlz_header
from tpk import FormatError


class ArchiveTests(unittest.TestCase):
    def sample(self):
        return b'BIG4'+struct.pack('<I',30)+struct.pack('>II',1,26)+struct.pack('>II',26,4)+b'a\0DATA'

    def test_mixed_endian_big4(self):
        r=big4_index(self.sample())
        self.assertEqual(r['entries'],[{'name':'a','offset':26,'size':4}])

    def test_big4_truncations(self):
        for n in range(30):
            with self.assertRaises(FormatError):big4_index(self.sample()[:n])

    def test_big4_bounds_count_and_name(self):
        for offset,value in [(8,100000),(12,31),(16,0),(16,0xffffffff),(20,5)]:
            b=bytearray(self.sample());struct.pack_into('>I',b,offset,value)
            with self.assertRaises(FormatError):big4_index(b)
        b=bytearray(self.sample());b[25]=65
        with self.assertRaises(FormatError):big4_index(b)

    def test_jdlz_header_only(self):
        b=b'JDLZ\x02\x10\0\0'+struct.pack('<II',4,20)
        self.assertFalse(jdlz_header(b,20)['payload_validated'])
        for header,size in [(b,19),(b[:15],20),(b'BAD!'+b[4:],20)]:
            with self.assertRaises(FormatError):jdlz_header(header,size)


if __name__=='__main__':unittest.main()
