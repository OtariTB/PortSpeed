import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from tpk import (
    parse_tpk,
    texture_payload,
    decode_bc1,
    decode_bc2,
    decode_bc3,
    decode_dxt,
    jdlz_decompress,
    huff_decompress,
    cip_decompress,
    chunks,
    flatten,
    FormatError,
)
from fixture_tpk import fixture, chunk


class TpkTests(unittest.TestCase):
    def setUp(self):
        self.data=fixture()
        self.nodes={c.tag:c for c in flatten(chunks(self.data))}
        self.record=self.nodes[0x33310004].start

    def reject(self,data):
        with self.assertRaises(FormatError):parse_tpk(data)

    def test_synthetic_texture(self):
        t,=parse_tpk(self.data)
        self.assertEqual((t.name,t.width,t.height,t.fourcc),('RED',4,4,'DXT5'))
        self.assertEqual(decode_bc3(self.data[t.data_offset:t.data_offset+16],4,4),bytes([255,0,0,255])*16)

    def test_every_truncation(self):
        for n in range(len(self.data)):
            with self.subTest(length=n):self.reject(self.data[:n])

    def test_header_endianness_and_overflow(self):
        for value in (0,0xffffffff,1):
            b=bytearray(self.data);struct.pack_into('<I',b,4,value);self.reject(b)
        b=bytearray(self.data);b[:8]=struct.pack('>II',0xb3300000,len(b)-8);self.reject(b)

    def test_bad_fields(self):
        mutations=[(12,'I',7),(20,'I',0xffffffff),(28,'I',17),(36,'I',8),
                   (40,'H',0),(42,'H',5000),(46,'B',0),(50,'B',0),(50,'B',32),(88,'B',255)]
        for offset,fmt,value in mutations:
            with self.subTest(offset=offset,value=value):
                b=bytearray(self.data);struct.pack_into('<'+fmt,b,self.record+offset,value);self.reject(b)

    def test_names_padding_version_format(self):
        offsets=[self.record+92,self.nodes[0x33320002].start,self.nodes[0x33310001].start,self.nodes[0x33310005].start+12]
        for offset in offsets:
            b=bytearray(self.data);b[offset]^=0xff;self.reject(b)

    def test_count_mismatch(self):
        b=bytearray(self.data);struct.pack_into('<I',b,self.nodes[0x33310002].offset+4,7);self.reject(b)

    def test_compressed_rejected(self):
        b=bytearray(self.data);struct.pack_into('<I',b,self.nodes[0x33310004].offset,0x33310003);self.reject(b)

    def test_duplicate_chunk(self):
        body=self.data[8:]+chunk(0x33310001,bytes(124))
        self.reject(chunk(0xb3300000,body))

    def test_nesting_limit(self):
        b=b''
        for _ in range(20):b=chunk(0x80000001,b)
        self.reject(b)

    def test_overlapping_texture_ranges(self):
        original=self.data
        info=self.nodes[0x33310001];r=self.nodes[0x33310004];f=self.nodes[0x33310005];d=self.nodes[0x33320002]
        second=bytearray(original[r.start:r.end]);struct.pack_into('<I',second,12,0x12345679)
        meta=chunk(0x33310001,original[info.start:info.end])+chunk(0x33310002,struct.pack('<IIII',0x12345678,0,0x12345679,0))
        meta+=chunk(0x33310004,original[r.start:r.end]+second)+chunk(0x33310005,original[f.start:f.end]*2)
        b=chunk(0xb3300000,chunk(0xb3310000,meta)+chunk(0xb3320000,chunk(0x33320002,original[d.start:d.end])))
        with self.assertRaisesRegex(FormatError,'overlapping'):parse_tpk(b)

    def test_two_mip_levels(self):
        b=bytearray(self.data)
        struct.pack_into('<I',b,self.record+28,32);b[self.record+50]=2
        # Append a second 16-byte block for the 2x2 level and update ancestor lengths.
        for tag in (0xb3300000,0xb3320000,0x33320002):
            node=self.nodes[tag];struct.pack_into('<I',b,node.offset+4,node.end-node.start+16)
        b+=self.data[-16:]
        t,=parse_tpk(b)
        self.assertEqual((t.mip_count,t.data_size,t.base_size),(2,32,16))

    def test_bc3_length_and_partial_blocks(self):
        block=bytes([255,0])+bytes(6)+struct.pack('<HHI',0xf800,0,0)
        self.assertEqual(decode_bc3(block,1,1),bytes([255,0,0,255]))
        for data,w,h in [(block[:-1],4,4),(block+b'x',4,4),(block,0,4),(block,4097,4)]:
            with self.assertRaises(FormatError):decode_bc3(data,w,h)

    def test_alpha_modes_and_color_interpolation(self):
        for a0,a1,expected in [(255,0,[255,0,218,182,145,109,72,36]),(0,255,[0,255,51,102,153,204,0,255])]:
            indices=sum((j%8)<<(3*j) for j in range(16))
            block=bytes([a0,a1])+indices.to_bytes(6,'little')+struct.pack('<HHI',0xf800,0x07e0,0xaaaaaaaa)
            rgba=decode_bc3(block,4,4)
            self.assertEqual(list(rgba[3::4]),expected*2)
            self.assertEqual(rgba[:3],bytes([170,85,0]))

    def test_bc1_and_bc2_modes(self):
        # BC1 4-color mode (c0 > c1) and 1-bit alpha mode (c0 <= c1)
        blk_4col = struct.pack('<HHI', 0xf800, 0x07e0, 0xaaaaaaaa)
        rgba_4 = decode_bc1(blk_4col, 4, 4)
        self.assertEqual(rgba_4[:4], bytes([170, 85, 0, 255]))
        blk_3col = struct.pack('<HHI', 0x07e0, 0xf800, 0xffffffff)
        rgba_3 = decode_bc1(blk_3col, 4, 4)
        self.assertEqual(rgba_3[:4], bytes([0, 0, 0, 0]))
        self.assertEqual(decode_dxt('DXT1', blk_4col, 1, 1), bytes([170, 85, 0, 255]))

        # BC2 explicit 4-bit alpha
        blk_bc2 = (0xfedcba9876543210).to_bytes(8, 'little') + struct.pack('<HHI', 0xf800, 0x07e0, 0x00000000)
        rgba_bc2 = decode_bc2(blk_bc2, 4, 4)
        self.assertEqual(list(rgba_bc2[3::4]), [i * 17 for i in range(16)])
        self.assertEqual(decode_dxt('DXT3', blk_bc2, 4, 4), rgba_bc2)

    def test_jdlz_huff_cip_and_compressed_tpk(self):
        # Synthetic JDLZ stream (16 bytes of 0xaa)
        raw_pixels = bytes([255, 0]) + bytes(6) + struct.pack('<HHI', 0xf800, 0, 0)
        jdlz_hdr = bytearray(18)
        jdlz_hdr[:4] = b'JDLZ'
        jdlz_hdr[4] = 2
        jdlz_hdr[5] = 0x10
        struct.pack_into('<I', jdlz_hdr, 8, 16)
        jdlz_hdr[16] = 0x00
        jdlz_hdr[17] = 0x00
        jdlz_stream = bytes(jdlz_hdr) + raw_pixels[:8] + bytes([0x00]) + raw_pixels[8:]
        jdlz_stream = jdlz_stream[:12] + struct.pack('<I', len(jdlz_stream)) + jdlz_stream[16:]
        self.assertEqual(jdlz_decompress(jdlz_stream), raw_pixels)

        # Real 148-byte HUFF block from 240SX_MISC trailer (or synthetic 148B JDLZ trailer in CIP)
        huff_sample = bytes.fromhex(
            '4855464601100000940000004a00000030fb000094b196e51880b40a411c17fc'
            '23a080540a44afa82716bdbaad150677bc4fd3ecafafbe6015b3f5c202540186'
            '8c710184b61106184fb76e652ee9d6eefc526facf31086e134520b08'
        )
        self.assertEqual(len(huff_decompress(huff_sample)), 148)

        # Build synthetic 148-byte trailer (124B 0x33310004 + 24B 0x33310005) for 4x4 RED DXT5
        rec124 = bytearray(124)
        struct.pack_into('<I', rec124, 12, 0x12345678)
        struct.pack_into('<5I', rec124, 20, 0, 0xffffffff, 16, 0, 16)
        struct.pack_into('<HH', rec124, 40, 4, 4)
        rec124[46] = 0x26
        rec124[50] = 1
        rec124[88] = 35
        rec124[89:93] = b'RED\0'
        fmt24 = bytearray(24)
        fmt24[12:16] = b'DXT5'
        trailer148 = bytes(rec124 + fmt24)

        # Compress trailer148 as JDLZ literal run inside a CIP block
        tr_jdlz = bytearray(18)
        tr_jdlz[:4] = b'JDLZ'
        tr_jdlz[4] = 2
        tr_jdlz[5] = 0x10
        struct.pack_into('<I', tr_jdlz, 8, 148)
        for off in range(0, 148, 8):
            chunk_bytes = trailer148[off:off + 8]
            tr_jdlz += chunk_bytes
            if off + 8 < 148:
                tr_jdlz += b'\x00'
        struct.pack_into('<I', tr_jdlz, 12, len(tr_jdlz))
        while len(tr_jdlz) % 4 != 0:
            tr_jdlz += b'\x00'
        jdlz_padded = bytearray(jdlz_stream)
        while len(jdlz_padded) % 4 != 0:
            jdlz_padded += b'\x00'

        blk0 = struct.pack('<6I', 0x55441122, 148, 24 + len(tr_jdlz), 16, 0, 0) + bytes(tr_jdlz)
        blk1 = struct.pack('<6I', 0x55441122, 16, 24 + len(jdlz_padded), 0, len(blk0), 0) + bytes(jdlz_padded)
        cip_stream = blk0 + blk1
        self.assertEqual(cip_decompress(cip_stream, 164), raw_pixels + trailer148)

        # Build complete synthetic compressed TPK (0x33310003)
        info = bytearray(124)
        struct.pack_into('<I', info, 0, 8)
        c1 = chunk(0x33310001, info)
        c2 = chunk(0x33310002, struct.pack('<II', 0x12345678, 0))
        # Calculate exact file offset where 0x33320002 payload starts:
        # 8 (0xb3300000) + 8 (0xb3310000) + len(c1) + len(c2) + (8 + 24 for 0x33310003) + 8 (0xb3320000) + (8 + 24 for 0x33320001) + 8 (0x33320002 hdr)
        foff = 8 + 8 + len(c1) + len(c2) + 32 + 8 + 32 + 8
        c3 = chunk(0x33310003, struct.pack('<6I', 0x12345678, foff, len(cip_stream), 164, 1, 0))
        b1 = chunk(0xb3310000, c1 + c2 + c3)
        b2 = chunk(0xb3320000, chunk(0x33320001, bytes(24)) + chunk(0x33320002, cip_stream))
        comp_tpk = chunk(0xb3300000, b1 + b2)

        t, = parse_tpk(comp_tpk)
        self.assertEqual((t.name, t.width, t.height, t.fourcc, t.compressed_size), ('RED', 4, 4, 'DXT5', len(cip_stream)))
        self.assertEqual(decode_bc3(texture_payload(comp_tpk, t), 4, 4), bytes([255, 0, 0, 255]) * 16)


if __name__=='__main__':unittest.main()
