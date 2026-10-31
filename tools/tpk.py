"""Bounded reader for PC version-8 ProStreet texture packs (uncompressed and CIP/JDLZ/HUFF compressed).

Format research and reference revisions: research/phase2-formats.md and research/phase3-recompilation.md.
No compression autodetection, embedded-signature searching or executable loading.
"""
from dataclasses import dataclass, asdict
import struct
import zlib

LIMIT = 64 * 1024 * 1024


class FormatError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise FormatError(message)


@dataclass
class Chunk:
    tag: int
    offset: int
    start: int
    end: int
    children: list


def chunks(data, start=0, end=None, depth=0, budget=None):
    end = len(data) if end is None else end
    budget = [100000] if budget is None else budget
    require(0 <= start <= end <= len(data), 'invalid container bounds')
    require(depth <= 16, 'nesting limit')
    out = []
    while start < end:
        budget[0] -= 1
        require(budget[0] >= 0, 'chunk count limit')
        require(end - start >= 8, 'truncated chunk header')
        tag, size = struct.unpack_from('<II', data, start)
        stop = start + 8 + size
        require(stop <= end, f'chunk {tag:08x} at {start:x} exceeds parent')
        child = chunks(data, start + 8, stop, depth + 1, budget) if tag & 0x80000000 else []
        out.append(Chunk(tag, start, start + 8, stop, child))
        start = stop
    return out


def flatten(nodes):
    for node in nodes:
        yield node
        yield from flatten(node.children)


def jdlz_decompress(src):
    require(len(src) >= 18, 'truncated JDLZ stream')
    magic, version, uncomp_len, comp_len = struct.unpack_from('<IB3xII', src, 0)
    require(magic == 0x5a4c444a and version == 2, 'invalid JDLZ header')
    require(18 <= comp_len <= len(src) and 0 < uncomp_len <= LIMIT, 'invalid JDLZ sizes')
    out = bytearray(uncomp_len)
    f1 = src[16] | 0x100
    f2 = src[17] | 0x100
    sp = 18
    dp = 0
    while dp < uncomp_len:
        if (f1 & 1) == 0:
            while dp < uncomp_len and (f1 & 1) == 0:
                require(sp < len(src), 'truncated JDLZ literal')
                out[dp] = src[sp]
                dp += 1
                sp += 1
                f1 >>= 1
            if f1 == 1 and dp < uncomp_len:
                require(sp < len(src), 'truncated JDLZ flags1')
                f1 = src[sp] | 0x100
                sp += 1
        else:
            require(sp + 2 <= len(src), 'truncated JDLZ match')
            b0, b1 = src[sp], src[sp + 1]
            if (f2 & 1) != 0:
                length = (((b0 & 0xf0) << 4) | b1) + 3
                back = (b0 & 0x0f) + 1
            else:
                back = (((b0 & 0xe0) << 3) | b1) + 17
                length = (b0 & 0x1f) + 3
            require(back <= dp and dp + length <= uncomp_len, 'JDLZ match out of bounds')
            base = dp - back
            for i in range(length):
                out[dp + i] = out[base + i]
            dp += length
            sp += 2
            f1 >>= 1
            if f1 == 1 and dp < uncomp_len:
                require(sp < len(src), 'truncated JDLZ flags1')
                f1 = src[sp] | 0x100
                sp += 1
            f2 >>= 1
            if f2 == 1 and dp < uncomp_len:
                require(sp < len(src), 'truncated JDLZ flags2')
                f2 = src[sp] | 0x100
                sp += 1
    return bytes(out)


