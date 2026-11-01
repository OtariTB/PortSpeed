import test from 'node:test';
import assert from 'node:assert/strict';
import {
  OPFS_BLOCK_SIZE,
  calculateBlockCount,
  calculateBlockRange,
  getCacheKey,
  getAssetUrl,
  MemoryBlockCache,
  GameManifest,
} from '../src/io_datacache.js';
import { AssetIOEngine } from '../src/io_worker.js';
import { VirtualFileSystem } from '../src/vfs.js';

test('OPFS block calculation and range math', () => {
  // Empty file
  assert.equal(calculateBlockCount(0), 0);

  // 1 byte -> 1 block
  assert.equal(calculateBlockCount(1), 1);

  // Exact 1 MiB -> 1 block
  assert.equal(calculateBlockCount(OPFS_BLOCK_SIZE), 1);

  // 1 MiB + 1 byte -> 2 blocks
  assert.equal(calculateBlockCount(OPFS_BLOCK_SIZE + 1), 2);

  // 5.6 GB (~5872025600 bytes) -> 5600 blocks
  assert.equal(calculateBlockCount(5872025600), 5600);

  // Range of block 0 in a 1.5 MiB file
  const r0 = calculateBlockRange(1572864, 0);
  assert.equal(r0.start, 0);
  assert.equal(r0.end, OPFS_BLOCK_SIZE);
  assert.equal(r0.length, OPFS_BLOCK_SIZE);

  // Range of block 1 (tail block)
  const r1 = calculateBlockRange(1572864, 1);
  assert.equal(r1.start, OPFS_BLOCK_SIZE);
  assert.equal(r1.end, 1572864);
  assert.equal(r1.length, 524288); // 0.5 MiB
});

test('Cache key and URL building normalizes paths', () => {
  const key = getCacheKey({ path: 'GLOBAL\\GLOBALB.LZC', size: 12345678, mtime: 1600000000 });
  assert.equal(key, 'GLOBAL_GLOBALB.LZC.12345678.1600000000');

  const url1 = getAssetUrl('/data', 'CARS\\CORVETTE\\GEOMETRY.BIN');
  assert.equal(url1, '/data/CARS/CORVETTE/GEOMETRY.BIN');

  const url2 = getAssetUrl('/data/', '/TRACKS/L1R1.BIN');
  assert.equal(url2, '/data/TRACKS/L1R1.BIN');
});

test('MemoryBlockCache manages blocks and bitmasks', () => {
  const cache = new MemoryBlockCache();
  const sample = new Uint8Array([1, 2, 3, 4, 5]);

  assert.equal(cache.hasBlock('file1', 0), false);
  assert.equal(cache.getBlock('file1', 0), null);

  cache.putBlock('file1', 0, sample);
  assert.equal(cache.hasBlock('file1', 0), true);
  assert.deepEqual(cache.getBlock('file1', 0), sample);

  // Put block 3 (gaps 1 and 2 remain 0)
  cache.putBlock('file1', 3, sample);
  const map = cache.getHaveMap('file1');
  assert.ok(map);
  assert.equal(map[0], 1);
  assert.equal(map[1], 0);
  assert.equal(map[2], 0);
  assert.equal(map[3], 1);
});

test('AssetIOEngine indexes manifest and normalizes paths case-insensitively', () => {
  const engine = new AssetIOEngine('/data');
  const manifest: GameManifest = {
    totalBytes: 2500000,
    files: [
      { path: 'GLOBAL/GLOBALB.LZC', size: 2500000 },
      { path: 'CARS/CORVETTE/GEOMETRY.BIN', size: 500000 },
    ],
  };
  engine.setManifest(manifest);

  const e1 = engine.getManifestEntry('global\\globalb.lzc');
  assert.ok(e1);
  assert.equal(e1.size, 2500000);

  const e2 = engine.getManifestEntry('CARS/CORVETTE/GEOMETRY.BIN');
  assert.ok(e2);
  assert.equal(e2.size, 500000);

  const missing = engine.getManifestEntry('NONEXISTENT.BIN');
  assert.equal(missing, null);
});

