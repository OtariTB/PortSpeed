import { cipDecompress, huffDecompress, jdlzDecompress } from './tpk';

const GEOMETRY_LIMIT = 64 * 1024 * 1024;
const check = (ok: boolean, reason: string): void => {
  if (!ok) throw new Error(reason);
};

export interface GeometryPartRecord {
  index: number;
  partHash: number;
  fileOffset: number;
  compressedSize: number;
  uncompressedSize: number;
  flags: number;
  name: string;
}

export interface SubmeshData {
  index: number;
  indexStart: number;
  numIndices: number;
  numVertices: number;
  stride: number;
  effectHash: number;
  textureIndices: number[];
  textureHashes: number[];
  positions: Float32Array;
  normals: Float32Array;
  uvs: Float32Array;
  colors: Uint8Array;
  indices: Uint16Array;
}

export interface SolidMesh {
  name: string;
  partHash: number;
  numTris: number;
  numVerts: number;
  bboxMin: [number, number, number];
  bboxMax: [number, number, number];
  matrix: Float32Array;
  textureHashes: number[];
  materialHashes: number[];
  markerCount: number;
  submeshes: SubmeshData[];
}

function extractSolidName(buf: Uint8Array, alignedStart: number, chunkEnd: number): string {
  for (const nameOff of [0xb8, 0xac, 0xa0]) {
    const start = alignedStart + nameOff;
    if (start < chunkEnd && buf[start] >= 32 && buf[start] < 127) {
      const sub = buf.subarray(start, chunkEnd);
      const zero = sub.indexOf(0);
      if (zero > 0) {
        const slice = sub.subarray(0, zero);
        if (slice.every(b => b >= 32 && b < 127)) {
          return String.fromCharCode(...slice);
        }
      }
    }
  }
  throw new Error('Missing or invalid ASCII part name in 0x00134011');
}

function peekPartNameFromCip(bytes: Uint8Array, fileOffset: number, compressedSize: number): string {
  const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let cur = fileOffset;
  const end = fileOffset + compressedSize;
  while (cur + 24 <= end) {
    const magic = v.getUint32(cur, true);
    check(magic === 0x55441122, 'Invalid CIP block header in geometry stream');
    const cSz = v.getUint32(cur + 8, true);
    const targetOff = v.getUint32(cur + 12, true);
    check(cSz >= 40 && cur + cSz <= end, 'Invalid CIP block size in geometry stream');
    if (targetOff === 0) {
      const payload = bytes.subarray(cur + 24, cur + cSz);
      const imagic = v.getUint32(cur + 24, true);
      const blk = imagic === 0x5a4c444a ? jdlzDecompress(payload) : huffDecompress(payload);
      const bv = new DataView(blk.buffer, blk.byteOffset, blk.byteLength);
      check(blk.length >= 32 && bv.getUint32(0, true) === 0x80134010, 'Expected 0x80134010 eSolid root');
      const tag = bv.getUint32(8, true);
      const sz = bv.getUint32(12, true);
      check(tag === 0x00134011 && 16 + sz <= blk.length, 'Expected 0x00134011 header chunk');
      const al = (8 + 0x17) & ~0x0f;
      return extractSolidName(blk, al, 16 + sz);
    }
    cur += cSz;
  }
  throw new Error('Missing targetOffset 0 block in geometry CIP stream');
}

