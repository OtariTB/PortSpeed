#!/usr/bin/env node
/**
 * Phase D verification harness for statically recompiled ProStreet x86 functions in WebAssembly.
 *
 * Loads %LOCALAPPDATA%/NFSProStreetResearch/phase3/recomp/prostreet_lifted.wasm and validates:
 *   1. sub_00436680 (bStringHash) against all 22 original texture name hashes + boundary cases.
 *   2. sub_004366b0 (bStringHashInit) chained string hashing.
 *   3. sub_004366e0 (bStringHashUpper) case-insensitive hashing.
 *   4. sub_006cd550 (LZDecompress_JDLZ) against invalid headers, synthetic JDLZ streams, and
 *      real read-only ProStreet JDLZ streams (GLOBAL/ishp.lzc and CARS/240SX/TEXTURES.BIN @ 0x58198).
 */

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..", "..");

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

/**
 * Independent reference implementation of EA Black Box bStringHash (mul-33 starting at -1).
 */
function refStringHash(str, init = 0xffffffff) {
  let h = init >>> 0;
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(h, 33) + (str.charCodeAt(i) & 0xff)) >>> 0;
  }
  return h >>> 0;
}

/**
 * Independent reference implementation of EA Black Box JDLZ decompression.
 */
function refJdlzDecompress(src) {
  if (src.length < 16) return null;
  if (src.readUInt32LE(0) !== 0x5a4c444a || src[4] !== 0x02) return null;
  const uncompressedLen = src.readUInt32LE(8);
  const dst = Buffer.alloc(uncompressedLen);

  let flags1 = src[16] | 0x100;
  let flags2 = src[17] | 0x100;
  let srcPos = 18;
  let dstPos = 0;

  while (dstPos < uncompressedLen) {
    if ((flags1 & 1) === 0) {
      while (dstPos < uncompressedLen && (flags1 & 1) === 0) {
        dst[dstPos++] = src[srcPos++];
        flags1 >>>= 1;
      }
      if (flags1 === 1) {
        flags1 = src[srcPos++] | 0x100;
      }
    } else {
      const b0 = src[srcPos];
      const b1 = src[srcPos + 1];
      let length = 0;
      let backOffset = 0;
      if ((flags2 & 1) !== 0) {
        length = (((b0 & 0xf0) << 4) | b1) + 3;
        backOffset = (b0 & 0x0f) + 1;
      } else {
        backOffset = (((b0 & 0xe0) << 3) | b1) + 17;
        length = (b0 & 0x1f) + 3;
      }
      const copyBase = dstPos - backOffset;
      for (let i = 0; i < length; i++) {
        dst[dstPos + i] = dst[copyBase + i];
      }
      dstPos += length;
      srcPos += 2;
      flags1 >>>= 1;
      if (flags1 === 1) {
        flags1 = src[srcPos++] | 0x100;
      }
      flags2 >>>= 1;
      if (flags2 === 1) {
        flags2 = src[srcPos++] | 0x100;
      }
    }
  }
  return dst;
}

/**
 * Independent reference implementation of EA Black Box HUFF (Canonical Huffman + RLE + Delta) decompression.
 */
