/**
 * Need for Speed ProStreet - AudioRing Binary Protocol & Constants.
 *
 * Defines the shared memory layout between the guest WASM linear memory
 * (populated by runtime/dsound.c) and the browser's AudioWorkletProcessor.
 */

export const AUDIO_RING_MAGIC = 0x4E415544; // 'NAUD'
export const AUDIO_RING_VERSION = 1;
export const AUDIO_RING_FRAMES = 16384;      // 16K stereo frames (~371.5 ms buffer)
export const AUDIO_RATE = 44100;             // Authentic ProStreet mixer sample rate (44.1 kHz)
export const AUDIO_HEADER_WORDS = 64;        // 64 * 4 = 256 bytes header
export const AUDIO_HEADER_BYTES = 256;

// Shared memory address in guest space
export const AUDIO_RING_GUEST_ADDR = 0x02030000;
export const AUDIO_RING_TOTAL_BYTES = AUDIO_HEADER_BYTES + AUDIO_RING_FRAMES * 2 * 4; // 131,328 bytes

// Header field word indices (uint32[64])
export const AR_MAGIC   = 0;
export const AR_VERSION = 1;
export const AR_FRAMES  = 2;
export const AR_RATE    = 3;
export const AR_W       = 4; // Write pointer (frame index modulo 2^32, produced by dsound.c)
export const AR_R       = 5; // Read pointer (frame index modulo 2^32, consumed by AudioWorklet)
export const AR_TARGET  = 6; // Target buffer latency (e.g. 2048 frames ~46 ms)

export interface AudioRingHeader {
  magic: number;
  version: number;
  frames: number;
  rate: number;
  writePos: number;
  readPos: number;
  targetLatency: number;
}

/**
 * Parses and returns the AudioRingHeader from a Uint32Array header view.
 */
export function parseAudioRingHeader(u32View: Uint32Array, offsetWords: number = 0): AudioRingHeader {
  return {
    magic: u32View[offsetWords + AR_MAGIC],
    version: u32View[offsetWords + AR_VERSION],
    frames: u32View[offsetWords + AR_FRAMES],
    rate: u32View[offsetWords + AR_RATE],
    writePos: u32View[offsetWords + AR_W],
    readPos: u32View[offsetWords + AR_R],
    targetLatency: u32View[offsetWords + AR_TARGET],
  };
}

