import test from 'node:test';
import assert from 'node:assert/strict';
import {
  HardwareScaler,
  MobileGraphicsManager,
  TextureFormatArbiter,
  RESOLUTION_PRESETS,
  GRAPHICS_PRESETS,
} from '../src/mobile_presets.js';

test('HardwareScaler manages resolution scale and fitPicture CSS', () => {
  const mockCanvas = {
    width: 0,
    height: 0,
    style: {} as any,
  } as HTMLCanvasElement;

  const scaler = new HardwareScaler(mockCanvas);

  // Default is native (1280x720)
  assert.equal(scaler.getPreset(), 'native');
  assert.equal(mockCanvas.width, 1280);
  assert.equal(mockCanvas.height, 720);
  assert.equal(mockCanvas.style.aspectRatio, '16 / 9');
  assert.equal(mockCanvas.style.objectFit, 'contain');

  // Balanced preset (960x540)
  scaler.applyPreset('balanced');
  assert.equal(scaler.getPreset(), 'balanced');
  assert.equal(mockCanvas.width, 960);
  assert.equal(mockCanvas.height, 540);
  assert.equal(mockCanvas.style.imageRendering, 'auto');

  // Performance preset (640x360)
  scaler.applyPreset('performance');
  assert.equal(scaler.getPreset(), 'performance');
  assert.equal(mockCanvas.width, 640);
  assert.equal(mockCanvas.height, 360);
  assert.equal(mockCanvas.style.imageRendering, 'pixelated');
});

test('MobileGraphicsManager configures quality levels and skips heavy passes', () => {
  const mgr = new MobileGraphicsManager('medium');
  assert.equal(mgr.currentSettings.level, 'medium');
  assert.equal(mgr.shouldSkipPostProcessPass('motionBlur'), true);
  assert.equal(mgr.shouldSkipPostProcessPass('dof'), true);
  assert.equal(mgr.shouldSkipPostProcessPass('bloom'), false); // Bloom enabled on medium

  // Set to Low (mobile battery saver)
  mgr.setQuality('low');
  assert.equal(mgr.shouldSkipPostProcessPass('motionBlur'), true);
  assert.equal(mgr.shouldSkipPostProcessPass('dof'), true);
  assert.equal(mgr.shouldSkipPostProcessPass('bloom'), true);
  assert.equal(mgr.shouldSkipPostProcessPass('shadows'), true);
  assert.equal(mgr.currentSettings.maxAnisotropy, 1);

  // Set to Ultra (desktop / high-end tablet)
  mgr.setQuality('ultra');
  assert.equal(mgr.shouldSkipPostProcessPass('motionBlur'), false);
  assert.equal(mgr.shouldSkipPostProcessPass('dof'), false);
  assert.equal(mgr.shouldSkipPostProcessPass('bloom'), false);
  assert.equal(mgr.shouldSkipPostProcessPass('shadows'), false);
  assert.equal(mgr.currentSettings.maxAnisotropy, 16);
});

test('TextureFormatArbiter detects extensions and selects optimal upload strategy', () => {
  const arbiter = new TextureFormatArbiter();

  // Desktop GPU with S3TC
  arbiter.supportsS3TC = true;
  arbiter.supportsASTC = false;
  assert.equal(arbiter.selectStrategy(true), 's3tc');

  // Mobile iOS / Android GPU with ASTC (no S3TC)
  arbiter.supportsS3TC = false;
  arbiter.supportsASTC = true;
  assert.equal(arbiter.selectStrategy(true), 'astc_transcode');

  // Fallback environment (no compressed texture extensions)
  arbiter.supportsS3TC = false;
  arbiter.supportsASTC = false;
  assert.equal(arbiter.selectStrategy(true), 'rgba_decode');

  // Uncompressed texture always uses rgba_decode
  assert.equal(arbiter.selectStrategy(false), 'rgba_decode');
});

test('TextureFormatArbiter transcodes BC1 to ASTC 4x4 blocks', () => {
  const arbiter = new TextureFormatArbiter();

  // Create 1 BC1 block (4x4 pixels = 8 bytes)
  const bc1 = new Uint8Array([
    0x00, 0xF8, // c0: Red (RGB565)
    0xE0, 0x07, // c1: Green (RGB565)
    0xAA, 0x55, 0xAA, 0x55, // 2-bit interpolation indices
  ]);

  const astc = arbiter.transcodeBc1ToAstc4x4(bc1, 4, 4);

  // ASTC block must be exactly 16 bytes per 4x4 block
  assert.equal(astc.length, 16);
  // Block mode index
  assert.equal(astc[0], 0x02);
  // Preserved color endpoints
  assert.equal(astc[2], 0x00);
  assert.equal(astc[3], 0xF8);
  assert.equal(astc[4], 0xE0);
  assert.equal(astc[5], 0x07);
  // Preserved pixel interpolation weights
  assert.equal(astc[6], 0xAA);
  assert.equal(astc[7], 0x55);
});

