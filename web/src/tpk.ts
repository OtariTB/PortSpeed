export interface Texture {
  name: string; hash: number; width: number; height: number; mips: number;
  fourcc: string; recordOffset: number; dataOffset: number; size: number; baseSize: number;
  compressedSize?: number;
}
interface Chunk { tag: number; start: number; end: number; children: Chunk[] }
const LIMIT = 64 * 1024 * 1024;
const check = (ok: boolean, reason: string): void => { if (!ok) throw new Error(reason); };

export function jdlzDecompress(src: Uint8Array): Uint8Array {
  check(src.length >= 18, 'Truncated JDLZ stream');
  const v = new DataView(src.buffer, src.byteOffset, src.byteLength);
  const magic = v.getUint32(0, true), version = src[4];
  const uncompLen = v.getUint32(8, true), compLen = v.getUint32(12, true);
  check(magic === 0x5a4c444a && version === 2, 'Invalid JDLZ header');
  check(compLen >= 18 && compLen <= src.length && uncompLen > 0 && uncompLen <= LIMIT, 'Invalid JDLZ sizes');
  const out = new Uint8Array(uncompLen);
  let f1 = src[16] | 0x100, f2 = src[17] | 0x100, sp = 18, dp = 0;
  while (dp < uncompLen) {
    if ((f1 & 1) === 0) {
      while (dp < uncompLen && (f1 & 1) === 0) {
        check(sp < src.length, 'Truncated JDLZ literal');
        out[dp++] = src[sp++];
        f1 >>>= 1;
      }
      if (f1 === 1 && dp < uncompLen) {
        check(sp < src.length, 'Truncated JDLZ flags1');
        f1 = src[sp++] | 0x100;
      }
    } else {
      check(sp + 2 <= src.length, 'Truncated JDLZ match');
      const b0 = src[sp], b1 = src[sp + 1];
      let length = 0, back = 0;
      if ((f2 & 1) !== 0) {
        length = (((b0 & 0xf0) << 4) | b1) + 3;
        back = (b0 & 0x0f) + 1;
      } else {
        back = (((b0 & 0xe0) << 3) | b1) + 17;
        length = (b0 & 0x1f) + 3;
      }
      check(back <= dp && dp + length <= uncompLen, 'JDLZ match out of bounds');
      const base = dp - back;
      for (let i = 0; i < length; i++) out[dp + i] = out[base + i];
      dp += length;
      sp += 2;
      f1 >>>= 1;
      if (f1 === 1 && dp < uncompLen) {
        check(sp < src.length, 'Truncated JDLZ flags1');
        f1 = src[sp++] | 0x100;
      }
      f2 >>>= 1;
      if (f2 === 1 && dp < uncompLen) {
        check(sp < src.length, 'Truncated JDLZ flags2');
        f2 = src[sp++] | 0x100;
      }
    }
  }
  return out;
}