def huff_decompress(src):
    require(len(src) >= 16, 'truncated HUFF stream')
    magic, version, uncomp_len, comp_payload = struct.unpack_from('<IB3xII', src, 0)
    require(magic == 0x46465548 and version == 1, 'invalid HUFF header')
    require(0 < uncomp_len <= LIMIT and 16 + comp_payload <= len(src), 'invalid HUFF sizes')
    bit_pos = 16 * 8

    def peek16():
        byte_idx = bit_pos >> 3
        b0 = src[byte_idx] if byte_idx < len(src) else 0
        b1 = src[byte_idx + 1] if byte_idx + 1 < len(src) else 0
        b2 = src[byte_idx + 2] if byte_idx + 2 < len(src) else 0
        combined = ((b0 << 16) | (b1 << 8) | b2) << (bit_pos & 7)
        return (combined >> 8) & 0xffff

    def read_bits(n):
        nonlocal bit_pos
        if n <= 0:
            return 0
        val = 0
        for _ in range(n):
            byte_idx = bit_pos >> 3
            b = src[byte_idx] if byte_idx < len(src) else 0
            bit = (b >> (7 - (bit_pos & 7))) & 1
            val = (val << 1) | bit
            bit_pos += 1
        return val

    def get_vlc():
        zeros = 0
        while read_bits(1) == 0:
            zeros += 1
            require(zeros <= 24, 'corrupt HUFF VLC')
        nbits = zeros + 2
        return read_bits(nbits) + (1 << nbits) - 4

    hdr_type = read_bits(16)
    if hdr_type & 0x0100:
        read_bits(24)
        hdr_type &= ~0x0100
    _internal_uncomp = read_bits(24)
    escape_byte = read_bits(8)
    limit_table = [0] * 17
    base_offset = [0] * 17
    sym_table = [0] * 256
    code = 0
    total_syms = 0
    bit_len = 1
    while bit_len <= 16:
        code <<= 1
        base_offset[bit_len] = (code - total_syms) & 0xffffffff
        cnt = get_vlc()
        total_syms += cnt
        require(total_syms <= 256, 'HUFF symbol count overflow')
        code += cnt
        lim16 = ((code << (16 - bit_len)) & 0xffff) if cnt else 0
        limit_table[bit_len] = lim16
        if cnt != 0 and lim16 == 0:
            break
        bit_len += 1
    if bit_len <= 16:
        limit_table[bit_len] = 0xffffffff
    cur_sym = 0xff
    used = [0] * 256
    for i in range(total_syms):
        skip = get_vlc() + 1
        while skip > 0:
            cur_sym = (cur_sym + 1) & 0xff
            if used[cur_sym] == 0:
                skip -= 1
        used[cur_sym] = 1
        sym_table[i] = cur_sym
    out = bytearray(uncomp_len)
    out_pos = 0
    while out_pos < uncomp_len:
        p16 = peek16()
        bl = 1
        while bl <= 16 and p16 >= limit_table[bl]:
            bl += 1
        require(bl <= 16, 'invalid HUFF code')
        cval = read_bits(bl)
        sym_idx = (cval - base_offset[bl]) & 0xffffffff
        sym = sym_table[sym_idx & 0xff]
        if sym != escape_byte:
            out[out_pos] = sym
            out_pos += 1
        else:
            run_len = get_vlc()
            if run_len != 0:
                require(out_pos > 0, 'HUFF RLE before first byte')
                prev = out[out_pos - 1]
                for _ in range(run_len):
                    if out_pos < uncomp_len:
                        out[out_pos] = prev
                        out_pos += 1
            else:
                if read_bits(1) != 0:
                    break
                out[out_pos] = read_bits(8)
                out_pos += 1
    if hdr_type in (0x32fb, 0xb2fb):
        acc = 0
        for i in range(uncomp_len):
            acc = (acc + out[i]) & 0xff
            out[i] = acc
    elif hdr_type in (0x34fb, 0xb4fb):
        a1 = 0
        a2 = 0
        for i in range(uncomp_len):
            a1 = (a1 + out[i]) & 0xff
            a2 = (a2 + a1) & 0xff
            out[i] = a2
    return bytes(out)