export function parseGeometryDirectory(bytes: Uint8Array, readNames = true): GeometryPartRecord[] {
  check(bytes.length >= 16 && bytes.length <= GEOMETRY_LIMIT, 'Geometry file size outside supported range');
  const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const u32 = (p: number) => v.getUint32(p, true);
  check(u32(0) === 0x80134000 && 8 + u32(4) === bytes.length, 'Expected 0x80134000 geometry root');

  let pos = 8;
  let dirStart = -1;
  let dirEnd = -1;
  while (pos + 8 <= bytes.length) {
    const tag = u32(pos);
    const sz = u32(pos + 4);
    check(pos + 8 + sz <= bytes.length, 'Chunk exceeds geometry container');
    if (tag === 0x80134001) {
      dirStart = pos + 8;
      dirEnd = pos + 8 + sz;
      break;
    }
    check(tag === 0, 'Unexpected pre-directory chunk');
    pos += 8 + sz;
  }
  check(dirStart > 0 && dirEnd > dirStart, 'Missing 0x80134001 geometry directory chunk');

  const dirChunks = new Map<number, { start: number; end: number }>();
  let dpos = dirStart;
  while (dpos + 8 <= dirEnd) {
    const tag = u32(dpos);
    const sz = u32(dpos + 4);
    check(dpos + 8 + sz <= dirEnd, 'Directory child chunk exceeds 0x80134001');
    if (tag !== 0) dirChunks.set(tag, { start: dpos + 8, end: dpos + 8 + sz });
    dpos += 8 + sz;
  }

  const cInfo = dirChunks.get(0x00134002);
  const cHashes = dirChunks.get(0x00134003);
  const cRecords = dirChunks.get(0x00134004);
  check(!!cInfo && !!cHashes && !!cRecords, 'Missing required geometry directory chunks');
  check(cInfo!.end - cInfo!.start === 144, 'Unexpected 0x00134002 header length');

  const partCount = u32(cInfo!.start + 12);
  check(partCount > 0 && partCount <= 8192, 'Invalid geometry part count');
  check(cHashes!.end - cHashes!.start === partCount * 8, '0x00134003 hash table size mismatch');
  check(cRecords!.end - cRecords!.start === partCount * 24, '0x00134004 record table size mismatch');

  const seen = new Set<number>();
  const entries: GeometryPartRecord[] = [];
  for (let i = 0; i < partCount; i++) {
    const expectedHash = u32(cHashes!.start + i * 8);
    check(!seen.has(expectedHash), 'Duplicate geometry part hash');
    seen.add(expectedHash);

    const rec = cRecords!.start + i * 24;
    const partHash = u32(rec);
    const fileOffset = u32(rec + 4);
    const compressedSize = u32(rec + 8);
    const uncompressedSize = u32(rec + 12);
    const flags = u32(rec + 16);
    const zero = u32(rec + 20);
    check(partHash === expectedHash && zero === 0, 'Geometry part record/hash mismatch');
    check(fileOffset >= dirEnd && fileOffset + compressedSize <= bytes.length, 'Geometry CIP stream out of bounds');
    check(compressedSize >= 24 && uncompressedSize >= 24 && uncompressedSize <= GEOMETRY_LIMIT, 'Invalid geometry CIP stream sizes');

    const name = readNames
      ? peekPartNameFromCip(bytes, fileOffset, compressedSize)
      : `PART_${i}_0x${partHash.toString(16).padStart(8, '0')}`;
    entries.push({ index: i, partHash, fileOffset, compressedSize, uncompressedSize, flags, name });
  }

  const ordered = [...entries].sort((a, b) => a.fileOffset - b.fileOffset);
  for (let i = 1; i < ordered.length; i++) {
    check(ordered[i - 1].fileOffset + ordered[i - 1].compressedSize <= ordered[i].fileOffset, 'Overlapping geometry CIP streams');
  }
  return entries;
}