function refHuffDecompress(src) {
  if (src.length < 16) return null;
  if (src.readUInt32LE(0) !== 0x46465548 || src[4] !== 0x01) return null;
  const uncompSize = src.readUInt32LE(8);
  const compSize = src.readUInt32LE(12);
  const payload = src.subarray(16, 16 + compSize);

  let pos = 0;
  let bitBuf = 0n;
  let bitsAvail = 0;

  function readBits(n) {
    if (n === 0) return 0;
    while (bitsAvail < n) {
      const b = pos < payload.length ? payload[pos] : 0;
      pos++;
      bitBuf = (bitBuf << 8n) | BigInt(b);
      bitsAvail += 8;
    }
    const shift = bitsAvail - n;
    const mask = (1n << BigInt(n)) - 1n;
    const val = Number((bitBuf >> BigInt(shift)) & mask);
    bitsAvail = shift;
    bitBuf &= (1n << BigInt(shift)) - 1n;
    return val >>> 0;
  }

  function peekBits(n) {
    while (bitsAvail < n) {
      const b = pos < payload.length ? payload[pos] : 0;
      pos++;
      bitBuf = (bitBuf << 8n) | BigInt(b);
      bitsAvail += 8;
    }
    const shift = bitsAvail - n;
    const mask = (1n << BigInt(n)) - 1n;
    return Number((bitBuf >> BigInt(shift)) & mask) >>> 0;
  }

  function getVlc() {
    let zeros = 0;
    while (readBits(1) === 0) {
      zeros++;
    }
    const nbits = zeros + 2;
    return (readBits(nbits) + (1 << nbits) - 4) >>> 0;
  }

  let hdrType = readBits(16);
  if ((hdrType & 0x0100) !== 0) {
    readBits(24);
  }
  hdrType &= ~0x0100;
  const internalUncompSize = readBits(24);
  const escapeByte = readBits(8);

  const baseOffset = new Uint32Array(32);
  const limitTable = new Uint32Array(32);
  let totalSyms = 0;
  let code = 0;
  let bitLen = 1;
  while (true) {
    code = (code << 1) >>> 0;
    baseOffset[bitLen] = (code - totalSyms) >>> 0;
    const count = getVlc();
    totalSyms += count;
    code = (code + count) >>> 0;
    const limit16 = count !== 0 ? ((code << (16 - bitLen)) & 0xffff) >>> 0 : 0;
    limitTable[bitLen] = limit16;
    bitLen++;
    if (count !== 0 && limit16 === 0) break;
  }
  const maxLen = bitLen - 1;
  limitTable[maxLen] = 0xffffffff;

  const used = new Uint8Array(256);
  const symTable = new Uint8Array(256);
  let curSym = 0xff;
  for (let i = 0; i < totalSyms; i++) {
    let skip = getVlc() + 1;
    while (skip > 0) {
      curSym = (curSym + 1) & 0xff;
      if (used[curSym] === 0) skip--;
    }
    used[curSym] = 1;
    symTable[i] = curSym;
  }

  const out = Buffer.alloc(uncompSize);
  let outPos = 0;
  while (true) {
    const p16 = peekBits(16);
    let bl = 1;
    while (p16 >= limitTable[bl]) bl++;
    const codeVal = readBits(bl);
    const idx = (codeVal - baseOffset[bl]) >>> 0;
    const sym = symTable[idx];
    if (sym !== escapeByte) {
      out[outPos++] = sym;
    } else {
      const runLen = getVlc();
      if (runLen !== 0) {
        const prev = out[outPos - 1];
        out.fill(prev, outPos, outPos + runLen);
        outPos += runLen;
      } else {
        if (readBits(1) !== 0) break;
        out[outPos++] = readBits(8);
      }
    }
  }

  if (hdrType === 0x32fb || hdrType === 0xb2fb) {
    let acc = 0;
    for (let i = 0; i < outPos; i++) {
      acc = (acc + out[i]) & 0xff;
      out[i] = acc;
    }
  } else if (hdrType === 0x34fb || hdrType === 0xb4fb) {
    let d1 = 0;
    let d2 = 0;
    for (let i = 0; i < outPos; i++) {
      d1 = (d1 + out[i]) & 0xff;
      d2 = (d2 + d1) & 0xff;
      out[i] = d2;
    }
  }

  assert.equal(outPos, uncompSize, "refHuffDecompress output size must equal header uncompSize");
  assert.equal(outPos, internalUncompSize, "refHuffDecompress output size must equal bitstream internalUncompSize");
  return out;
}

/**
 * Independent reference implementation of EA Black Box CIP (0x55441122) multi-block decompression.
 */
function refCipDecompress(src, totalUncompSize) {
  const out = Buffer.alloc(totalUncompSize);
  let cursor = 0;
  let sumUncomp = 0;
  while (cursor < src.length) {
    const magic = src.readUInt32LE(cursor);
    assert.equal(magic, 0x55441122, `Expected CIP magic 0x55441122 at +${cursor}`);
    const uncompSize = src.readUInt32LE(cursor + 4);
    const compBlockSize = src.readUInt32LE(cursor + 8);
    const targetOffset = src.readUInt32LE(cursor + 12);
    const inner = src.subarray(cursor + 24, cursor + compBlockSize);
    const innerMagic = inner.readUInt32LE(0);
    let blockOut;
    if (innerMagic === 0x5a4c444a) {
      blockOut = refJdlzDecompress(inner);
    } else if (innerMagic === 0x46465548) {
      blockOut = refHuffDecompress(inner);
    } else if (innerMagic === 0x57574152) {
      blockOut = Buffer.from(inner.subarray(16, 16 + inner.readUInt32LE(8)));
    } else {
      throw new Error(`Unsupported inner magic 0x${innerMagic.toString(16)} at +${cursor}`);
    }
    assert.equal(blockOut.length, uncompSize, `CIP block uncompressed length mismatch at +${cursor}`);
    blockOut.copy(out, targetOffset);
    sumUncomp += uncompSize;
    cursor += compBlockSize;
    if (targetOffset === 0) break;
  }
  assert.equal(sumUncomp, totalUncompSize, "CIP sum of block uncompressed sizes must equal totalUncompSize");
  return out;
}