export function huffDecompress(src: Uint8Array): Uint8Array {
  check(src.length >= 16, 'Truncated HUFF stream');
  const v = new DataView(src.buffer, src.byteOffset, src.byteLength);
  const magic = v.getUint32(0, true), version = src[4];
  const uncompLen = v.getUint32(8, true), compPayload = v.getUint32(12, true);
  check(magic === 0x46465548 && version === 1, 'Invalid HUFF header');
  check(uncompLen > 0 && uncompLen <= LIMIT && 16 + compPayload <= src.length, 'Invalid HUFF sizes');

  let bitPos = 16 * 8;
  const peek16 = (): number => {
    const byteIdx = bitPos >>> 3;
    const b0 = byteIdx < src.length ? src[byteIdx] : 0;
    const b1 = byteIdx + 1 < src.length ? src[byteIdx + 1] : 0;
    const b2 = byteIdx + 2 < src.length ? src[byteIdx + 2] : 0;
    const combined = ((b0 << 16) | (b1 << 8) | b2) << (bitPos & 7);
    return (combined >>> 8) & 0xffff;
  };
  const readBits = (n: number): number => {
    if (n <= 0) return 0;
    let val = 0;
    for (let i = 0; i < n; i++) {
      const byteIdx = bitPos >>> 3;
      const b = byteIdx < src.length ? src[byteIdx] : 0;
      const bit = (b >>> (7 - (bitPos & 7))) & 1;
      val = ((val << 1) | bit) >>> 0;
      bitPos++;
    }
    return val >>> 0;
  };
  const getVlc = (): number => {
    let zeros = 0;
    while (readBits(1) === 0) {
      zeros++;
      check(zeros <= 24, 'Corrupt HUFF VLC');
    }
    const nbits = zeros + 2;
    return (readBits(nbits) + (1 << nbits) - 4) >>> 0;
  };

  let hdrType = readBits(16);
  if ((hdrType & 0x0100) !== 0) {
    readBits(24);
    hdrType &= ~0x0100;
  }
  readBits(24); // internal uncompressed size
  const escapeByte = readBits(8);

  const limitTable = new Uint32Array(17);
  const baseOffset = new Uint32Array(17);
  const symTable = new Uint8Array(256);

  let code = 0, totalSyms = 0, bitLen = 1;
  while (bitLen <= 16) {
    code = (code << 1) >>> 0;
    baseOffset[bitLen] = (code - totalSyms) >>> 0;
    const cnt = getVlc();
    totalSyms += cnt;
    check(totalSyms <= 256, 'HUFF symbol count overflow');
    code = (code + cnt) >>> 0;
    const lim16 = cnt !== 0 ? ((code << (16 - bitLen)) & 0xffff) >>> 0 : 0;
    limitTable[bitLen] = lim16;
    if (cnt !== 0 && lim16 === 0) break;
    bitLen++;
  }
  if (bitLen <= 16) limitTable[bitLen] = 0xffffffff;

  let curSym = 0xff;
  const used = new Uint8Array(256);
  for (let i = 0; i < totalSyms; i++) {
    let skip = getVlc() + 1;
    while (skip > 0) {
      curSym = (curSym + 1) & 0xff;
      if (used[curSym] === 0) skip--;
    }
    used[curSym] = 1;
    symTable[i] = curSym;
  }

  const out = new Uint8Array(uncompLen);
  let outPos = 0;
  while (outPos < uncompLen) {
    const p16 = peek16();
    let bl = 1;
    while (bl <= 16 && p16 >= limitTable[bl]) bl++;
    check(bl <= 16, 'Invalid HUFF code');
    const cval = readBits(bl);
    const symIdx = (cval - baseOffset[bl]) >>> 0;
    const sym = symTable[symIdx & 0xff];
    if (sym !== escapeByte) {
      out[outPos++] = sym;
    } else {
      const runLen = getVlc();
      if (runLen !== 0) {
        check(outPos > 0, 'HUFF RLE before first byte');
        const prev = out[outPos - 1];
        for (let r = 0; r < runLen && outPos < uncompLen; r++) out[outPos++] = prev;
      } else {
        if (readBits(1) !== 0) break;
        out[outPos++] = readBits(8) & 0xff;
      }
    }
  }
  if (hdrType === 0x32fb || hdrType === 0xb2fb) {
    let acc = 0;
    for (let i = 0; i < uncompLen; i++) {
      acc = (acc + out[i]) & 0xff;
      out[i] = acc;
    }
  } else if (hdrType === 0x34fb || hdrType === 0xb4fb) {
    let a1 = 0, a2 = 0;
    for (let i = 0; i < uncompLen; i++) {
      a1 = (a1 + out[i]) & 0xff;
      a2 = (a2 + a1) & 0xff;
      out[i] = a2;
    }
  }
  return out;
}

export function cipDecompress(src: Uint8Array, totalUncomp: number): Uint8Array {
  check(src.length >= 24 && totalUncomp > 0 && totalUncomp <= LIMIT, 'Invalid CIP bounds');
  const v = new DataView(src.buffer, src.byteOffset, src.byteLength);
  const out = new Uint8Array(totalUncomp);
  let cur = 0, sumUncomp = 0, sawZero = false;
  while (cur < src.length) {
    check(cur + 24 <= src.length, 'Truncated CIP block header');
    const magic = v.getUint32(cur, true);
    const uSz = v.getUint32(cur + 4, true);
    const cSz = v.getUint32(cur + 8, true);
    const targetOff = v.getUint32(cur + 12, true);
    const streamOff = v.getUint32(cur + 16, true);
    const zero = v.getUint32(cur + 20, true);
    check(magic === 0x55441122 && zero === 0 && streamOff === cur, 'Invalid CIP block header');
    check(cSz >= 40 && cur + cSz <= src.length, 'Invalid CIP block size');
    check(uSz > 0 && targetOff + uSz <= totalUncomp, 'CIP block target out of bounds');
    const payload = src.subarray(cur + 24, cur + cSz);
    const imagic = v.getUint32(cur + 24, true);
    let blk: Uint8Array;
    if (imagic === 0x5a4c444a) blk = jdlzDecompress(payload);
    else if (imagic === 0x46465548) blk = huffDecompress(payload);
    else throw new Error(`Unsupported CIP inner magic 0x${imagic.toString(16)}`);
    check(blk.length === uSz, 'CIP block uncompressed size mismatch');
    out.set(blk, targetOff);
    sumUncomp += uSz;
    cur += cSz;
    if (targetOff === 0) {
      sawZero = true;
      break;
    }
  }
  check(sawZero && sumUncomp === totalUncomp, 'Incomplete CIP stream');
  return out;
}