export function parseSolid(data: Uint8Array, expectedHash?: number): SolidMesh {
  check(data.length >= 8 && data.length <= GEOMETRY_LIMIT, 'Invalid solid buffer length');
  const v = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const u32 = (p: number) => v.getUint32(p, true);
  const u16 = (p: number) => v.getUint16(p, true);
  const i16 = (p: number) => v.getInt16(p, true);
  const f32 = (p: number) => v.getFloat32(p, true);

  check(u32(0) === 0x80134010 && 8 + u32(4) === data.length, 'Expected 0x80134010 eSolid root');

  let name = '';
  let partHash = 0;
  let bboxMin: [number, number, number] = [0, 0, 0];
  let bboxMax: [number, number, number] = [0, 0, 0];
  const matrix = new Float32Array(16);
  let hasHeader = false;
  const textureHashes: number[] = [];
  const materialHashes: number[] = [];
  let markerCount = 0;

  let submeshCount = -1;
  let hdrTris = 0;
  let hdrVerts = 0;
  let b02Start = -1;
  let b02End = -1;
  const b01Slices: Array<{ start: number; end: number }> = [];
  let b03Start = -1;
  let b03End = -1;

  let pos = 8;
  while (pos + 8 <= data.length) {
    const tag = u32(pos);
    const sz = u32(pos + 4);
    const stop = pos + 8 + sz;
    check(stop <= data.length, 'Solid chunk exceeds bounds');

    if (tag === 0x00134011) {
      const al = (pos + 0x17) & ~0x0f;
      check(al + 0xb8 <= stop, 'Truncated 0x00134011 header');
      partHash = u32(al + 0x10);
      if (expectedHash !== undefined) {
        check(partHash === expectedHash, '0x00134011 part hash mismatch');
      }
      bboxMin = [f32(al + 0x20), f32(al + 0x24), f32(al + 0x28)];
      bboxMax = [f32(al + 0x30), f32(al + 0x34), f32(al + 0x38)];
      for (let k = 0; k < 16; k++) matrix[k] = f32(al + 0x40 + k * 4);
      name = extractSolidName(data, al, stop);
      hasHeader = true;
    } else if (tag === 0x00134012) {
      check(sz % 8 === 0, 'Invalid 0x00134012 texture table size');
      for (let k = 0; k < sz; k += 8) textureHashes.push(u32(pos + 8 + k));
    } else if (tag === 0x00134013) {
      check(sz % 8 === 0, 'Invalid 0x00134013 material table size');
      for (let k = 0; k < sz; k += 8) materialHashes.push(u32(pos + 8 + k));
    } else if (tag === 0x0013401a) {
      const al = (pos + 0x17) & ~0x0f;
      check(stop >= al && (stop - al) % 80 === 0, 'Invalid 0x0013401a marker table size');
      markerCount = (stop - al) / 80;
    } else if (tag === 0x80134100) {
      let q = pos + 8;
      while (q + 8 <= stop) {
        const ctag = u32(q);
        const csz = u32(q + 4);
        const cstop = q + 8 + csz;
        check(cstop <= stop, 'Mesh chunk exceeds 0x80134100');
        if (ctag === 0x00134900) {
          const al = (q + 0x17) & ~0x0f;
          check(al + 56 <= cstop, 'Truncated 0x00134900 mesh header');
          submeshCount = u32(al + 16);
          hdrTris = u32(al + 40);
          hdrVerts = u32(al + 48);
        } else if (ctag === 0x00134b02) {
          const al = (q + 0x87) & ~0x7f;
          check(al <= cstop && (cstop - al) % 128 === 0, 'Invalid 0x00134b02 alignment/size');
          b02Start = al;
          b02End = cstop;
        } else if (ctag === 0x00134b01) {
          const al = (q + 0x87) & ~0x7f;
          check(al <= cstop, 'Invalid 0x00134b01 alignment');
          b01Slices.push({ start: al, end: cstop });
        } else if (ctag === 0x00134b03) {
          const al = (q + 0x27) & ~0x1f;
          check(al <= cstop && (cstop - al) % 2 === 0, 'Invalid 0x00134b03 alignment/size');
          b03Start = al;
          b03End = cstop;
        }
        q = cstop;
      }
    }
    pos = stop;
  }

  check(hasHeader && submeshCount > 0, 'Missing solid header or mesh header');
  check(b02Start > 0 && b03Start > 0, 'Missing submesh descriptors or index buffer');
  check((b02End - b02Start) / 128 === submeshCount, 'Submesh descriptor count mismatch');
  check(b01Slices.length === submeshCount, 'Vertex stream count mismatch');

  const totalIndexWords = (b03End - b03Start) / 2;
  check(totalIndexWords >= hdrTris * 3, 'Index buffer smaller than triangle count');

  const submeshes: SubmeshData[] = [];
  let sumVerts = 0;
  let sumTris = 0;
  for (let idx = 0; idx < submeshCount; idx++) {
    const ebase = b02Start + idx * 128;
    const indexStart = u32(ebase);
    const effectHash = u32(ebase + 0x24);
    const numIndices = u32(ebase + 0x2c);
    const vbBytes = u32(ebase + 0x4c);
    const stride = u16(ebase + 0x52) & 0x7fff;
    check(stride === 32 && vbBytes > 0 && vbBytes % stride === 0, `Unsupported vertex stride ${stride}`);
    const numVertices = vbBytes / stride;

    const vb = b01Slices[idx];
    check(vb.end - vb.start === vbBytes, '0x00134b01 size mismatch');
    check(numIndices > 0 && numIndices % 3 === 0, 'Submesh index count must be a positive multiple of 3');
    check(indexStart + numIndices <= totalIndexWords, 'Submesh indices exceed 0x00134b03');

    const textureIndices = Array.from(data.subarray(ebase + 0x1c, ebase + 0x21));
    const resolvedTex = textureIndices
      .filter(t => t !== 0xff)
      .map(t => (t < textureHashes.length ? textureHashes[t] : 0));

    const positions = new Float32Array(numVertices * 3);
    const normals = new Float32Array(numVertices * 3);
    const uvs = new Float32Array(numVertices * 2);
    const colors = new Uint8Array(numVertices * 4);

    for (let vIdx = 0; vIdx < numVertices; vIdx++) {
      const voff = vb.start + vIdx * 32;
      const px = i16(voff);
      const py = i16(voff + 2);
      const pz = i16(voff + 4);
      const pw = i16(voff + 6);
      const tu = i16(voff + 8);
      const tv = i16(voff + 10);
      const cb = data[voff + 12];
      const cg = data[voff + 13];
      const cr = data[voff + 14];
      const ca = data[voff + 15];
      const nx = i16(voff + 16);
      const ny = i16(voff + 18);
      const nz = i16(voff + 20);
      const scale = pw !== 0 ? pw : 3277;

      positions[vIdx * 3] = px / scale;
      positions[vIdx * 3 + 1] = py / scale;
      positions[vIdx * 3 + 2] = pz / scale;

      normals[vIdx * 3] = nx / 32767.0;
      normals[vIdx * 3 + 1] = ny / 32767.0;
      normals[vIdx * 3 + 2] = nz / 32767.0;

      uvs[vIdx * 2] = tu / 32767.0;
      uvs[vIdx * 2 + 1] = tv / 32767.0;

      colors[vIdx * 4] = cr;
      colors[vIdx * 4 + 1] = cg;
      colors[vIdx * 4 + 2] = cb;
      colors[vIdx * 4 + 3] = ca;
    }

    const indices = new Uint16Array(numIndices);
    const ibOff = b03Start + indexStart * 2;
    for (let k = 0; k < numIndices; k++) {
      const ix = u16(ibOff + k * 2);
      check(ix < numVertices, 'Submesh vertex index out of bounds');
      indices[k] = ix;
    }

    sumVerts += numVertices;
    sumTris += numIndices / 3;
    submeshes.push({
      index: idx,
      indexStart,
      numIndices,
      numVertices,
      stride,
      effectHash,
      textureIndices,
      textureHashes: resolvedTex,
      positions,
      normals,
      uvs,
      colors,
      indices,
    });
  }

  check(sumVerts === hdrVerts && sumTris === hdrTris, 'Mesh vertex/triangle totals mismatch');
  return {
    name,
    partHash,
    numTris: hdrTris,
    numVerts: hdrVerts,
    bboxMin,
    bboxMax,
    matrix,
    textureHashes,
    materialHashes,
    markerCount,
    submeshes,
  };
}

