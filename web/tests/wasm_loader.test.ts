import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  createGuestMemory,
  createWasiImports,
  ProStreetManifest,
} from '../src/wasm_loader.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PUBLIC_DIR = path.resolve(__dirname, '../public');

test('WasmLoader verifies prostreet.json manifest schema', () => {
  const jsonPath = path.join(PUBLIC_DIR, 'prostreet.json');
  assert.ok(fs.existsSync(jsonPath), 'prostreet.json must exist');

  const raw = fs.readFileSync(jsonPath, 'utf-8');
  const manifest: ProStreetManifest = JSON.parse(raw);

  assert.equal(manifest.pages, 16384); // 1024 MB
  assert.equal(manifest.maxPages, 65536); // 4096 MB
  assert.equal(manifest.guestEnd, 671088640); // 640 MB
  assert.equal(manifest.shards, 32);
  assert.equal(manifest.functions, 31995);
  assert.ok(manifest.size > 0);
});

test('WasmLoader creates guest linear memory according to manifest', () => {
  const manifest: ProStreetManifest = {
    pages: 16,
    maxPages: 32,
    guestEnd: 671088640,
    size: 100,
    opt: '-O3',
    toolchain: 'synthetic-wasm-host',
    shards: 32,
    functions: 31995,
    compiledAt: new Date().toISOString(),
  };

  const mem = createGuestMemory(manifest);
  assert.ok(mem instanceof WebAssembly.Memory);
  assert.ok(mem.buffer.byteLength >= 16 * 65536);
});

test('WasmLoader creates WASI syscall imports and processes fd_write stdout', () => {
  const mem = new WebAssembly.Memory({ initial: 2, maximum: 4 });
  let captured = '';

  const wasi = createWasiImports(mem, (text) => {
    captured += text;
  });

  assert.ok(typeof wasi.proc_exit === 'function');
  assert.ok(typeof wasi.fd_write === 'function');
  assert.ok(typeof wasi.clock_time_get === 'function');

  // Write a string to guest memory at 0x100
  const view = new DataView(mem.buffer);
  const u8 = new Uint8Array(mem.buffer);
  const msg = 'Need for Speed ProStreet Engine Boot\n';
  const encoded = new TextEncoder().encode(msg);
  u8.set(encoded, 0x100);

  // Set up iovec at 0x20: { ptr: 0x100, len: msg.length }
  view.setUint32(0x20, 0x100, true);
  view.setUint32(0x24, encoded.length, true);

  // Invoke fd_write(fd=1, iovs=0x20, iovsLen=1, nwritten=0x30)
  const ret = wasi.fd_write(1, 0x20, 1, 0x30);
  assert.equal(ret, 0);
  assert.equal(view.getUint32(0x30, true), encoded.length);
  assert.equal(captured, msg);
});

test('WasmLoader validates and instantiates prostreet.wasm binary', async () => {
  const wasmPath = path.join(PUBLIC_DIR, 'prostreet.wasm');
  assert.ok(fs.existsSync(wasmPath), 'prostreet.wasm must exist');

  const wasmBytes = fs.readFileSync(wasmPath);
  assert.ok(WebAssembly.validate(wasmBytes), 'prostreet.wasm must be valid WebAssembly');

  const module = await WebAssembly.compile(wasmBytes);
  assert.ok(module instanceof WebAssembly.Module);

  const manifest = JSON.parse(fs.readFileSync(path.join(PUBLIC_DIR, 'prostreet.json'), 'utf-8'));
  const memory = createGuestMemory(manifest);
  const wasi = createWasiImports(memory);
  const instance = await WebAssembly.instantiate(module, {
    env: { memory },
    wasi_snapshot_preview1: wasi,
  });
  assert.ok(instance instanceof WebAssembly.Instance);

  const exp = instance.exports as any;
  assert.ok(typeof exp.prostreet_main === 'function');
  assert.ok(typeof exp.prostreet_get_guest_memory === 'function');
  assert.ok(typeof exp.prostreet_tick === 'function');

  // Verify function invocations
  assert.equal(exp.prostreet_main(0, 0), 0);
  assert.equal(exp.prostreet_get_guest_memory(), 0);
  assert.equal(exp.prostreet_tick(), 0);
});

