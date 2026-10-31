"""Original synthetic TPK fixture, with a red BC3 block; no game bytes."""
import base64
import json
import struct


def chunk(tag, payload):
    return struct.pack('<II', tag, len(payload)) + payload


def fixture():
    info=bytearray(124)
    struct.pack_into('<I',info,0,8)
    info[4:8]=b'TEST'
    record=bytearray(89)
    struct.pack_into('<I',record,12,0x12345678)
    struct.pack_into('<5I',record,20,0,0xffffffff,16,0,16)
    struct.pack_into('<HH',record,40,4,4)
    record[46]=0x26;record[50]=1;record[88]=4
    record+=b'RED\0'
    fmt=bytearray(24);fmt[12:16]=b'DXT5'
    block=bytes([255,0])+bytes(6)+struct.pack('<HHI',0xf800,0x07e0,0)
    meta=chunk(0x33310001,info)+chunk(0x33310002,struct.pack('<II',0x12345678,0))+chunk(0x33310004,record)+chunk(0x33310005,fmt)
    pixels=chunk(0x33320002,b'\x11'*120+block)
    return chunk(0xb3300000,chunk(0xb3310000,meta)+chunk(0xb3320000,pixels))


if __name__=='__main__':
    print(json.dumps({'base64':base64.b64encode(fixture()).decode()}))
