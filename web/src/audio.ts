/**
 * Need for Speed ProStreet - Browser Web Audio Pipeline.
 *
 * Initializes AudioContext, registers the AudioWorkletProcessor,
 * connects to destination, and transparently unlocks audio playback on first user gesture.
 */

import {
  AUDIO_RATE,
  AUDIO_RING_GUEST_ADDR,
  AUDIO_RING_FRAMES,
} from './audio_proto.js';
import {
  AUDIO_WORKLET_PROCESSOR_CODE,
  ProStreetAudioConsumer,
} from './audio_worklet.js';

export interface AudioPipelineConfig {
  sampleRate?: number;
  ringByteOffset?: number;
  framesCapacity?: number;
}

export class BrowserAudioPipeline {
  private ctx: AudioContext | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private consumer: ProStreetAudioConsumer | null = null;
  private isUnlocked: boolean = false;
  private config: Required<AudioPipelineConfig>;

  constructor(config?: AudioPipelineConfig) {
    this.config = {
      sampleRate: config?.sampleRate ?? AUDIO_RATE,
      ringByteOffset: config?.ringByteOffset ?? AUDIO_RING_GUEST_ADDR,
      framesCapacity: config?.framesCapacity ?? AUDIO_RING_FRAMES,
    };
  }

  /**
   * Initializes AudioContext and loads the AudioWorkletProcessor.
   */
  public async init(sharedBuffer: ArrayBufferLike): Promise<void> {
    if (typeof AudioContext === 'undefined') {
      console.warn('[Audio] Web Audio API not supported in this environment');
      return;
    }

    this.ctx = new AudioContext({
      sampleRate: this.config.sampleRate,
      latencyHint: 'interactive',
    });

    this.consumer = new ProStreetAudioConsumer(
      sharedBuffer,
      this.config.ringByteOffset,
      this.config.framesCapacity
    );

    // Register AudioWorkletProcessor via Blob URL
    const blob = new Blob([AUDIO_WORKLET_PROCESSOR_CODE], {
      type: 'application/javascript',
    });
    const workletUrl = URL.createObjectURL(blob);

    try {
      await this.ctx.audioWorklet.addModule(workletUrl);
      this.workletNode = new AudioWorkletNode(this.ctx, 'prostreet-audio-processor', {
        numberOfInputs: 0,
        numberOfOutputs: 1,
        outputChannelCount: [2],
        processorOptions: {
          sharedBuffer,
          byteOffset: this.config.ringByteOffset,
          framesCapacity: this.config.framesCapacity,
        },
      });

      this.workletNode.connect(this.ctx.destination);
    } finally {
      URL.revokeObjectURL(workletUrl);
    }

    this.setupAutoplayUnlock();
  }

  /**
   * Automatically unlocks suspended AudioContext on first user interaction.
   */
  private setupAutoplayUnlock(): void {
    if (!this.ctx) return;

    if (this.ctx.state === 'running') {
      this.isUnlocked = true;
      return;
    }

    const unlock = async () => {
      if (this.ctx && this.ctx.state === 'suspended') {
        try {
          await this.ctx.resume();
          this.isUnlocked = true;
        } catch (e) {
          console.warn('[Audio] Failed to resume AudioContext:', e);
        }
      }
      cleanup();
    };

    const cleanup = () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('pointerdown', unlock);
        window.removeEventListener('keydown', unlock);
        window.removeEventListener('touchstart', unlock);
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('pointerdown', unlock, { once: true, passive: true });
      window.addEventListener('keydown', unlock, { once: true, passive: true });
      window.addEventListener('touchstart', unlock, { once: true, passive: true });
    }
  }

  public async resume(): Promise<void> {
    if (this.ctx && this.ctx.state === 'suspended') {
      await this.ctx.resume();
      this.isUnlocked = true;
    }
  }

  public async suspend(): Promise<void> {
    if (this.ctx && this.ctx.state === 'running') {
      await this.ctx.suspend();
    }
  }

  public async close(): Promise<void> {
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.ctx) {
      await this.ctx.close();
      this.ctx = null;
    }
  }

  public getState(): AudioContextState | 'uninitialized' {
    return this.ctx ? this.ctx.state : 'uninitialized';
  }

  public getSampleRate(): number {
    return this.ctx ? this.ctx.sampleRate : this.config.sampleRate;
  }

  public getConsumer(): ProStreetAudioConsumer | null {
    return this.consumer;
  }

  public isPlaybackUnlocked(): boolean {
    return this.isUnlocked || (this.ctx !== null && this.ctx.state === 'running');
  }
}

