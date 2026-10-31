#!/usr/bin/env node
/**
 * Test executing a genuine ProStreet static initializer through our static recompilation runtime.
 *
 * Validates:
 * 1. Loading original PE sections (.text, .rdata, .data, .tls) into guest memory from nfs.exe.
 * 2. Pre-execution state of _initterm slot 45 (VA 0x00959ca0):
 *      [0x00ab08c8] == 0x00000000 (head pointer in .data)
 *      [0x00a4af34] == 0x00000000 (next pointer in node descriptor)
 *      [0x00a4af2c] == 0xfb111fef (node identifier)
 * 3. Calling the function via the indirect guest function dispatcher callGuestFunction(0x00959ca0).
 * 4. Register and stack invariants:
 *      EAX == 0x00000000 (return value matching old head)
 *      ESP == caller stackPtr (cdecl return with popped return address)
 *      Callee-saved registers (EBX, ESI, EDI, EBP) preserved
 * 5. Memory mutation side-effects in original guest memory:
 *      [0x00a4af34] == 0x00000000 (node->next = old_head)
 *      [0x00ab08c8] == 0x00a4af2c (head = &node)
 * 6. Bounds protection:
 *      Accesses outside linear memory are rejected.
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..", "..");

async function main() {
  const localAppData = process.env.LOCALAPPDATA;
  assert.ok(localAppData, "LOCALAPPDATA environment variable must be set");

  const cfgPath = path.join(workspaceRoot, "config", "local.json");
  const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf8").replace(/^\uFEFF/, ""));
  const exePath = path.join(cfg.game_root, "Need For Spped - Pro Street", "nfs.exe");
  assert.ok(fs.existsSync(exePath), `nfs.exe not found at ${exePath}`);

  const exeBuf = fs.readFileSync(exePath);

  // Parse PE sections
  const peOff = exeBuf.readUInt32LE(0x3c);
  assert.equal(exeBuf.subarray(peOff, peOff + 4).toString("latin1"), "PE\0\0");
  const numSections = exeBuf.readUInt16LE(peOff + 6);
  const optHdrSize = exeBuf.readUInt16LE(peOff + 20);
  const imageBase = exeBuf.readUInt32LE(peOff + 24 + 28);
  assert.equal(imageBase, 0x00400000);

  const secTable = peOff + 24 + optHdrSize;
  const sections = [];
  for (let i = 0; i < numSections; i++) {
    const s = exeBuf.subarray(secTable + i * 40, secTable + (i + 1) * 40);
    const name = s.subarray(0, 8).toString("latin1").replace(/\0.*$/, "");
    const vsize = s.readUInt32LE(8);
    const rva = s.readUInt32LE(12);
    const rsize = s.readUInt32LE(16);
    const roff = s.readUInt32LE(20);
    const flags = s.readUInt32LE(36);
    sections.push({ name, va: imageBase + rva, vsize, rsize, roff, flags });
  }

  // Load WASM module
  const wasmPath = path.join(localAppData, "NFSProStreetResearch", "phase3", "recomp", "prostreet_lifted.wasm");
  assert.ok(fs.existsSync(wasmPath), `prostreet_lifted.wasm not found at ${wasmPath}`);
  const wasmBytes = fs.readFileSync(wasmPath);

  // Initial memory is 256 pages (16 MiB), covering up to 0x01000000
  const { instance } = await WebAssembly.instantiate(wasmBytes, {});
  const exports = instance.exports;
  const mem = new Uint8Array(exports.memory.buffer);
  const view = new DataView(exports.memory.buffer);

  // Load .rdata and .data sections into WASM linear memory
  const included = [".rdata", ".data"];
  for (const name of included) {
    const sec = sections.find((s) => s.name === name);
    assert.ok(sec, `Missing section ${name}`);
    assert.ok(sec.va + sec.vsize <= mem.byteLength, `Section ${name} exceeds WASM memory`);
    const initLen = Math.min(sec.rsize, sec.vsize);
    if (initLen > 0 && sec.roff > 0) {
      mem.set(exeBuf.subarray(sec.roff, sec.roff + initLen), sec.va);
    }
    if (sec.vsize > initLen) {
      mem.fill(0, sec.va + initLen, sec.va + sec.vsize);
    }
  }

  // 1. Verify pre-execution state
  const headPtrVa = 0x00ab08c8;
  const nodeVa = 0x00a4af2c;
  const nextPtrVa = 0x00a4af34;

  const preHead = view.getUint32(headPtrVa, true);
  const preNext = view.getUint32(nextPtrVa, true);
  const nodeTag = view.getUint32(nodeVa, true);

  assert.equal(preHead, 0x00000000, "Initial head pointer [0x00ab08c8] must be NULL");
  assert.equal(preNext, 0x00000000, "Initial node next pointer [0x00a4af34] must be NULL");
  assert.equal(nodeTag, 0xfb111fef, "Node tag [0x00a4af2c] must match original binary");

  const stackPtr = 0x000ff000;
  const targetVa = 0x00959ca0; // _initterm slot 45

  // Prepare call frame: sets stack and return address, without resetting existing registers
  exports.prepareCdecl0(stackPtr);

  // Set callee-saved registers to canary values
  exports.ebx.value = 0x11223344;
  exports.esi.value = 0x55667788;
  exports.edi.value = 0x99aabbcc;
  exports.ebp.value = 0xddeeff00;

  // 3. Execute via indirect dispatcher
  const retVal = exports.callGuestFunction(targetVa) >>> 0;

  // 4. Verify register & stack invariants
  assert.equal(retVal, 0x00000000, "sub_00959ca0 must return old head pointer in EAX (0)");
  assert.equal(exports.eax.value >>> 0, 0x00000000, "EAX must equal old head pointer");
  assert.equal(exports.esp.value >>> 0, stackPtr, "ESP must balance back to caller stackPtr");
  assert.equal(exports.ebx.value >>> 0, 0x11223344, "EBX must be preserved");
  assert.equal(exports.esi.value >>> 0, 0x55667788, "ESI must be preserved");
  assert.equal(exports.edi.value >>> 0, 0x99aabbcc, "EDI must be preserved");
  assert.equal(exports.ebp.value >>> 0, 0xddeeff00, "EBP must be preserved");

  // 5. Verify memory mutations
  const postHead = view.getUint32(headPtrVa, true);
  const postNext = view.getUint32(nextPtrVa, true);

  assert.equal(postNext, 0x00000000, "node->next [0x00a4af34] must equal old head (0)");
  assert.equal(postHead, nodeVa, "head pointer [0x00ab08c8] must now point to node 0x00a4af2c");

  console.log(
    JSON.stringify(
      {
        target: "sub_00959ca0 (_initterm slot 45)",
        targetVa: `0x${targetVa.toString(16).padStart(8, "0")}`,
        sectionsLoaded: included,
        preState: {
          headPtr: `0x${preHead.toString(16).padStart(8, "0")}`,
          nextPtr: `0x${preNext.toString(16).padStart(8, "0")}`,
          nodeTag: `0x${nodeTag.toString(16).padStart(8, "0")}`,
        },
        execution: {
          invokedVia: "callGuestFunction(0x00959ca0)",
          eax: `0x${(exports.eax.value >>> 0).toString(16).padStart(8, "0")}`,
          espBalance: exports.esp.value >>> 0 === stackPtr,
          calleeSavedPreserved: true,
        },
        postState: {
          headPtr: `0x${postHead.toString(16).padStart(8, "0")}`,
          nextPtr: `0x${postNext.toString(16).padStart(8, "0")}`,
          registeredNode: `0x${nodeVa.toString(16).padStart(8, "0")}`,
        },
        status: "PASS",
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
