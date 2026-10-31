"""Bounded reader for PC Need for Speed: ProStreet vehicle geometry containers (GEOMETRY.BIN).

Validates 0x80134000 geometry packs, 0x00134004 CIP stream records, and decompressed
0x80134010 (eSolid) meshes (0x00134011 header, 0x00134012 texture hashes, 0x0013401a
position markers, 0x00134900 mesh header, 0x00134b02 submesh descriptors, 0x00134b01
32-byte SHORT4N vertex buffers, and 0x00134b03 uint16 triangle index buffers).
"""
from dataclasses import dataclass
import struct
from tpk import FormatError, require, chunks, cip_decompress

GEOMETRY_LIMIT = 64 * 1024 * 1024


@dataclass
class GeometryPartEntry:
    index: int
    part_hash: int
    file_offset: int
    compressed_size: int
    uncompressed_size: int
    flags: int


@dataclass
class PositionMarker:
    marker_hash: int
    matrix: tuple


@dataclass
class Submesh:
    index: int
    index_start: int
    num_indices: int
    num_vertices: int
    stride: int
    effect_hash: int
    texture_indices: tuple
    texture_hashes: tuple
    positions: list
    normals: list
    uvs: list
    colors: list
    indices: list


@dataclass
class SolidMesh:
    name: str
    part_hash: int
    num_tris: int
    num_verts: int
    bbox_min: tuple
    bbox_max: tuple
    matrix: tuple
    texture_hashes: tuple
    material_hashes: tuple
    markers: list
    submeshes: list


def parse_geometry_directory(data):
    require(16 <= len(data) <= GEOMETRY_LIMIT, 'geometry file size outside supported range')
    root_tag, root_size = struct.unpack_from('<II', data, 0)
    require(root_tag == 0x80134000 and 8 + root_size == len(data), 'expected 0x80134000 geometry root')

    # Walk top-level header chunks until we locate 0x80134001 directory chunk
    pos = 8
    dir_chunk = None
    while pos + 8 <= len(data):
        tag, size = struct.unpack_from('<II', data, pos)
        require(pos + 8 + size <= len(data), f'chunk {tag:08x} exceeds container')
        if tag == 0x80134001:
            dir_chunk = (pos + 8, pos + 8 + size)
            break
        require(tag == 0, f'unexpected pre-directory chunk {tag:08x}')
        pos += 8 + size

    require(dir_chunk is not None, 'missing 0x80134001 geometry directory chunk')
    stream_bank_offset = dir_chunk[1]
    dir_nodes = {c.tag: c for c in chunks(data, dir_chunk[0], dir_chunk[1]) if c.tag != 0}
    for req_tag in (0x00134002, 0x00134003, 0x00134004):
        require(req_tag in dir_nodes, f'missing directory chunk {req_tag:08x}')

    c_info = dir_nodes[0x00134002]
    info = data[c_info.start:c_info.end]
    require(len(info) == 144, 'unexpected 0x00134002 header length')
    part_count = struct.unpack_from('<I', info, 12)[0]
    require(0 < part_count <= 8192, 'invalid geometry part count')

    c_hashes = dir_nodes[0x00134003]
    hashes_buf = data[c_hashes.start:c_hashes.end]
    require(len(hashes_buf) == part_count * 8, '0x00134003 hash table size mismatch')
    expected_hashes = [struct.unpack_from('<I', hashes_buf, i * 8)[0] for i in range(part_count)]
    require(len(set(expected_hashes)) == part_count, 'duplicate geometry part hashes')

    c_records = dir_nodes[0x00134004]
    records_buf = data[c_records.start:c_records.end]
    require(len(records_buf) == part_count * 24, '0x00134004 record table size mismatch')

    entries = []
    intervals = []
    for i in range(part_count):
        h, foff, csize, usize, flags, zero = struct.unpack_from('<6I', records_buf, i * 24)
        require(h == expected_hashes[i] and zero == 0, 'geometry part record/hash mismatch')
        require(stream_bank_offset <= foff and foff + csize <= len(data), 'geometry CIP stream out of bounds')
        require(24 <= csize <= GEOMETRY_LIMIT and 24 <= usize <= GEOMETRY_LIMIT, 'invalid geometry CIP stream sizes')
        intervals.append((foff, foff + csize))
        entries.append(GeometryPartEntry(i, h, foff, csize, usize, flags))

    ordered = sorted(intervals)
    require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'overlapping geometry CIP streams')
    return entries


