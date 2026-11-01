/**
 * Need for Speed ProStreet - AudioWorkletProcessor Implementation.
 *
 * Runs on the browser's dedicated high-priority audio rendering thread.
 * Pulls float32 stereo audio frames from the lock-free shared AudioRing
 * and writes them into Web Audio output channels every 128-sample quantum.
 */

import {
  AUDIO_RING_MAGIC,
  AUDIO_RING_FRAMES,
  AUDIO_HEADER_WORDS,
  AR_MAGIC,
  AR_VERSION,
  AR_FRAMES,
  AR_RATE,
  AR_W,
  AR_R,
  AR_TARGET,
} from './audio_proto.js';

export interface AudioProcessorStats {
  underflowCount: number;
  overflowCount: number;
  totalFramesRendered: number;
}

/**
 * Core lock-free audio ring frame consumer.
 * Operates on Uint32Array header and Float32Array PCM buffer.
 */
export class ProStreetAudioConsumer {
  private u32Hdr: Uint32Array;
  private f32Pcm: Float32Array;
  private headerOffset: number;
  private framesCapacity: number;
  public stats: AudioProcessorStats = {
    underflowCount: 0,
    overflowCount: 0,
    totalFramesRendered: 0,
  };

  constructor(
    sharedBuffer: ArrayBufferLike,
    byteOffset: number = 0,
    framesCapacity: number = AUDIO_RING_FRAMES
  ) {
    this.headerOffset = byteOffset / 4;
    this.framesCapacity = framesCapacity;
    this.u32Hdr = new Uint32Array(sharedBuffer, byteOffset, AUDIO_HEADER_WORDS);
    this.f32Pcm = new Float32Array(
      sharedBuffer,
      byteOffset + AUDIO_HEADER_WORDS * 4,
      this.framesCapacity * 2
    );
  }

  /**
   * Pulls up to `quantumFrames` stereo frames and copies to left/right channel arrays.
   * If not enough frames are available, fills remaining samples with silence (0.0).
   */
  public processQuantum(
    outputLeft: Float32Array,
    outputRight: Float32Array,
    quantumFrames: number = 128
  ): boolean {
    const w = Atomics.load(this.u32Hdr, AR_W);
    let r = this.u32Hdr[AR_R];

    const available = (w - r) >>> 0;
    const mask = this.framesCapacity - 1;

    // Underflow: not enough samples available in ring buffer
    if (available < quantumFrames) {
      this.stats.underflowCount++;
      outputLeft.fill(0.0);
      outputRight.fill(0.0);
      return true;
    }

    // Overflow protection: if producer is too far ahead, skip stale frames
    if (available > this.framesCapacity - 512) {
      this.stats.overflowCount++;
      const targetLatency = this.u32Hdr[AR_TARGET] || 2048;
      r = (w - targetLatency) >>> 0;
    }

    for (let i = 0; i < quantumFrames; ++i) {
      const idx = (r + i) & mask;
      outputLeft[i] = this.f32Pcm[idx * 2 + 0];
      outputRight[i] = this.f32Pcm[idx * 2 + 1];
    }

    this.u32Hdr[AR_R] = (r + quantumFrames) >>> 0;
    this.stats.totalFramesRendered += quantumFrames;
    return true;
  }

  public getAvailableFrames(): number {
    const w = Atomics.load(this.u32Hdr, AR_W);
    const r = this.u32Hdr[AR_R];
    return (w - r) >>> 0;
  }
}

/**
 * Self-contained source code string of the AudioWorkletProcessor
 * for dynamic injection via URL.createObjectURL.
 */
export const AUDIO_WORKLET_PROCESSOR_CODE = `
class ProStreetAudioWorkletProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = options.processorOptions || {};
    const sab = opts.sharedBuffer;
    const byteOffset = opts.byteOffset || 0;
    const framesCap = opts.framesCapacity || 16384;

    this.mask = framesCap - 1;
    this.u32Hdr = new Uint32Array(sab, byteOffset, 64);
    this.f32Pcm = new Float32Array(sab, byteOffset + 256, framesCap * 2);
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0];
    if (!output || output.length < 2) return true;

    const outL = output[0];
    const outR = output[1];
    const quantum = outL.length;

    const w = Atomics.load(this.u32Hdr, 4); // AR_W = 4
    let r = this.u32Hdr[5];                 // AR_R = 5

    const available = (w - r) >>> 0;
    if (available < quantum) {
      outL.fill(0.0);
      outR.fill(0.0);
      return true;
    }

    if (available > 16384 - 512) {
      const target = this.u32Hdr[6] || 2048; // AR_TARGET = 6
      r = (w - target) >>> 0;
    }

    for (let i = 0; i < quantum; ++i) {
      const idx = (r + i) & this.mask;
      outL[i] = this.f32Pcm[idx * 2 + 0];
      outR[i] = this.f32Pcm[idx * 2 + 1];
    }

    this.u32Hdr[5] = (r + quantum) >>> 0;
    return true;
  }
}

registerProcessor('prostreet-audio-processor', ProStreetAudioWorkletProcessor);
`;

