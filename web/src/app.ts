/**
 * Need for Speed ProStreet - Web Application Shell.
 *
 * Coordinates WebGL2 / WebGPU graphics renderer, Web Audio pipeline,
 * DirectInput/Gamepad/Touch input, OPFS asset streaming, and user settings.
 */

import { BrowserAudioPipeline } from './audio.js';
import { BrowserInputAdapter, DINPUT_GUEST_SHARED_STATE } from './input.js';
import { TouchOverlay, SteeringMode } from './touch.js';
import { D3D9CommandConsumer, D3D9CommandProducer } from './d3d9_consumer.js';
import { AssetIOEngine } from './io_worker.js';
import { VirtualFileSystem } from './vfs.js';
import { ClientVehicleSim } from './sim.js';
import { loadProStreetModule, LoadedEngine } from './wasm_loader.js';

export type AppState = 'idle' | 'loading' | 'running' | 'paused' | 'error';
export type ResolutionScale = 1.0 | 0.75 | 0.5;

export interface AppSettings {
  resolutionScale: ResolutionScale;
  fpsTarget: 60 | 120;
  audioVolume: number; // 0..100
  steeringMode: SteeringMode;
  levelHorizon: boolean;
  touchControlScale: number; // 0.8 .. 1.4
}

export const DEFAULT_SETTINGS: AppSettings = {
  resolutionScale: 1.0,
  fpsTarget: 60,
  audioVolume: 85,
  steeringMode: 'buttons',
  levelHorizon: true,
  touchControlScale: 1.0,
};

const SETTINGS_KEY = 'prostreet-web-settings';

export class AppShell {
  public state: AppState = 'idle';
  public settings: AppSettings = { ...DEFAULT_SETTINGS };

  public canvas: HTMLCanvasElement | null = null;
  public audio: BrowserAudioPipeline | null = null;
  public input: BrowserInputAdapter | null = null;
  public touch: TouchOverlay | null = null;
  public d3d9: D3D9CommandConsumer | null = null;
  public ioEngine: AssetIOEngine | null = null;
  public vfs: VirtualFileSystem | null = null;
  public sim: ClientVehicleSim = new ClientVehicleSim();
  public loadedEngine: LoadedEngine | null = null;

  public activeTab: string = 'play';
  public isRunning: boolean = false;
  private animationFrameId: number | null = null;
  private sharedMemory: ArrayBuffer | null = null;

  constructor() {
    this.loadSettings();
  }