def cip_decompress(src, total_uncomp):
    require(len(src) >= 24 and 0 < total_uncomp <= LIMIT, 'invalid CIP bounds')
    out = bytearray(total_uncomp)
    cur = 0
    sum_uncomp = 0
    saw_zero_offset = False
    while cur < len(src):
        require(cur + 24 <= len(src), 'truncated CIP block header')
        magic, u_sz, c_sz, target_off, stream_off, zero = struct.unpack_from('<6I', src, cur)
        require(magic == 0x55441122 and zero == 0 and stream_off == cur, 'invalid CIP block header')
        require(c_sz >= 40 and cur + c_sz <= len(src), 'invalid CIP block size')
        require(u_sz > 0 and target_off + u_sz <= total_uncomp, 'CIP block target out of bounds')
        payload = src[cur + 24:cur + c_sz]
        imagic = struct.unpack_from('<I', payload, 0)[0]
        if imagic == 0x5a4c444a:
            blk = jdlz_decompress(payload)
        elif imagic == 0x46465548:
            blk = huff_decompress(payload)
        else:
            raise FormatError(f'unsupported CIP inner magic {imagic:08x}')
        require(len(blk) == u_sz, 'CIP block uncompressed size mismatch')
        out[target_off:target_off + u_sz] = blk
        sum_uncomp += u_sz
        cur += c_sz
        if target_off == 0:
            saw_zero_offset = True
            break
    require(saw_zero_offset and sum_uncomp == total_uncomp, 'incomplete CIP stream')
    return bytes(out)


@dataclass
class Texture:
    name: str
    name_hash: int
    width: int
    height: int
    mip_count: int
    fourcc: str
    record_offset: int
    data_offset: int
    data_size: int
    base_size: int
    compressed_size: int = 0