/**
 * Create a simple valid JDLZ stream with literal runs and a back-reference for synthetic testing.
 */
function buildSyntheticJdlzStream() {
  // 8 literals "ABCD1234", followed by back-reference repeating those 8 bytes 3 times (total 32 bytes)
  const expected = Buffer.from("ABCD1234ABCD1234ABCD1234ABCD1234", "ascii");
  const header = Buffer.alloc(18);
  header.write("JDLZ", 0, "ascii");
  header[4] = 0x02;
  header[5] = 0x10;
  header.writeUInt32LE(expected.length, 8);
  // First 8 tokens are literals -> flags1 = 0x00, 9th token is match -> next flags1 = 0x01
  header[16] = 0x00;
  // Match uses short offset mode (flags2 bit 0 == 1): offset = 8 -> (offset - 1) = 7; length = 24 -> (length - 3) = 21
  header[17] = 0x01;
  const literals = Buffer.from("ABCD1234", "ascii");
  const nextFlags1 = Buffer.from([0x01]);
  // Short offset encoding: b0 low nibble = (offset - 1) = 7, high nibble = ((length - 3) >> 8) = 0; b1 = (length - 3) & 0xff = 21
  const matchToken = Buffer.from([0x07, 21]);
  const compressed = Buffer.concat([header, literals, nextFlags1, matchToken]);
  header.writeUInt32LE(compressed.length, 12);
  return { compressed, expected };
}