function validateRecord(
  recBytes: Uint8Array,
  recStart: number,
  recEnd: number,
  fmtBytes: Uint8Array,
  fmtStart: number,
  expectedHash: number,
): { name: string; hash: number; width: number; height: number; mips: number; fourcc: string; offset: number; size: number; baseSize: number; nameLength: number } {
  check(recStart + 89 <= recEnd, 'Truncated texture record');
  const rv = new DataView(recBytes.buffer, recBytes.byteOffset, recBytes.byteLength);
  const hash = rv.getUint32(recStart + 12, true);
  const offset = rv.getUint32(recStart + 20, true);
  const size = rv.getUint32(recStart + 28, true);
  const baseSize = rv.getUint32(recStart + 36, true);
  check(hash === expectedHash, 'Texture hash mismatch');
  const width = rv.getUint16(recStart + 40, true);
  const height = rv.getUint16(recStart + 42, true);
  const mips = recBytes[recStart + 50];
  const nameLength = recBytes[recStart + 88];
  check(nameLength > 0 && recStart + 89 + nameLength <= recEnd, 'Invalid name bounds');
  const raw = recBytes.subarray(recStart + 89, recStart + 89 + nameLength);
  const terminator = raw.indexOf(0);
  check(terminator > 0 && raw.subarray(terminator).every(b => b === 0), 'Invalid name termination');
  check(raw.subarray(0, terminator).every(b => b >= 32 && b < 127), 'Invalid ASCII name');
  const name = String.fromCharCode(...raw.subarray(0, terminator));
  check(width > 0 && height > 0 && width <= 4096 && height <= 4096, 'Invalid dimensions');
  check(mips > 0 && mips <= Math.floor(Math.log2(Math.max(width, height))) + 1, 'Invalid mip count');
  check(rv.getUint32(recStart + 24, true) === 0xffffffff && rv.getUint32(recStart + 32, true) === 0, 'Paletted texture unsupported');
  const fourcc = String.fromCharCode(...fmtBytes.subarray(fmtStart + 12, fmtStart + 16));
  const enc: Record<string, number> = { DXT1: 0x22, DXT3: 0x24, DXT5: 0x26 };
  check(fourcc in enc && enc[fourcc] === recBytes[recStart + 46], 'Unsupported or inconsistent pixel format');
  const levelSize = (m: number) => Math.ceil(Math.max(1, width >> m) / 4) * Math.ceil(Math.max(1, height >> m) / 4) * (fourcc === 'DXT1' ? 8 : 16);
  let total = 0;
  for (let m = 0; m < mips; m++) total += levelSize(m);
  check(baseSize === levelSize(0) && size === total, 'Mipmap size mismatch');
  return { name, hash, width, height, mips, fourcc, offset, size, baseSize, nameLength };
}