export function decompressAndParseSolid(bytes: Uint8Array, entry: GeometryPartRecord): SolidMesh {
  const slice = bytes.subarray(entry.fileOffset, entry.fileOffset + entry.compressedSize);
  const decompressed = cipDecompress(slice, entry.uncompressedSize);
  return parseSolid(decompressed, entry.partHash);
}

/**
 * Filter the stock KIT00 LOD-A vehicle-space parts (excluding local-origin parts like wheels/seats/brakes
 * and morph targets _T0_A.._T4_A).
 */
export function getStockVehicleSpaceParts(entries: GeometryPartRecord[]): GeometryPartRecord[] {
  const excludedSubstrings = [
    'DAMAGE',
    'DECAL',
    'WHEEL',
    'BRAKE_',
    'BRAKEROTOR',
    'SEAT_',
    'DRIVER',
    'ROLL_CAGE',
    'WINDTUNNEL',
    'UNIVERSAL_SPOILER',
    'SPOILER_DRAG',
    'SPOILER_EVO',
    '_T0_A',
    '_T1_A',
    '_T2_A',
    '_T3_A',
    '_T4_A',
  ];
  return entries.filter(
    e =>
      e.name.includes('_KIT00_') &&
      e.name.endsWith('_A') &&
      !excludedSubstrings.some(sub => e.name.includes(sub)),
  );
}
