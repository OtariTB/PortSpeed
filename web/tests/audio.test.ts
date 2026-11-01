import test from 'node:test';
import assert from 'node:assert/strict';
import {
  AUDIO_RING_MAGIC,
  AUDIO_RING_VERSION,
  AUDIO_RING_FRAMES,
  AUDIO_RATE,
  AUDIO_HEADER_WORDS,
  AUDIO_HEADER_BYTES,
  AR_MAGIC,
  AR_VERSION,
  AR_FRAMES,
  AR_RATE,
  AR_W,
  AR_R,
  AR_TARGET,
  AUDIO_RING_TOTAL_BYTES,
  parseAudioRingHeader,
} from '../src/audio_proto.js';
import {
  ProStreetAudioConsumer,
  AUDIO_WORKLET_PROCESSOR_CODE,
} from '../src/audio_worklet.js';
import { BrowserAudioPipeline } from '../src/audio.js';

test('AudioRing protocol constants and header parser', () => {
  const sab = new ArrayBuffer(AUDIO_RING_TOTAL_BYTES);
  const u32 = new Uint32Array(sab, 0, AUDIO_HEADER_WORDS);

  u32[AR_MAGIC]   = AUDIO_RING_MAGIC;
  u32[AR_VERSION] = AUDIO_RING_VERSION;
  u32[AR_FRAMES]  = AUDIO_RING_FRAMES;
  u32[AR_RATE]    = AUDIO_RATE;
  u32[AR_W]       = 1024;
  u32[AR_R]       = 512;
  u32[AR_TARGET]  = 2048;

  const hdr = parseAudioRingHeader(u32);
  assert.equal(hdr.magic, AUDIO_RING_MAGIC);
  assert.equal(hdr.version, 1);
  assert.equal(hdr.frames, 16384);
  assert.equal(hdr.rate, 44100);
  assert.equal(hdr.writePos, 1024);
  assert.equal(hdr.readPos, 512);
  assert.equal(hdr.targetLatency, 2048);
});

test('ProStreetAudioConsumer renders stereo frames to output channels', () => {
  const sab = new ArrayBuffer(AUDIO_RING_TOTAL_BYTES);
  const u32 = new Uint32Array(sab, 0, AUDIO_HEADER_WORDS);
  const f32 = new Float32Array(sab, AUDIO_HEADER_BYTES, AUDIO_RING_FRAMES * 2);

  // Initialize header
  u32[AR_MAGIC] = AUDIO_RING_MAGIC;
  u32[AR_FRAMES] = AUDIO_RING_FRAMES;
  u32[AR_W] = 0;
  u32[AR_R] = 0;

  // Producer writes 128 frames into ring
  for (let i = 0; i < 128; i++) {
    f32[i * 2 + 0] = 0.5;   // Left
    f32[i * 2 + 1] = -0.75; // Right
  }
  Atomics.store(u32, AR_W, 128);

  const consumer = new ProStreetAudioConsumer(sab, 0, AUDIO_RING_FRAMES);
  assert.equal(consumer.getAvailableFrames(), 128);

  const outLeft = new Float32Array(128);
  const outRight = new Float32Array(128);

  const ok = consumer.processQuantum(outLeft, outRight, 128);
  assert.equal(ok, true);
  assert.equal(outLeft[0], 0.5);
  assert.equal(outRight[0], -0.75);
  assert.equal(outLeft[127], 0.5);
  assert.equal(outRight[127], -0.75);

  // Read cursor should now be 128
  assert.equal(u32[AR_R], 128);
  assert.equal(consumer.getAvailableFrames(), 0);
  assert.equal(consumer.stats.totalFramesRendered, 128);
  assert.equal(consumer.stats.underflowCount, 0);
});

test('ProStreetAudioConsumer conceals underflow with silence', () => {
  const sab = new ArrayBuffer(AUDIO_RING_TOTAL_BYTES);
  const u32 = new Uint32Array(sab, 0, AUDIO_HEADER_WORDS);
  u32[AR_W] = 64; // only 64 frames available, need 128
  u32[AR_R] = 0;

  const consumer = new ProStreetAudioConsumer(sab, 0, AUDIO_RING_FRAMES);
  const outLeft = new Float32Array(128);
  const outRight = new Float32Array(128);
  outLeft.fill(1.0);
  outRight.fill(1.0);

  consumer.processQuantum(outLeft, outRight, 128);

  assert.equal(consumer.stats.underflowCount, 1);
  assert.equal(outLeft[0], 0.0);
  assert.equal(outRight[0], 0.0);
  assert.equal(outLeft[127], 0.0);
  assert.equal(outRight[127], 0.0);
  // Read pointer should remain unchanged on underflow
  assert.equal(u32[AR_R], 0);
});

test('ProStreetAudioConsumer handles circular buffer index wrapping', () => {
  const sab = new ArrayBuffer(AUDIO_RING_TOTAL_BYTES);
  const u32 = new Uint32Array(sab, 0, AUDIO_HEADER_WORDS);
  const f32 = new Float32Array(sab, AUDIO_HEADER_BYTES, AUDIO_RING_FRAMES * 2);

  // Start read cursor 64 frames before wrap boundary (16384 - 64 = 16320)
  const startPos = AUDIO_RING_FRAMES - 64;
  u32[AR_R] = startPos;
  u32[AR_W] = startPos + 128; // will wrap to index 64

  // Populate samples across wrap boundary
  for (let i = 0; i < 128; i++) {
    const idx = (startPos + i) & (AUDIO_RING_FRAMES - 1);
    f32[idx * 2 + 0] = (i + 1) * 0.001;
    f32[idx * 2 + 1] = -(i + 1) * 0.001;
  }

  const consumer = new ProStreetAudioConsumer(sab, 0, AUDIO_RING_FRAMES);
  const outLeft = new Float32Array(128);
  const outRight = new Float32Array(128);

  consumer.processQuantum(outLeft, outRight, 128);

  assert.equal(u32[AR_R], startPos + 128);
  assert.almostEqual = (a: number, b: number) => assert.ok(Math.abs(a - b) < 1e-6);
  assert.almostEqual(outLeft[0], 0.001);
  assert.almostEqual(outRight[0], -0.001);
  assert.almostEqual(outLeft[63], 64 * 0.001);   // Frame before boundary
  assert.almostEqual(outLeft[64], 65 * 0.001);   // Frame after boundary wrap
  assert.almostEqual(outLeft[127], 128 * 0.001);
});

test('BrowserAudioPipeline configures and manages state', () => {
  const pipeline = new BrowserAudioPipeline({
    sampleRate: 44100,
    framesCapacity: 16384,
  });

  assert.equal(pipeline.getState(), 'uninitialized');
  assert.equal(pipeline.getSampleRate(), 44100);
  assert.equal(pipeline.isPlaybackUnlocked(), false);
  assert.ok(AUDIO_WORKLET_PROCESSOR_CODE.includes('prostreet-audio-processor'));
});

