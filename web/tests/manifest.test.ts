import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { AssetIOEngine } from '../src/io_worker.js';
import { GameManifest } from '../src/io_datacache.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PUBLIC_DIR = path.resolve(__dirname, '../public');

test('AssetIOEngine indexes authentic data-manifest.json correctly', () => {
  const manifestPath = path.join(PUBLIC_DIR, 'data-manifest.json');
  assert.ok(fs.existsSync(manifestPath), 'data-manifest.json must exist');

  const raw = fs.readFileSync(manifestPath, 'utf-8');
  const manifest: GameManifest = JSON.parse(raw);

  assert.ok(manifest.files.length > 3000, 'Must contain over 3,000 files');
  assert.ok(manifest.totalBytes > 5 * 1024 * 1024 * 1024, 'Must exceed 5 GB');

  const engine = new AssetIOEngine('/data/');
  engine.setManifest(manifest);

  // 1. Verify case-insensitive lookup of critical bundles
  const globalB = engine.getManifestEntry('global/globalb.lzc');
  assert.ok(globalB, 'Must resolve global/globalb.lzc');
  assert.equal(globalB?.size, 5540892);

  const car240sx = engine.getManifestEntry('CARS\\240SX\\GEOMETRY.BIN');
  assert.ok(car240sx, 'Must resolve Windows-style path CARS\\240SX\\GEOMETRY.BIN');
  assert.equal(car240sx?.size, 19327188);

  const trackAutopolis = engine.getManifestEntry('TRACKS/L6R_Autopolis.BUN');
  assert.ok(trackAutopolis, 'Must resolve TRACKS/L6R_Autopolis.BUN');
  assert.ok((trackAutopolis?.size ?? 0) > 0);

  // 2. Verify unknown file returns null
  assert.equal(engine.getManifestEntry('NON_EXISTENT_FILE.BIN'), null);
});

