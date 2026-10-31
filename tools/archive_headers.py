"""Bounded BIG4 index reader and JDLZ header inspector, no extraction/decompression."""
import struct
from tpk import require


def big4_index(data):
    require(len(data)>=16 and data[:4]==b'BIG4','expected BIG4 magic')
    size=struct.unpack_from('<I',data,4)[0]
    count,end=struct.unpack_from('>II',data,8)
    require(size==len(data),'BIG4 declared file size mismatch')
    require(16<=end<=size and 0<count<=100000,'invalid BIG4 index bounds/count')
    require(count<=(end-16)//9,'entry count cannot fit index')
    p=16;entries=[]
    for _ in range(count):
        require(p+9<=end,'truncated BIG4 entry')
        offset,length=struct.unpack_from('>II',data,p);p+=8
        nul=data.find(b'\0',p,min(p+261,end))
        require(nul>=p,'unterminated BIG4 entry name')
        try:name=data[p:nul].decode('ascii')
        except UnicodeDecodeError as exc:raise ValueError('non-ASCII BIG4 name') from exc
        require(bool(name),'empty BIG4 name')
        require(end<=offset<=size and length<=size-offset,'BIG4 entry outside payload')
        entries.append({'name':name,'offset':offset,'size':length});p=nul+1
    require(p==end,f'BIG4 index end mismatch: parsed {p:#x}, declared {end:#x}; unverified trailer')
    ranges=sorted((e['offset'],e['offset']+e['size']) for e in entries if e['size'])
    require(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),'overlapping BIG4 entries')
    require(len(set(e['name'] for e in entries))==count,'duplicate BIG4 names')
    return {'size':size,'count':count,'index_end':end,'entries':entries}


def jdlz_header(header,file_size):
    require(len(header)>=16 and header[:8]==b'JDLZ\x02\x10\0\0','unsupported JDLZ header')
    unpacked,packed=struct.unpack_from('<II',header,8)
    require(packed==file_size and packed>=16,'JDLZ declared input size mismatch')
    require(0<unpacked<=256*1024*1024,'JDLZ output size outside research limit')
    return {'compressed_size':packed,'advertised_uncompressed_size':unpacked,'payload_validated':False}