export function parseTpk(bytes: Uint8Array): Texture[] {
  check(bytes.length >= 8 && bytes.length <= LIMIT, 'File size outside supported range');
  const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
  const u32=(p: number)=>v.getUint32(p,true);
  let budget=100000;
  function walk(start: number,end: number,depth=0): Chunk[] {
    check(depth<=16,'Nesting limit');
    const nodes: Chunk[]=[];
    while(start<end) {
      check(--budget>=0,'Chunk count limit');
      check(start+8<=end,'Truncated chunk header');
      const tag=u32(start), stop=start+8+u32(start+4);
      check(stop<=end,'Chunk exceeds parent boundary');
      nodes.push({tag,start:start+8,end:stop,children:tag&0x80000000?walk(start+8,stop,depth+1):[]});
      start=stop;
    }
    return nodes;
  }
  const roots=walk(0,bytes.length);
  check(roots.length===1 && roots[0].tag===0xb3300000,'Expected exactly one TPK root');
  const leaves=new Map<number,Chunk>();
  function collect(nodes: Chunk[]): void {
    for(const c of nodes) {
      if(c.children.length) collect(c.children);
      else if(c.tag) { check(!leaves.has(c.tag),'Duplicate TPK chunk'); leaves.set(c.tag,c); }
    }
  }
  collect(roots);
  function get(tag: number): Chunk { const c=leaves.get(tag); check(!!c,`Missing chunk ${tag.toString(16)}`); return c!; }
  const info=get(0x33310001), hashes=get(0x33310002), data=get(0x33320002);
  check(info.end-info.start===124 && u32(info.start)===8,'Unsupported TPK version/info size');
  const count=(hashes.end-hashes.start)/8;
  check(Number.isInteger(count)&&count>0&&count<=4096,'Invalid texture count');
  const seen=new Set<number>();
  for(let i=0;i<count;i++) {
    const h=u32(hashes.start+i*8);
    check(!seen.has(h),'Duplicate texture hash');
    seen.add(h);
  }

  if (leaves.has(0x33310003)) {
    check(!leaves.has(0x33310004) && !leaves.has(0x33310005), 'Conflicting compressed/uncompressed TPK chunks');
    check(leaves.has(0x33320001), 'Missing compressed TPK bank header');
    const comp = get(0x33310003);
    check(comp.end - comp.start === count * 24, 'Compressed record count mismatch');
    const result: Texture[] = [];
    for (let i = 0; i < count; i++) {
      const recPos = comp.start + i * 24;
      const expectedHash = u32(hashes.start + i * 8);
      const h = u32(recPos), foff = u32(recPos + 4), csize = u32(recPos + 8), usize = u32(recPos + 12), zero = u32(recPos + 20);
      check(h === expectedHash && zero === 0, 'Compressed hash/record mismatch');
      check(foff >= data.start && foff + csize <= data.end, 'Compressed texture exceeds data chunk');
      check(usize > 148, 'Compressed texture uncompressed size too small');
      const dec = cipDecompress(bytes.subarray(foff, foff + csize), usize);
      const trailer = dec.subarray(usize - 148, usize);
      const parsed = validateRecord(trailer, 0, 124, trailer, 124, expectedHash);
      check(parsed.size + 148 === usize, 'Compressed texture pixel/trailer size mismatch');
      result.push({
        name: parsed.name,
        hash: parsed.hash,
        width: parsed.width,
        height: parsed.height,
        mips: parsed.mips,
        fourcc: parsed.fourcc,
        recordOffset: recPos,
        dataOffset: foff,
        size: parsed.size,
        baseSize: parsed.baseSize,
        compressedSize: csize,
      });
    }
    const ordered = [...result].sort((a, b) => a.dataOffset - b.dataOffset);
    for (let i = 1; i < ordered.length; i++) {
      check(ordered[i - 1].dataOffset + (ordered[i - 1].compressedSize ?? 0) <= ordered[i].dataOffset, 'Overlapping compressed textures');
    }
    return result;
  }

  const records=get(0x33310004), formats=get(0x33310005);
  check(formats.end-formats.start===count*24,'Format table count mismatch');
  check(data.end-data.start>=120 && bytes.subarray(data.start,data.start+120).every(b=>b===0x11),'Unsupported data prefix');
  const result: Texture[]=[];
  let p=records.start;
  for(let i=0;i<count;i++) {
    const expectedHash=u32(hashes.start+i*8);
    const parsed=validateRecord(bytes,p,records.end,bytes,formats.start+i*24,expectedHash);
    const dataOffset=data.start+120+parsed.offset;
    check(dataOffset+parsed.size<=data.end,'Texture exceeds data boundary');
    result.push({
      name:parsed.name,
      hash:parsed.hash,
      width:parsed.width,
      height:parsed.height,
      mips:parsed.mips,
      fourcc:parsed.fourcc,
      recordOffset:p,
      dataOffset,
      size:parsed.size,
      baseSize:parsed.baseSize,
      compressedSize:0,
    });
    p+=89+parsed.nameLength;
  }
  check(p===records.end,'Unconsumed texture records');
  const ordered=[...result].sort((a,b)=>a.dataOffset-b.dataOffset);
  for(let i=1;i<ordered.length;i++) check(ordered[i-1].dataOffset+ordered[i-1].size<=ordered[i].dataOffset,'Overlapping textures');
  return result;
}

export function extractTexturePayload(bytes: Uint8Array, t: Texture): Uint8Array {
  if (t.compressedSize && t.compressedSize > 0) {
    const dec = cipDecompress(bytes.subarray(t.dataOffset, t.dataOffset + t.compressedSize), t.size + 148);
    return dec.subarray(0, t.baseSize);
  }
  return bytes.subarray(t.dataOffset, t.dataOffset + t.baseSize);
}