  /**
   * Loads persisted settings from localStorage.
   */
  public loadSettings(): void {
    try {
      if (typeof localStorage !== 'undefined') {
        const saved = localStorage.getItem(SETTINGS_KEY);
        if (saved) {
          this.settings = { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
        }
      }
    } catch (_) {
      this.settings = { ...DEFAULT_SETTINGS };
    }
  }

  /**
   * Persists current settings to localStorage.
   */
  public saveSettings(): void {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(this.settings));
      }
    } catch (_) {}
  }

  /**
   * Initializes shared subsystems with WebAssembly linear memory buffer.
   */
  public async initSubsystems(
    canvas: HTMLCanvasElement,
    wasmMemory: ArrayBufferLike,
    touchContainer?: HTMLElement
  ): Promise<void> {
    this.canvas = canvas;
    this.sharedMemory = wasmMemory as ArrayBuffer;

    // 1. D3D9 WebGL2 renderer & ring buffer auto-initialization
    const gl = canvas.getContext('webgl2');
    try {
      D3D9CommandProducer.initRing(wasmMemory as ArrayBuffer, 0x02010000);
    } catch (_) {}
    this.d3d9 = new D3D9CommandConsumer(wasmMemory as ArrayBuffer, 0x02010000, { gl });

    // 2. AudioWorklet pipeline
    this.audio = new BrowserAudioPipeline();
    await this.audio.init(wasmMemory);

    // 3. DirectInput & touch controls
    this.input = new BrowserInputAdapter(wasmMemory as ArrayBuffer, DINPUT_GUEST_SHARED_STATE);
    this.input.attachKeyboard();
    this.input.startGamepadPolling();

    if (touchContainer) {
      this.touch = new TouchOverlay(this.input, touchContainer);
    }

    // 4. OPFS asset streamer & VFS
    this.ioEngine = new AssetIOEngine('/data/');
    await this.ioEngine.initOPFS();
    this.vfs = new VirtualFileSystem(this.ioEngine);

    this.applyResolutionScale(this.settings.resolutionScale);
    this.state = 'idle';
  }

  /**
   * Switches active UI tab panel.
   */
  public setTab(tabName: string): void {
    this.activeTab = tabName;
  }

  /**
   * Adjusts canvas render resolution scaling.
   */
  public applyResolutionScale(scale: ResolutionScale): void {
    this.settings.resolutionScale = scale;
    const baseWidth = 1280;
    const baseHeight = 720;
    if (this.canvas) {
      this.canvas.width = Math.round(baseWidth * scale);
      this.canvas.height = Math.round(baseHeight * scale);
    }
    this.saveSettings();
  }

  /**
   * Toggles native browser fullscreen.
   */
  public async toggleFullscreen(targetElement?: HTMLElement): Promise<boolean> {
    const el = targetElement || this.canvas?.parentElement || document.documentElement;
    if (!document.fullscreenElement) {
      try {
        await el.requestFullscreen();
        return true;
      } catch (e) {
        console.warn('[Shell] Fullscreen request denied:', e);
        return false;
      }
    } else {
      try {
        await document.exitFullscreen();
        return false;
      } catch (e) {
        return false;
      }
    }
  }

  /**
   * Preloads critical game assets into OPFS cache with progress reporting.
   */
  public async preloadGameData(
    onProgress?: (percent: number, loadedBytes: number, totalBytes: number) => void
  ): Promise<void> {
    if (!this.ioEngine) return;

    this.state = 'loading';
    const criticalAssets = [
      'GLOBAL/GLOBALB.LZC',
      'GLOBAL/LOADINGTEXTURES.BUN',
      'CARS/240SX/GEOMETRY.BIN',
      'CARS/240SX/TEXTURES.BIN',
    ];

    try {
      await this.ioEngine.preloadFiles(criticalAssets, (p) => {
        if (onProgress) {
          onProgress(p.percent, p.bytesLoaded, p.bytesTotal);
        }
      });
      this.state = 'idle';
    } catch (e) {
      this.state = 'error';
      throw e;
    }
  }

  /**
   * Starts live in-game race loop (WASM execution, D3D9 rendering, audio, input, physics).
   */
  public async startRace(touchContainer?: HTMLElement): Promise<void> {
    if (this.isRunning) return;

    // 1. Load WebAssembly engine module if not already loaded
    if (!this.loadedEngine) {
      this.state = 'loading';
      this.loadedEngine = await loadProStreetModule('/prostreet.wasm', '/prostreet.json');
    }

    // 2. Initialize subsystems if not already initialized
    if (!this.d3d9 && this.canvas) {
      await this.initSubsystems(this.canvas, this.loadedEngine.memory.buffer, touchContainer);
    }

    // 2b. Load authentic PE image sections from server if available
    try {
      const resp = await fetch('/data/nfs.exe');
      if (resp.ok) {
        const exeBuf = await resp.arrayBuffer();
        const peBytes = new Uint8Array(exeBuf);
        const stagingVa = 0x1f000000;
        const memU8 = new Uint8Array(this.loadedEngine.memory.buffer);
        memU8.set(peBytes, stagingVa);
        if (this.loadedEngine.exports.prostreet_load_pe) {
          const rc = this.loadedEngine.exports.prostreet_load_pe(stagingVa, peBytes.length);
          console.log('[Engine] prostreet_load_pe result:', rc);
        }
      }
    } catch (e) {
      console.warn('[Engine] nfs.exe load skipped or unavailable:', e);
    }

    // 3. Ensure asset manifest is loaded into IO engine
    if (this.ioEngine && !this.ioEngine.getManifestEntry('GLOBAL/GLOBALB.LZC')) {
      try {
        const resp = await fetch('/data-manifest.json');
        if (resp.ok) {
          const manifest = await resp.json();
          this.ioEngine.setManifest(manifest);
        }
      } catch (_) {}
    }

    // 4. Resume Web Audio pipeline
    if (this.audio) {
      await this.audio.resume();
    }

    // 5. Invoke guest main entrypoint if exported
    if (this.loadedEngine.exports.prostreet_main) {
      try {
        this.loadedEngine.exports.prostreet_main(0, 0);
      } catch (e) {
        console.warn('[Engine] main exited or running asynchronously:', e);
      }
    }

    // 6. Start 60 FPS animation frame loop
    this.isRunning = true;
    this.state = 'running';
    let lastTime = performance.now();

    const frameLoop = () => {
      if (!this.isRunning) return;

      const now = performance.now();
      const dt = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;

      // 1. Poll input and feed vehicle dynamics
      if (this.input) {
        this.input.pollGamepad();
        const state = this.input.getState();
        this.sim.steering = state.joystate.lX / 32767;
        this.sim.throttle = Math.max(0, state.joystate.lRz / 32767);
        this.sim.brake = Math.max(0, state.joystate.lZ / 32767);
        this.sim.handbrake = state.joystate.rgbButtons[5] ? 1 : 0;
        this.sim.nitrous = state.joystate.rgbButtons[4] ? 1 : 0;
      }

      // 2. Step vehicle physics simulation
      this.sim.step(dt);

      // 3. Process D3D9 command ring buffer & dispatch WebGL2 draws from authentic engine
      if (this.d3d9) {
        try {
          this.d3d9.processCommands();
        } catch (err) {
          // Keep loop running if ring buffer has unhandled command
        }
      }

      // 4. Tick WebAssembly guest engine
      if (this.loadedEngine?.exports.prostreet_tick) {
        try {
          this.loadedEngine.exports.prostreet_tick();
        } catch (_) {}
      }

      if (typeof requestAnimationFrame !== 'undefined') {
        this.animationFrameId = requestAnimationFrame(frameLoop);
      }
    };

    if (typeof requestAnimationFrame !== 'undefined') {
      this.animationFrameId = requestAnimationFrame(frameLoop);
    }
  }

  /**
   * Pauses the live race loop.
   */
  public stopRace(): void {
    this.isRunning = false;
    if (this.animationFrameId !== null && typeof cancelAnimationFrame !== 'undefined') {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    this.state = 'paused';
  }

  /**
   * Tears down and cleans up resources on exit.
   */
  public async dispose(): Promise<void> {
    this.stopRace();
    if (this.input) {
      this.input.stopGamepadPolling();
      this.input.detachKeyboard();
    }
    if (this.audio) {
      await this.audio.close();
    }
    if (this.d3d9) {
      this.d3d9.dispose();
    }
    this.state = 'idle';
  }
}