def _validate_texture_record(records, p, formats, fmt_offset, expected_hash):
    require(p + 89 <= len(records), 'truncated texture record')
    h = struct.unpack_from('<I', records, p + 12)[0]
    offset, palette, size, palette_size, base_size = struct.unpack_from('<5I', records, p + 20)
    w, height = struct.unpack_from('<HH', records, p + 40)
    compression, mips, name_len = records[p + 46], records[p + 50], records[p + 88]
    require(h == expected_hash, 'hash table/record mismatch')
    require(0 < name_len <= 255 and p + 89 + name_len <= len(records), 'name outside record table')
    raw_name = records[p + 89:p + 89 + name_len]
    require(b'\0' in raw_name and not raw_name.split(b'\0', 1)[1].strip(b'\0'), 'name termination/padding')
    try:
        name = raw_name.split(b'\0', 1)[0].decode('ascii')
    except UnicodeDecodeError as exc:
        raise FormatError('non-ASCII name') from exc
    require(bool(name) and all(32 <= ord(c) < 127 for c in name), 'invalid texture name')
    require(0 < w <= 4096 and 0 < height <= 4096, 'invalid dimensions')
    require(0 < mips <= max(w, height).bit_length(), 'invalid mip count')
    require(palette_size == 0 and palette == 0xffffffff, 'paletted textures unsupported')
    fmt = bytes(formats[fmt_offset + 12:fmt_offset + 16])
    require(fmt in (b'DXT1', b'DXT3', b'DXT5'), 'unsupported pixel format')
    require(compression == {b'DXT1': 0x22, b'DXT3': 0x24, b'DXT5': 0x26}[fmt], 'compression/FourCC mismatch')
    block = 8 if fmt == b'DXT1' else 16
    sizes = [((max(1, w >> m) + 3) // 4) * ((max(1, height >> m) + 3) // 4) * block for m in range(mips)]
    require(base_size == sizes[0] and size == sum(sizes), 'mipmap size mismatch')
    return name, h, w, height, mips, fmt.decode(), offset, size, base_size, name_len


def parse_tpk(data):
    require(8 <= len(data) <= LIMIT, 'file size outside supported range')
    roots = chunks(data)
    require(len(roots) == 1 and roots[0].tag == 0xb3300000, 'expected exactly one TPK root')
    leaves = {}
    for c in flatten(roots):
        if c.tag and not c.children:
            require(c.tag not in leaves, 'duplicate TPK chunk')
            leaves[c.tag] = c

    def get(tag):
        require(tag in leaves, f'missing chunk {tag:08x}')
        c = leaves[tag]
        return c, data[c.start:c.end]

    _, info = get(0x33310001)
    require(len(info) == 124 and struct.unpack_from('<I', info)[0] == 8, 'unsupported TPK version/info size')
    _, hashes = get(0x33310002)
    require(len(hashes) % 8 == 0 and 0 < len(hashes) // 8 <= 4096, 'invalid hash table count')
    count = len(hashes) // 8
    expected = [struct.unpack_from('<I', hashes, i * 8)[0] for i in range(count)]
    require(len(set(expected)) == count, 'duplicate texture hashes')
    dc, payload = get(0x33320002)

    if 0x33310003 in leaves:
        require(0x33310004 not in leaves and 0x33310005 not in leaves, 'conflicting compressed/uncompressed TPK chunks')
        require(0x33320001 in leaves, 'missing compressed TPK bank header')
        cc, comp_records = get(0x33310003)
        require(len(comp_records) == count * 24, 'compressed record count mismatch')
        textures, intervals = [], []
        for i in range(count):
            rec_off = i * 24
            h, foff, csize, usize, flags, zero = struct.unpack_from('<6I', comp_records, rec_off)
            require(h == expected[i] and zero == 0, 'compressed hash/record mismatch')
            require(dc.start <= foff and foff + csize <= dc.end, 'compressed texture exceeds data chunk')
            require(usize > 148, 'compressed texture uncompressed size too small')
            dec = cip_decompress(data[foff:foff + csize], usize)
            trailer = dec[-148:]
            tex_rec = trailer[:124]
            fmt_rec = trailer[124:]
            name, _, w, height, mips, fourcc, _, size, base_size, _ = _validate_texture_record(
                tex_rec, 0, fmt_rec, 0, expected[i]
            )
            require(size + 148 == usize, 'compressed texture pixel/trailer size mismatch')
            intervals.append((foff, foff + csize))
            textures.append(Texture(name, h, w, height, mips, fourcc, cc.start + rec_off, foff, size, base_size, csize))
        ordered = sorted(intervals)
        require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'overlapping compressed textures')
        return textures

    rc, records = get(0x33310004)
    _, formats = get(0x33310005)
    require(len(formats) == count * 24, 'format table count mismatch')
    require(len(payload) >= 120 and payload[:120] == b'\x11' * 120, 'unsupported data prefix/alignment')
    base = dc.start + 120
    p, textures, intervals = 0, [], []
    for i in range(count):
        name, h, w, height, mips, fourcc, offset, size, base_size, name_len = _validate_texture_record(
            records, p, formats, i * 24, expected[i]
        )
        require(base + offset + size <= dc.end, 'texture payload exceeds data chunk')
        intervals.append((offset, offset + size))
        textures.append(Texture(name, h, w, height, mips, fourcc, rc.start + p, base + offset, size, base_size, 0))
        p += 89 + name_len
    require(p == len(records), 'unconsumed texture records')
    ordered = sorted(intervals)
    require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'overlapping textures')
    return textures


def texture_payload(data, texture):
    if texture.compressed_size > 0:
        dec = cip_decompress(
            data[texture.data_offset:texture.data_offset + texture.compressed_size],
            texture.data_size + 148,
        )
        return dec[:texture.data_size]
    return data[texture.data_offset:texture.data_offset + texture.data_size]


def _rgb565(v):
    r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


def decode_bc1(data, width, height):
    require(0 < width <= 4096 and 0 < height <= 4096, 'invalid BC1 dimensions')
    require(len(data) == ((width + 3) // 4) * ((height + 3) // 4) * 8, 'invalid BC1 length')
    out = bytearray(width * height * 4)
    p = 0
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            c0, c1, ci = struct.unpack_from('<HHI', data, p)
            rgb0, rgb1 = _rgb565(c0), _rgb565(c1)
            if c0 > c1:
                c = [
                    (*rgb0, 255),
                    (*rgb1, 255),
                    (*((2 * rgb0[k] + rgb1[k]) // 3 for k in range(3)), 255),
                    (*((rgb0[k] + 2 * rgb1[k]) // 3 for k in range(3)), 255),
                ]
            else:
                c = [
                    (*rgb0, 255),
                    (*rgb1, 255),
                    (*((rgb0[k] + rgb1[k]) // 2 for k in range(3)), 255),
                    (0, 0, 0, 0),
                ]
            for j in range(16):
                px, py = x + j % 4, y + j // 4
                if px < width and py < height:
                    q = (py * width + px) * 4
                    out[q:q + 4] = bytes(c[(ci >> (2 * j)) & 3])
            p += 8
    return bytes(out)


def decode_bc2(data, width, height):
    require(0 < width <= 4096 and 0 < height <= 4096, 'invalid BC2 dimensions')
    require(len(data) == ((width + 3) // 4) * ((height + 3) // 4) * 16, 'invalid BC2 length')
    out = bytearray(width * height * 4)
    p = 0
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            ai = int.from_bytes(data[p:p + 8], 'little')
            c0, c1, ci = struct.unpack_from('<HHI', data, p + 8)
            rgb0, rgb1 = _rgb565(c0), _rgb565(c1)
            c = [
                rgb0,
                rgb1,
                tuple((2 * rgb0[k] + rgb1[k]) // 3 for k in range(3)),
                tuple((rgb0[k] + 2 * rgb1[k]) // 3 for k in range(3)),
            ]
            for j in range(16):
                px, py = x + j % 4, y + j // 4
                if px < width and py < height:
                    q = (py * width + px) * 4
                    a4 = (ai >> (4 * j)) & 0xf
                    out[q:q + 4] = bytes((*c[(ci >> (2 * j)) & 3], a4 * 17))
            p += 16
    return bytes(out)


def decode_bc3(data, width, height):
    require(0 < width <= 4096 and 0 < height <= 4096, 'invalid BC3 dimensions')
    require(len(data) == ((width+3)//4)*((height+3)//4)*16, 'invalid BC3 length')
    out = bytearray(width*height*4)
    p=0
    for y in range(0,height,4):
        for x in range(0,width,4):
            a0,a1=data[p:p+2]
            alpha=[a0,a1]
            if a0>a1:
                alpha += [((7-i)*a0+i*a1)//7 for i in range(1,7)]
            else:
                alpha += [((5-i)*a0+i*a1)//5 for i in range(1,5)]+[0,255]
            ai=int.from_bytes(data[p+2:p+8],'little')
            c0,c1,ci=struct.unpack_from('<HHI',data,p+8)
            c=[_rgb565(c0),_rgb565(c1)]
            c += [tuple((2*c[0][k]+c[1][k])//3 for k in range(3)),tuple((c[0][k]+2*c[1][k])//3 for k in range(3))]
            for j in range(16):
                px,py=x+j%4,y+j//4
                if px<width and py<height:
                    q=(py*width+px)*4
                    out[q:q+4]=bytes((*c[(ci>>(2*j))&3],alpha[(ai>>(3*j))&7]))
            p+=16
    return bytes(out)


def decode_dxt(fourcc, data, width, height):
    if fourcc == 'DXT1':
        return decode_bc1(data, width, height)
    if fourcc == 'DXT3':
        return decode_bc2(data, width, height)
    if fourcc == 'DXT5':
        return decode_bc3(data, width, height)
    raise FormatError(f'unsupported DXT format {fourcc}')


def dds(texture, payload):
    """Standard legacy DDS, all recorded mip levels, for independent validation."""
    header = bytearray(124)
    flags=0x81007 | (0x20000 if texture.mip_count>1 else 0)
    struct.pack_into('<7I',header,0,124,flags,texture.height,texture.width,texture.base_size,0,texture.mip_count)
    struct.pack_into('<II4s',header,72,32,4,texture.fourcc.encode())
    struct.pack_into('<I',header,104,0x1000 | (0x400008 if texture.mip_count>1 else 0))
    return b'DDS '+header+payload


def png(width,height,rgba):
    require(len(rgba)==width*height*4,'RGBA length mismatch')
    def chunk(tag,body):
        return struct.pack('>I',len(body))+tag+body+struct.pack('>I',zlib.crc32(tag+body))
    rows=b''.join(b'\0'+rgba[y*width*4:(y+1)*width*4] for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
