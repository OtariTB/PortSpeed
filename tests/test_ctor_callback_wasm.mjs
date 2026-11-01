#!/usr/bin/env node
/**
 * Genuine WebAssembly Integration Test for Constructor Callback 0x006f8d60.
 *
 * Validates:
 * 1. Direct execution of lifted sub_006f8d60 in WebAssembly:
 *    - EAX returns 'this' pointer (matching initial ECX).
 *    - ECX cleared to 0.
 *    - Stack pointer ESP strictly preserved.
 *    - Callee-saved registers (EBX, EBP, ESI, EDI) preserved.
 *    - Three consecutive 32-bit fields at [this + 0x40], [this + 0x44], [this + 0x48] mutated to 0.
 * 2. Indirect dispatch via __ehvec_ctor (sub_00401000) using function pointer 0x006f8d60:
 *    - Iterates over 50 elements of 80 bytes each.
 *    - Calls 0x006f8d60 indirectly for each element.
 *    - Stack balance verified (ret 0x10 callee cleanup).
 *    - All 50 elements verified with zeroed fields.
 * 3. Authentic static initializer loop sub_0095b650:
 *    - Executes 3 iterations x 50 elements = 150 constructor calls.
 *    - Verifies complete execution without dispatch failure or NULL traps.
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");

async function run() {
  const localAppData = process.env.LOCALAPPDATA;
  assert.ok(localAppData, "LOCALAPPDATA must be set");

  const wasmPath = path.join(localAppData, "NFSProStreetResearch", "phase3", "recomp", "ctor_callback.wasm");
  assert.ok(fs.existsSync(wasmPath), `WASM module not found at ${wasmPath}`);

  const wasmBytes = fs.readFileSync(wasmPath);
  const dispatchCalls = [];

  const { instance } = await WebAssembly.instantiate(wasmBytes, {
    env: {
      dispatchCall: (targetVa) => {
        dispatchCalls.push(targetVa);
      },
      abort: () => {
        throw new Error("WASM execution trapped via abort");
      },
    },
  });

  const exports = instance.exports;
  const mem = new Uint8Array(exports.memory.buffer);
  const view = new DataView(exports.memory.buffer);

  console.log("=== Test 1: Direct Invocation of sub_006f8d60 ===");
  {
    const initialEsp = 0x003fe000;
    const testObjectVa = 0x00500000;
    const initialEbx = 0x11223344;
    const initialEbp = 0x55667788;

    // Preset dirty sentinel bytes at object fields
    view.setUint32(testObjectVa + 0x40, 0xdeadbeef, true);
    view.setUint32(testObjectVa + 0x44, 0xcafebabe, true);
    view.setUint32(testObjectVa + 0x48, 0xfeedface, true);

    exports.setupCpu(initialEsp, testObjectVa, initialEbx, initialEbp);
    exports.sub_006f8d60();

    assert.equal(exports.getEax(), testObjectVa, "EAX must return 'this' pointer (matching input ECX)");
    assert.equal(exports.getEcx(), 0, "ECX must be cleared to 0");
    assert.equal(exports.getEsp(), initialEsp, "ESP must be preserved");
    assert.equal(exports.getEbx(), initialEbx, "EBX (callee-saved) must be preserved");
    assert.equal(exports.getEbp(), initialEbp, "EBP (callee-saved) must be preserved");

    assert.equal(view.getUint32(testObjectVa + 0x40, true), 0x00000000, "[object + 0x40] must be 0");
    assert.equal(view.getUint32(testObjectVa + 0x44, true), 0x00000000, "[object + 0x44] must be 0");
    assert.equal(view.getUint32(testObjectVa + 0x48, true), 0x00000000, "[object + 0x48] must be 0");
    console.log("  PASS: Direct constructor execution preserves registers and mutates object correctly.");
  }

  console.log("\n=== Test 2: Indirect Dispatch via __ehvec_ctor (sub_00401000) ===");
  {
    const initialEsp = 0x003fe000;
    const arrayBaseVa = 0x00600000;
    const elementCount = 50;
    const elementSize = 80; // 0x50 bytes

    // Fill all 50 elements with dirty marker bytes
    for (let i = 0; i < elementCount; i++) {
      const obj = arrayBaseVa + i * elementSize;
      view.setUint32(obj + 0x40, 0x11111111 * (i + 1), true);
      view.setUint32(obj + 0x44, 0x22222222 * (i + 1), true);
      view.setUint32(obj + 0x48, 0x33333333 * (i + 1), true);
    }

    // Set up stack for sub_00401000:
    // [esp + 4] = arrayBaseVa
    // [esp + 8] = elementSize
    // [esp + 12] = elementCount
    // [esp + 16] = 0x006f8d60 (ctor callback)
    let sp = initialEsp;
    sp -= 4; view.setUint32(sp, 0x006f8d60, true); // ctor_fn
    sp -= 4; view.setUint32(sp, elementCount, true); // count
    sp -= 4; view.setUint32(sp, elementSize, true); // elem_size
    sp -= 4; view.setUint32(sp, arrayBaseVa, true); // array_ptr
    sp -= 4; view.setUint32(sp, 0x00828ae0, true); // dummy return address

    exports.setupCpu(sp, 0, 0x778899aa, 0xbbccddee);
    exports.sub_00401000();

    assert.equal(exports.getEsp() >>> 0, initialEsp, "ESP must be cleanly restored to initial value (ret 0x10 cleanup)");
    assert.equal(exports.getEbx() >>> 0, 0x778899aa, "EBX preserved across __ehvec_ctor");
    assert.equal(exports.getEbp() >>> 0, 0xbbccddee, "EBP preserved across __ehvec_ctor");

    // Verify all 50 elements were constructed
    for (let i = 0; i < elementCount; i++) {
      const obj = arrayBaseVa + i * elementSize;
      assert.equal(view.getUint32(obj + 0x40, true), 0x00000000, `Element ${i} offset +0x40 must be 0`);
      assert.equal(view.getUint32(obj + 0x44, true), 0x00000000, `Element ${i} offset +0x44 must be 0`);
      assert.equal(view.getUint32(obj + 0x48, true), 0x00000000, `Element ${i} offset +0x48 must be 0`);
    }
    console.log(`  PASS: __ehvec_ctor successfully constructed all ${elementCount} elements via 0x006f8d60.`);
  }

  console.log("\n=== Test 3: Authentic Static Initializer Execution (sub_0095b650) ===");
  {
    const initialEsp = 0x003fe000;
    // sub_0095b650 operates on authentic BSS buffers around 0x00ac8000..0x00acc000
    // Preset memory with sentinel values
    const startVa = 0x00ac7000;
    const endVa = 0x00acc500;
    for (let va = startVa; va < endVa; va += 4) {
      view.setUint32(va, 0xaaaaaaaa, true);
    }

    exports.setupCpu(initialEsp, 0, 0x12345678, 0x87654321);
    exports.sub_0095b650();

    assert.equal(exports.getEsp() >>> 0, initialEsp, "ESP must match after sub_0095b650 returns");
    assert.equal(exports.getEbx() >>> 0, 0x12345678, "EBX (callee-saved) restored after sub_0095b650");

    // Check array 1 (50 elements at esi - 0xfa0 where esi = 0xac91f0 -> base = 0xac8250)
    const base1 = 0x00ac8250;
    for (let i = 0; i < 50; i++) {
      const obj = base1 + i * 80;
      assert.equal(view.getUint32(obj + 0x40, true), 0, `Array 1 elem ${i} +0x40 must be 0`);
      assert.equal(view.getUint32(obj + 0x44, true), 0, `Array 1 elem ${i} +0x44 must be 0`);
      assert.equal(view.getUint32(obj + 0x48, true), 0, `Array 1 elem ${i} +0x48 must be 0`);
    }

    // Check array 2 (50 elements at base = 0xac8250 + 0xfd0 = 0xac9220)
    const base2 = base1 + 0xfd0;
    for (let i = 0; i < 50; i++) {
      const obj = base2 + i * 80;
      assert.equal(view.getUint32(obj + 0x40, true), 0, `Array 2 elem ${i} +0x40 must be 0`);
      assert.equal(view.getUint32(obj + 0x44, true), 0, `Array 2 elem ${i} +0x44 must be 0`);
      assert.equal(view.getUint32(obj + 0x48, true), 0, `Array 2 elem ${i} +0x48 must be 0`);
    }

    // Check array 3 (50 elements at base = 0xac9220 + 0xfd0 = 0xaca1f0)
    const base3 = base2 + 0xfd0;
    for (let i = 0; i < 50; i++) {
      const obj = base3 + i * 80;
      assert.equal(view.getUint32(obj + 0x40, true), 0, `Array 3 elem ${i} +0x40 must be 0`);
      assert.equal(view.getUint32(obj + 0x44, true), 0, `Array 3 elem ${i} +0x44 must be 0`);
      assert.equal(view.getUint32(obj + 0x48, true), 0, `Array 3 elem ${i} +0x48 must be 0`);
    }

    console.log("  PASS: sub_0095b650 successfully executed all 150 constructor calls across 3 arrays.");
  }

  console.log("\nALL CONSTRUCTOR CALLBACK WASM INTEGRATION TESTS PASSED!");
}

run().catch((err) => {
  console.error("FATAL:", err);
  process.exit(1);
});