test('AssetIOEngine reads across 1 MiB block boundary seamlessly', async () => {
  const engine = new AssetIOEngine('/data');
  const totalSize = OPFS_BLOCK_SIZE + 4096; // 2 blocks

  engine.setManifest({
    totalBytes: totalSize,
    files: [{ path: 'TEST.BIN', size: totalSize }],
  });

  const desc = await engine.open('TEST.BIN');

  // Pre-seed block 0 and block 1 directly into the engine's fallback cache
  const b0 = new Uint8Array(OPFS_BLOCK_SIZE);
  b0.fill(0xAA);
  // Mark end of block 0 with 0x42
  b0[OPFS_BLOCK_SIZE - 2] = 0x42;
  b0[OPFS_BLOCK_SIZE - 1] = 0x43;

  const b1 = new Uint8Array(4096);
  b1.fill(0xBB);
  b1[0] = 0x44;
  b1[1] = 0x45;

  (engine as any).memFallback.putBlock(desc.cacheKey, 0, b0);
  (engine as any).memFallback.putBlock(desc.cacheKey, 1, b1);

  // Read 4 bytes spanning the boundary: [OPFS_BLOCK_SIZE - 2 .. OPFS_BLOCK_SIZE + 2)
  const slice = await engine.read(desc.fd, OPFS_BLOCK_SIZE - 2, 4);
  assert.equal(slice.length, 4);
  assert.equal(slice[0], 0x42);
  assert.equal(slice[1], 0x43);
  assert.equal(slice[2], 0x44);
  assert.equal(slice[3], 0x45);

  engine.close(desc.fd);
});

test('VirtualFileSystem bridges data directly to guest WebAssembly memory', async () => {
  const engine = new AssetIOEngine('/data');
  engine.setManifest({
    totalBytes: 1024,
    files: [{ path: 'GLOBAL/GLOBALB.LZC', size: 1024 }],
  });

  const vfs = new VirtualFileSystem(engine);
  const handle = await vfs.openFile('GLOBAL/GLOBALB.LZC');
  assert.equal(vfs.getFileSize(handle), 1024);
  assert.equal(vfs.getPointer(handle), 0);

  // Pre-populate data in block cache
  const fileData = new Uint8Array(1024);
  for (let i = 0; i < 1024; i++) fileData[i] = i & 0xFF;
  const desc = (engine as any).openFiles.get((vfs as any).handles.get(handle).engineFd);
  (engine as any).memFallback.putBlock(desc.cacheKey, 0, fileData);

  // Create simulated 64 MB guest memory buffer
  const guestMem = new ArrayBuffer(0x4000000);
  const targetVA = 0x02500000; // 37 MB in guest dynamic arena

  // Read 256 bytes
  const bytesRead = await vfs.readBytesToGuest(handle, guestMem, targetVA, 256);
  assert.equal(bytesRead, 256);
  assert.equal(vfs.getPointer(handle), 256);

  // Verify memory content in guest space
  const guestView = new Uint8Array(guestMem, targetVA, 256);
  for (let i = 0; i < 256; i++) {
    assert.equal(guestView[i], i & 0xFF);
  }

  // Set file pointer back and re-read
  vfs.setPointer(handle, 100, 'begin');
  assert.equal(vfs.getPointer(handle), 100);

  vfs.closeFile(handle);
});

test('PreloadFiles tracks progress accurately', async () => {
  const engine = new AssetIOEngine('/data');
  const size1 = 500000;
  const size2 = 500000;

  engine.setManifest({
    totalBytes: size1 + size2,
    files: [
      { path: 'FILE1.BIN', size: size1 },
      { path: 'FILE2.BIN', size: size2 },
    ],
  });

  // Seed blocks
  const desc1 = await engine.open('FILE1.BIN');
  (engine as any).memFallback.putBlock(desc1.cacheKey, 0, new Uint8Array(size1));
  engine.close(desc1.fd);

  const desc2 = await engine.open('FILE2.BIN');
  (engine as any).memFallback.putBlock(desc2.cacheKey, 0, new Uint8Array(size2));
  engine.close(desc2.fd);

  const progressHistory: number[] = [];
  await engine.preloadFiles(['FILE1.BIN', 'FILE2.BIN'], (p) => {
    progressHistory.push(p.percent);
  });

  assert.equal(progressHistory.length, 2);
  assert.equal(progressHistory[0], 50);  // 50% after file 1
  assert.equal(progressHistory[1], 100); // 100% after file 2
});