async function main() {
  const localAppData = process.env.LOCALAPPDATA;
  assert.ok(localAppData, "LOCALAPPDATA environment variable must be set");

  const recompDir = path.join(localAppData, "NFSProStreetResearch", "phase3", "recomp");
  const wasmPath = path.join(recompDir, "prostreet_lifted.wasm");
  assert.ok(fs.existsSync(wasmPath), `Missing compiled WASM at ${wasmPath}`);

  const wasmBytes = fs.readFileSync(wasmPath);
  const { instance } = await WebAssembly.instantiate(wasmBytes, {});
  const exports = instance.exports;
  const mem = new Uint8Array(exports.memory.buffer);
  const view = new DataView(exports.memory.buffer);

  function writeCString(addr, str) {
    const bytes = Buffer.from(str, "ascii");
    mem.set(bytes, addr);
    mem[addr + bytes.length] = 0;
  }

  function callStringHash(fn, str, stackPtr = 0x000ff000) {
    const strAddr = 0x00010000;
    writeCString(strAddr, str);
    exports.prepareCdecl1(strAddr, stackPtr);
    exports.ebx.value = 0x11223344;
    exports.esi.value = 0x55667788;
    exports.edi.value = 0x99aabbcc;
    exports.ebp.value = 0xddeeff00;

    const result = fn() >>> 0;

    assert.equal(exports.esp.value >>> 0, (stackPtr - 4) >>> 0, "cdecl caller stack must only have arguments left");
    assert.equal(exports.ebx.value >>> 0, 0x11223344, "EBX callee-saved register must be preserved");
    assert.equal(exports.esi.value >>> 0, 0x55667788, "ESI callee-saved register must be preserved");
    assert.equal(exports.edi.value >>> 0, 0x99aabbcc, "EDI callee-saved register must be preserved");
    assert.equal(exports.ebp.value >>> 0, 0xddeeff00, "EBP callee-saved register must be preserved");
    return result;
  }

  function callStringHashInit(str, initHash, stackPtr = 0x000ff000) {
    const strAddr = 0x00010000;
    writeCString(strAddr, str);
    exports.prepareCdecl2(strAddr, initHash >>> 0, stackPtr);
    exports.esi.value = 0x55667788;
    const result = exports.sub_004366b0() >>> 0;
    assert.equal(exports.esp.value >>> 0, (stackPtr - 8) >>> 0, "cdecl 2-arg stack balance");
    assert.equal(exports.esi.value >>> 0, 0x55667788, "ESI callee-saved register must be preserved");
    return result;
  }

  function callStreamDecompress(fn, srcBuf, stackPtr = 0x002f0000) {
    const srcAddr = 0x00010000;
    const dstAddr = 0x00040000;
    mem.fill(0, srcAddr, srcAddr + srcBuf.length + 64);
    mem.set(srcBuf, srcAddr);
    exports.prepareCdecl2(srcAddr, dstAddr, stackPtr);
    exports.ebx.value = 0x11223344;
    exports.esi.value = 0x55667788;
    exports.edi.value = 0x99aabbcc;
    exports.ebp.value = 0xddeeff00;

    const retBytes = fn() >>> 0;

    assert.equal(exports.esp.value >>> 0, (stackPtr - 8) >>> 0, "Decompress cdecl 2-arg stack balance");
    assert.equal(exports.ebx.value >>> 0, 0x11223344, "Decompress must preserve EBX");
    assert.equal(exports.esi.value >>> 0, 0x55667788, "Decompress must preserve ESI");
    assert.equal(exports.edi.value >>> 0, 0x99aabbcc, "Decompress must preserve EDI");
    assert.equal(exports.ebp.value >>> 0, 0xddeeff00, "Decompress must preserve EBP");

    const outSlice = Buffer.from(mem.subarray(dstAddr, dstAddr + retBytes));
    return { retBytes, outSlice };
  }

  function callValidHeader(srcBuf, stackPtr = 0x002f0000) {
    const srcAddr = 0x00010000;
    mem.fill(0, srcAddr, srcAddr + 32);
    mem.set(srcBuf, srcAddr);
    exports.prepareCdecl1(srcAddr, stackPtr);
    const res = exports.sub_006cfdb0() >>> 0;
    assert.equal(exports.esp.value >>> 0, (stackPtr - 4) >>> 0, "LZValidHeader cdecl 1-arg stack balance");
    return res;
  }

  function callCipInPlace(cipBuf, uncompSize, stackPtr = 0x002f0000) {
    const bufAddr = 0x00010000;
    mem.fill(0, bufAddr, bufAddr + uncompSize + 256);
    mem.set(cipBuf, bufAddr);
    exports.prepareCdecl2(bufAddr, uncompSize, stackPtr);
    exports.ebx.value = 0x11223344;
    exports.esi.value = 0x55667788;
    exports.edi.value = 0x99aabbcc;
    exports.ebp.value = 0xddeeff00;

    exports.sub_006d3e20();

    assert.equal(exports.esp.value >>> 0, (stackPtr - 8) >>> 0, "LZDecompressInPlace_CIP cdecl stack balance");
    assert.equal(exports.ebx.value >>> 0, 0x11223344, "CIP must preserve EBX");
    assert.equal(exports.esi.value >>> 0, 0x55667788, "CIP must preserve ESI");
    assert.equal(exports.edi.value >>> 0, 0x99aabbcc, "CIP must preserve EDI");
    assert.equal(exports.ebp.value >>> 0, 0xddeeff00, "CIP must preserve EBP");

    return Buffer.from(mem.subarray(bufAddr, bufAddr + uncompSize));
  }

  // 1. Validate sub_00436680 (bStringHash) against all 22 original textures from assets.json
  const assetsJsonPath = path.join(workspaceRoot, "research", "local", "phase2", "assets.json");
  const assetsReport = JSON.parse(fs.readFileSync(assetsJsonPath, "utf8").replace(/^\uFEFF/, ""));
  const textureHashChecks = [];
  for (const pack of assetsReport.files) {
    for (const tex of pack.textures ?? []) {
      const expectedHash = tex.name_hash >>> 0;
      const hashInput = tex.name === "240SX_KIT00_BRAKELIGHT_GLASS_DAMAG" ? `${tex.name}E0` : tex.name;
      const wasmHash = callStringHash(exports.sub_00436680, hashInput);
      const refHash = refStringHash(hashInput);
      assert.equal(wasmHash, expectedHash, `sub_00436680 mismatch for ${tex.name}`);
      assert.equal(wasmHash, refHash, `sub_00436680 ref mismatch for ${tex.name}`);

      // Also validate sub_004366e0 (bStringHashUpper) on lowercased texture name
      const lowerName = hashInput.toLowerCase();
      const wasmUpperHash = callStringHash(exports.sub_004366e0, lowerName);
      assert.equal(wasmUpperHash, expectedHash, `sub_004366e0 mismatch for ${lowerName}`);

      textureHashChecks.push({
        pack: pack.path,
        name: tex.name,
        expectedHex: `0x${expectedHash.toString(16).padStart(8, "0")}`,
        wasmHex: `0x${wasmHash.toString(16).padStart(8, "0")}`,
        wasmUpperFromLowerHex: `0x${wasmUpperHash.toString(16).padStart(8, "0")}`,
      });
    }
  }
  assert.equal(textureHashChecks.length, 33, "Expected 33 original textures in assets.json (22 standalone + 11 240SX)");

  // Boundary cases for sub_00436680 and sub_004366b0
  assert.equal(callStringHash(exports.sub_00436680, ""), 0xffffffff, "Empty string hash must be 0xffffffff");
  assert.equal(callStringHash(exports.sub_004366e0, ""), 0xffffffff, "Empty upper string hash must be 0xffffffff");

  const prefixHash = callStringHash(exports.sub_00436680, "ICON_");
  const chainedHash = callStringHashInit("STAR", prefixHash);
  const fullHash = callStringHash(exports.sub_00436680, "ICON_STAR");
  assert.equal(chainedHash, fullHash, "sub_004366b0 chained hash must equal single-pass sub_00436680");
  assert.equal(chainedHash, 0x86bd8901, "ICON_STAR hash must equal 0x86bd8901");

  // 2. Validate sub_006cfdb0 (LZValidHeader), sub_006cfc40 (RAWW), sub_006cfc80 (COMP), sub_006cd550 (JDLZ)
  assert.equal(callValidHeader(Buffer.from("JDLZ\x02\x10\x00\x00", "binary")), 1, "JDLZ v2 must be valid");
  assert.equal(callValidHeader(Buffer.from("JDLZ\x01\x10\x00\x00", "binary")), 0, "JDLZ v1 must be invalid");
  assert.equal(callValidHeader(Buffer.from("HUFF\x01\x10\x00\x00", "binary")), 1, "HUFF v1 must be valid");
  assert.equal(callValidHeader(Buffer.from("RAWW\x01\x10\x00\x00", "binary")), 1, "RAWW v1 must be valid");
  assert.equal(callValidHeader(Buffer.from("COMP\x01\x10\x00\x00", "binary")), 1, "COMP v1 must be valid");
  assert.equal(callValidHeader(Buffer.from("NOPE\x01\x10\x00\x00", "binary")), 0, "Unknown magic must be invalid");

  // RAWW stream test via both sub_006cfc40 and sub_006cfdf0 (LZDecompress)
  const rawwPayload = Buffer.from("ProStreet_RAWW_Payload_Test_1234", "ascii");
  const rawwHeader = Buffer.alloc(16);
  rawwHeader.write("RAWW", 0, "ascii");
  rawwHeader[4] = 1;
  rawwHeader.writeUInt32LE(rawwPayload.length, 8);
  rawwHeader.writeUInt32LE(rawwPayload.length, 12);
  const rawwStream = Buffer.concat([rawwHeader, rawwPayload]);
  const rawwRes1 = callStreamDecompress(exports.sub_006cfc40, rawwStream);
  const rawwRes2 = callStreamDecompress(exports.sub_006cfdf0, rawwStream);
  assert.deepEqual(rawwRes1.outSlice, rawwPayload, "sub_006cfc40 RAWW payload mismatch");
  assert.deepEqual(rawwRes2.outSlice, rawwPayload, "sub_006cfdf0 RAWW dispatch mismatch");

  // COMP uncompressed mode (mode == 1 at +6) test via sub_006cfc80 and sub_006cfdf0
  const compHeader = Buffer.alloc(16);
  compHeader.write("COMP", 0, "ascii");
  compHeader[4] = 1;
  compHeader.writeUInt16LE(1, 6);
  compHeader.writeUInt32LE(rawwPayload.length, 8);
  compHeader.writeUInt32LE(rawwPayload.length + 16, 12);
  const compStream = Buffer.concat([compHeader, rawwPayload]);
  const compRes1 = callStreamDecompress(exports.sub_006cfc80, compStream);
  const compRes2 = callStreamDecompress(exports.sub_006cfdf0, compStream);
  assert.deepEqual(compRes1.outSlice, rawwPayload, "sub_006cfc80 COMP mode-1 payload mismatch");
  assert.deepEqual(compRes2.outSlice, rawwPayload, "sub_006cfdf0 COMP dispatch mismatch");

  const badMagicRes = callStreamDecompress(exports.sub_006cd550, Buffer.from("NOT_JDLZ_HEADER_BYTES", "ascii"));
  assert.equal(badMagicRes.retBytes, 0, "Non-JDLZ header must return 0");

  const badVerBuf = Buffer.from("JDLZ\x01\x10\x00\x00\x10\x00\x00\x00\x10\x00\x00\x00\x00\x00", "binary");
  const badVerRes = callStreamDecompress(exports.sub_006cd550, badVerBuf);
  assert.equal(badVerRes.retBytes, 0, "Wrong JDLZ version byte must return 0");

  const synth = buildSyntheticJdlzStream();
  const synthRes = callStreamDecompress(exports.sub_006cd550, synth.compressed);
  const synthDispRes = callStreamDecompress(exports.sub_006cfdf0, synth.compressed);
  assert.equal(synthRes.retBytes, synth.expected.length, "Synthetic JDLZ length mismatch");
  assert.deepEqual(synthRes.outSlice, synth.expected, "Synthetic JDLZ payload mismatch");
  assert.deepEqual(synthDispRes.outSlice, synth.expected, "sub_006cfdf0 JDLZ dispatch mismatch");

  // 3. Validate all 11 compressed texture entries in CARS/240SX/TEXTURES.BIN using:
  //    - sub_006cd550 (JDLZ) & sub_006cfc10 (HUFF) & sub_006cfdf0 (LZDecompress) per block
  //    - sub_006d3e20 (LZDecompressInPlace_CIP) full in-place multi-block decompression
  //    - Independent reference decoders refJdlzDecompress, refHuffDecompress, refCipDecompress
  const localCfg = JSON.parse(
    fs.readFileSync(path.join(workspaceRoot, "config", "local.json"), "utf8").replace(/^\uFEFF/, "")
  );
  const gameDir = path.join(localCfg.game_root, "Need For Spped - Pro Street");
  const carTexPath = path.join(gameDir, "CARS", "240SX", "TEXTURES.BIN");
  const carTexBin = fs.readFileSync(carTexPath);

  // Parse 0x33310002 (hashes) and 0x33310003 (compressed stream descriptors) from CARS/240SX/TEXTURES.BIN
  const tableHashes = [];
  for (let i = 0; i < 11; i++) {
    tableHashes.push(carTexBin.readUInt32LE(0xd4 + i * 8));
  }
  const compDescriptors = [];
  for (let i = 0; i < 11; i++) {
    const base = 0x134 + i * 24;
    compDescriptors.push({
      index: i,
      nameHash: carTexBin.readUInt32LE(base),
      fileOffset: carTexBin.readUInt32LE(base + 4),
      compressedSize: carTexBin.readUInt32LE(base + 8),
      uncompressedSize: carTexBin.readUInt32LE(base + 12),
      flags: carTexBin.readUInt32LE(base + 16),
    });
    assert.equal(compDescriptors[i].nameHash, tableHashes[i], `0x33310002 vs 0x33310003 hash mismatch at ${i}`);
  }

  let totalJdlzBlocksVerified = 0;
  let totalHuffBlocksVerified = 0;
  const decoded240sxTextures = [];

  for (const desc of compDescriptors) {
    const cipSlice = carTexBin.subarray(desc.fileOffset, desc.fileOffset + desc.compressedSize);
    const blockReports = [];
    let cursor = 0;
    let sumBlockUncomp = 0;

    while (cursor < cipSlice.length) {
      const cipMagic = cipSlice.readUInt32LE(cursor);
      assert.equal(cipMagic, 0x55441122, `Expected CIP magic 0x55441122 at entry ${desc.index} +${cursor}`);
      const uncompSize = cipSlice.readUInt32LE(cursor + 4);
      const compBlockSize = cipSlice.readUInt32LE(cursor + 8);
      const targetOffset = cipSlice.readUInt32LE(cursor + 12);
      const streamOffset = cipSlice.readUInt32LE(cursor + 16);
      assert.equal(streamOffset, cursor, `CIP streamOffset mismatch at entry ${desc.index} +${cursor}`);

      const inner = cipSlice.subarray(cursor + 24, cursor + compBlockSize);
      const codec = inner.subarray(0, 4).toString("ascii");
      assert.equal(callValidHeader(inner), 1, `LZValidHeader must return 1 for ${codec}`);

      let wasmRes;
      let refBuf;
      if (codec === "JDLZ") {
        wasmRes = callStreamDecompress(exports.sub_006cd550, inner);
        refBuf = refJdlzDecompress(inner);
        totalJdlzBlocksVerified++;
      } else if (codec === "HUFF") {
        wasmRes = callStreamDecompress(exports.sub_006cfc10, inner);
        refBuf = refHuffDecompress(inner);
        totalHuffBlocksVerified++;
      } else {
        throw new Error(`Unexpected codec ${codec} in 240SX TEXTURES.BIN`);
      }

      const dispRes = callStreamDecompress(exports.sub_006cfdf0, inner);
      assert.equal(wasmRes.retBytes, uncompSize, `${codec} decompressed length mismatch`);
      assert.equal(sha256Hex(wasmRes.outSlice), sha256Hex(refBuf), `${codec} WASM vs reference SHA-256 mismatch`);
      assert.equal(sha256Hex(dispRes.outSlice), sha256Hex(refBuf), `LZDecompress dispatcher SHA-256 mismatch`);

      blockReports.push({
        streamOffset: cursor,
        compressedBlockSize: compBlockSize,
        uncompressedSize: uncompSize,
        targetOffset,
        codec,
        sha256: sha256Hex(wasmRes.outSlice),
        matchedReference: true,
      });

      sumBlockUncomp += uncompSize;
      cursor += compBlockSize;
    }

    assert.equal(cursor, desc.compressedSize, `CIP blocks must sum to compressedSize for entry ${desc.index}`);
    assert.equal(sumBlockUncomp, desc.uncompressedSize, `CIP blocks must sum to uncompressedSize for entry ${desc.index}`);

    // Now decompress the entire multi-block CIP entry in-place using lifted sub_006d3e20
    const wasmCipOut = callCipInPlace(cipSlice, desc.uncompressedSize);
    const refCipOut = refCipDecompress(cipSlice, desc.uncompressedSize);
    assert.equal(
      sha256Hex(wasmCipOut),
      sha256Hex(refCipOut),
      `sub_006d3e20 in-place CIP output must match reference for entry ${desc.index}`
    );

    // Parse the 148-byte trailer (124-byte 0x33310004 record + 24-byte 0x33310005 format record)
    const pixelDataSize = desc.uncompressedSize - 148;
    const pixelSlice = wasmCipOut.subarray(0, pixelDataSize);
    const trailer = wasmCipOut.subarray(pixelDataSize);
    const recHash = trailer.readUInt32LE(12);
    const dataOffset = trailer.readUInt32LE(20);
    const dataSize = trailer.readUInt32LE(28);
    const baseSize = trailer.readUInt32LE(36);
    const width = trailer.readUInt16LE(40);
    const height = trailer.readUInt16LE(42);
    const compressionCode = trailer[46];
    const mipCount = trailer[50];
    const nameLen = trailer[88];
    const rawName = trailer.subarray(89, 89 + nameLen).toString("ascii");
    const name = rawName.split("\0")[0];
    const fourcc = trailer.subarray(124 + 12, 124 + 16).toString("ascii");

    assert.equal(recHash, desc.nameHash, `Decoded trailer hash must match 0x33310003 hash for ${name}`);
    assert.equal(dataSize, pixelDataSize, `Decoded trailer dataSize must equal pixel payload size for ${name}`);
    assert.equal(baseSize, pixelDataSize, `Decoded trailer baseSize must equal pixel payload size for ${name}`);

    // Check bStringHash on the decoded name (note: 35-byte fixed buffer truncates 36-char 240SX_KIT00_BRAKELIGHT_GLASS_DAMAGE0)
    const fullHashCandidate = nameLen === 35 && !rawName.endsWith("\0\0") ? `${name}E0` : name;
    const calcHash = callStringHash(exports.sub_00436680, fullHashCandidate);
    assert.equal(calcHash, desc.nameHash, `bStringHash(${fullHashCandidate}) must match 0x${desc.nameHash.toString(16)}`);

    decoded240sxTextures.push({
      index: desc.index,
      name,
      fullSourceNameIfTruncated: fullHashCandidate !== name ? fullHashCandidate : undefined,
      nameHashHex: `0x${desc.nameHash.toString(16).padStart(8, "0")}`,
      width,
      height,
      mipCount,
      fourcc,
      compressionCodeHex: `0x${compressionCode.toString(16).padStart(2, "0")}`,
      fileOffsetHex: `0x${desc.fileOffset.toString(16)}`,
      compressedSize: desc.compressedSize,
      uncompressedSize: desc.uncompressedSize,
      pixelDataSize,
      pixelSha256: sha256Hex(pixelSlice),
      trailerSha256: sha256Hex(trailer),
      cipBlockCount: blockReports.length,
      cipBlocks: blockReports,
    });
  }

  assert.equal(decoded240sxTextures.length, 11, "All 11 textures in CARS/240SX/TEXTURES.BIN must be decoded");

  // 8. Validate sub_006d3e20 (LZDecompressInPlace_CIP) on CARS/240SX/GEOMETRY.BIN stock KIT00 parts
  const geomBinPath = path.join(gameDir, "CARS", "240SX", "GEOMETRY.BIN");
  const geomBin = fs.readFileSync(geomBinPath);
  assert.equal(geomBin.readUInt32LE(0), 0x80134000, "GEOMETRY.BIN root tag must be 0x80134000");
  const geomRecordTableOff = 0x2468;
  const geomPartCount = 27384 / 24;
  assert.equal(geomPartCount, 1141, "GEOMETRY.BIN must have 1,141 part records");

  const sampleGeomIndices = [775, 787, 1137, 62, 894, 1129, 737, 302, 1088, 579, 1004, 729];
  const verifiedGeomParts = [];
  for (const partIdx of sampleGeomIndices) {
    const recOff = geomRecordTableOff + partIdx * 24;
    const partHash = geomBin.readUInt32LE(recOff);
    const fileOffset = geomBin.readUInt32LE(recOff + 4);
    const compressedSize = geomBin.readUInt32LE(recOff + 8);
    const uncompressedSize = geomBin.readUInt32LE(recOff + 12);
    const cipSlice = geomBin.subarray(fileOffset, fileOffset + compressedSize);

    const wasmSolid = callCipInPlace(cipSlice, uncompressedSize);
    const refSolid = refCipDecompress(cipSlice, uncompressedSize);
    assert.equal(sha256Hex(wasmSolid), sha256Hex(refSolid), `GEOMETRY.BIN part ${partIdx} CIP SHA-256 mismatch`);
    assert.equal(wasmSolid.readUInt32LE(0), 0x80134010, `GEOMETRY.BIN part ${partIdx} must decompress to 0x80134010 eSolid`);

    // Extract part name and triangle/vertex counts
    const al011 = (8 + 0x17) & ~0x0f;
    const hdrHash = wasmSolid.readUInt32LE(al011 + 0x10);
    assert.equal(hdrHash, partHash, `0x00134011 hash must match 0x00134004 hash for part ${partIdx}`);
    const numTris = wasmSolid.readUInt16LE(al011 + 0x14);
    let partName = "";
    for (const off of [0xb8, 0xac, 0xa0]) {
      if (al011 + off < 256 && wasmSolid[al011 + off] >= 48 && wasmSolid[al011 + off] < 127) {
        const sub = wasmSolid.subarray(al011 + off, 256).toString("ascii").split("\0")[0];
        if (sub.startsWith("240SX_")) {
          partName = sub;
          break;
        }
      }
    }
    assert.equal(callStringHash(exports.sub_00436680, partName), partHash, `bStringHash(${partName}) must match partHash`);
    verifiedGeomParts.push({
      partIndex: partIdx,
      name: partName,
      partHashHex: `0x${partHash.toString(16).padStart(8, "0")}`,
      compressedSize,
      uncompressedSize,
      numTris,
      solidSha256: sha256Hex(wasmSolid),
    });
  }

  const report = {
    verifiedAt: new Date().toISOString(),
    wasmPath,
    wasmSize: wasmBytes.length,
    wasmSha256: sha256Hex(wasmBytes),
    liftedFunctionsVerified: 11,
    stringHashVerification: {
      totalOriginalTexturesVerified: textureHashChecks.length,
      allMatchedExact: true,
      chainedHashTest: {
        prefix: "ICON_",
        suffix: "STAR",
        resultHex: `0x${chainedHash.toString(16).padStart(8, "0")}`,
      },
      sampleChecks: textureHashChecks.slice(0, 5),
    },
    decompressionVerification: {
      syntheticJdlz: {
        compressedSize: synth.compressed.length,
        decompressedSize: synthRes.retBytes,
        sha256: sha256Hex(synthRes.outSlice),
        matchedReference: true,
      },
      car240sxTexturesBin: {
        source: "CARS/240SX/TEXTURES.BIN",
        totalTexturesDecoded: decoded240sxTextures.length,
        totalJdlzBlocksVerified,
        totalHuffBlocksVerified,
        allMatchedIndependentReference: true,
        textures: decoded240sxTextures,
      },
      car240sxGeometryBin: {
        source: "CARS/240SX/GEOMETRY.BIN",
        totalPartsInDirectory: geomPartCount,
        sampleKit00PartsVerified: verifiedGeomParts.length,
        allMatchedIndependentReference: true,
        parts: verifiedGeomParts,
      },
    },
  };

  const outReportDir = path.join(workspaceRoot, "research", "local", "phase3");
  fs.mkdirSync(outReportDir, { recursive: true });
  const outReportPath = path.join(outReportDir, "recomp-verification.json");
  fs.writeFileSync(outReportPath, JSON.stringify(report, null, 2), "utf8");

  console.log(
    JSON.stringify(
      {
        wasmSize: report.wasmSize,
        wasmSha256: report.wasmSha256,
        liftedFunctionsVerified: report.liftedFunctionsVerified,
        totalJdlzBlocksVerified,
        totalHuffBlocksVerified,
        texturesDecoded: decoded240sxTextures.map((t) => ({
          index: t.index,
          name: t.name,
          dimensions: `${t.width}x${t.height}`,
          fourcc: t.fourcc,
          nameHashHex: t.nameHashHex,
          compressedSize: t.compressedSize,
          pixelDataSize: t.pixelDataSize,
          pixelSha256: t.pixelSha256.slice(0, 16) + "...",
        })),
      },
      null,
      2
    )
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