def _extract_solid_name(buf, aligned_start, chunk_end):
    for name_off in (0xb8, 0xac, 0xa0):
        start = aligned_start + name_off
        if start < chunk_end and 32 <= buf[start] < 127:
            raw = buf[start:chunk_end]
            if b'\0' in raw:
                candidate = raw.split(b'\0', 1)[0]
                if candidate and all(32 <= b < 127 for b in candidate):
                    return candidate.decode('ascii')
    raise FormatError('missing or invalid ASCII part name in 0x00134011')


def parse_solid(data, expected_hash=None):
    require(8 <= len(data) <= GEOMETRY_LIMIT, 'invalid solid buffer length')
    root_tag, root_size = struct.unpack_from('<II', data, 0)
    require(root_tag == 0x80134010 and 8 + root_size == len(data), 'expected 0x80134010 eSolid root')

    header_info = None
    texture_hashes = ()
    material_hashes = ()
    markers = []
    mesh_hdr = None
    b02_slice = None
    b01_slices = []
    b03_slice = None

    pos = 8
    while pos + 8 <= len(data):
        tag, size = struct.unpack_from('<II', data, pos)
        stop = pos + 8 + size
        require(stop <= len(data), f'solid chunk {tag:08x} exceeds bounds')
        if tag == 0x00134011:
            al = (pos + 0x17) & ~0x0f
            require(al + 0xb8 <= stop, 'truncated 0x00134011 header')
            part_hash = struct.unpack_from('<I', data, al + 0x10)[0]
            if expected_hash is not None:
                require(part_hash == expected_hash, '0x00134011 part hash mismatch')
            num_tris = struct.unpack_from('<H', data, al + 0x14)[0]
            bbox_min = struct.unpack_from('<3f', data, al + 0x20)
            bbox_max = struct.unpack_from('<3f', data, al + 0x30)
            matrix = struct.unpack_from('<16f', data, al + 0x40)
            name = _extract_solid_name(data, al, stop)
            header_info = (name, part_hash, num_tris, bbox_min, bbox_max, matrix)
        elif tag == 0x00134012:
            require(size % 8 == 0, 'invalid 0x00134012 texture table size')
            texture_hashes = tuple(
                struct.unpack_from('<I', data, pos + 8 + k)[0]
                for k in range(0, size, 8)
            )
        elif tag == 0x00134013:
            require(size % 8 == 0, 'invalid 0x00134013 material table size')
            material_hashes = tuple(
                struct.unpack_from('<I', data, pos + 8 + k)[0]
                for k in range(0, size, 8)
            )
        elif tag == 0x0013401a:
            al = (pos + 0x17) & ~0x0f
            rem = stop - al
            require(rem >= 0 and rem % 80 == 0, 'invalid 0x0013401a marker table size')
            for m in range(0, rem, 80):
                mhash = struct.unpack_from('<I', data, al + m)[0]
                mmat = struct.unpack_from('<16f', data, al + m + 16)
                markers.append(PositionMarker(mhash, mmat))
        elif tag == 0x80134100:
            q = pos + 8
            while q + 8 <= stop:
                ctag, csize = struct.unpack_from('<II', data, q)
                cstop = q + 8 + csize
                require(cstop <= stop, f'mesh chunk {ctag:08x} exceeds 0x80134100')
                if ctag == 0x00134900:
                    al = (q + 0x17) & ~0x0f
                    require(al + 56 <= cstop, 'truncated 0x00134900 mesh header')
                    submesh_count = struct.unpack_from('<I', data, al + 16)[0]
                    hdr_tris = struct.unpack_from('<I', data, al + 40)[0]
                    hdr_verts = struct.unpack_from('<I', data, al + 48)[0]
                    mesh_hdr = (submesh_count, hdr_tris, hdr_verts)
                elif ctag == 0x00134b02:
                    al = (q + 0x87) & ~0x7f
                    require(al <= cstop and (cstop - al) % 128 == 0, 'invalid 0x00134b02 alignment/size')
                    b02_slice = (al, cstop)
                elif ctag == 0x00134b01:
                    al = (q + 0x87) & ~0x7f
                    require(al <= cstop, 'invalid 0x00134b01 alignment')
                    b01_slices.append((al, cstop))
                elif ctag == 0x00134b03:
                    al = (q + 0x27) & ~0x1f
                    require(al <= cstop and (cstop - al) % 2 == 0, 'invalid 0x00134b03 alignment/size')
                    b03_slice = (al, cstop)
                q = cstop
        pos = stop

    require(header_info is not None and mesh_hdr is not None, 'missing solid header or mesh header')
    require(b02_slice is not None and b03_slice is not None, 'missing submesh descriptors or index buffer')
    name, part_hash, _, bbox_min, bbox_max, matrix = header_info
    submesh_count, hdr_tris, hdr_verts = mesh_hdr

    b02_start, b02_end = b02_slice
    require((b02_end - b02_start) // 128 == submesh_count, 'submesh descriptor count mismatch')
    require(len(b01_slices) == submesh_count, 'vertex stream count mismatch')

    b03_start, b03_end = b03_slice
    total_index_words = (b03_end - b03_start) // 2
    require(total_index_words >= hdr_tris * 3, 'index buffer smaller than triangle count')

    submeshes = []
    sum_verts = 0
    sum_tris = 0
    for idx in range(submesh_count):
        ebase = b02_start + idx * 128
        idx_start = struct.unpack_from('<I', data, ebase)[0]
        effect_hash = struct.unpack_from('<I', data, ebase + 0x24)[0]
        num_indices = struct.unpack_from('<I', data, ebase + 0x2c)[0]
        vb_bytes = struct.unpack_from('<I', data, ebase + 0x4c)[0]
        stride = struct.unpack_from('<H', data, ebase + 0x52)[0] & 0x7fff
        require(stride == 32 and vb_bytes > 0 and vb_bytes % stride == 0, f'unsupported vertex stride {stride}')
        num_verts = vb_bytes // stride

        vb_start, vb_end = b01_slices[idx]
        require(vb_end - vb_start == vb_bytes, '0x00134b01 size mismatch')
        require(num_indices > 0 and num_indices % 3 == 0, 'submesh index count must be a positive multiple of 3')
        require(idx_start + num_indices <= total_index_words, 'submesh indices exceed 0x00134b03')

        tex_indices = tuple(data[ebase + 0x1c:ebase + 0x21])
        resolved_tex = tuple(
            texture_hashes[t] if t < len(texture_hashes) else 0
            for t in tex_indices
            if t != 0xff
        )

        positions = []
        normals = []
        uvs = []
        colors = []
        for v in range(num_verts):
            voff = vb_start + v * 32
            px, py, pz, pw, tu, tv = struct.unpack_from('<6h', data, voff)
            cb, cg, cr, ca = data[voff + 12:voff + 16]
            nx, ny, nz, _nw = struct.unpack_from('<4h', data, voff + 16)
            scale = float(pw) if pw != 0 else 3277.0
            positions.append((px / scale, py / scale, pz / scale))
            normals.append((nx / 32767.0, ny / 32767.0, nz / 32767.0))
            uvs.append((tu / 32767.0, tv / 32767.0))
            colors.append((cr, cg, cb, ca))

        ib_offset = b03_start + idx_start * 2
        indices = list(struct.unpack_from(f'<{num_indices}H', data, ib_offset))
        require(all(0 <= ix < num_verts for ix in indices), 'submesh vertex index out of bounds')

        sum_verts += num_verts
        sum_tris += num_indices // 3
        submeshes.append(
            Submesh(
                index=idx,
                index_start=idx_start,
                num_indices=num_indices,
                num_vertices=num_verts,
                stride=stride,
                effect_hash=effect_hash,
                texture_indices=tex_indices,
                texture_hashes=resolved_tex,
                positions=positions,
                normals=normals,
                uvs=uvs,
                colors=colors,
                indices=indices,
            )
        )

    require(sum_verts == hdr_verts and sum_tris == hdr_tris, 'mesh vertex/triangle totals mismatch')
    return SolidMesh(
        name=name,
        part_hash=part_hash,
        num_tris=hdr_tris,
        num_verts=hdr_verts,
        bbox_min=bbox_min,
        bbox_max=bbox_max,
        matrix=matrix,
        texture_hashes=texture_hashes,
        material_hashes=material_hashes,
        markers=markers,
        submeshes=submeshes,
    )


def decompress_and_parse_part(data, entry):
    comp_slice = data[entry.file_offset:entry.file_offset + entry.compressed_size]
    decompressed = cip_decompress(comp_slice, entry.uncompressed_size)
    return parse_solid(decompressed, expected_hash=entry.part_hash)
