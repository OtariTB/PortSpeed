import test from 'node:test';
import assert from 'node:assert/strict';
import { AppShell, DEFAULT_SETTINGS } from '../src/app.js';

test('AppShell initializes with default settings and idle state', () => {
  const shell = new AppShell();
  assert.equal(shell.state, 'idle');
  assert.equal(shell.activeTab, 'play');
  assert.equal(shell.settings.resolutionScale, 1.0);
  assert.equal(shell.settings.fpsTarget, 60);
  assert.equal(shell.settings.audioVolume, 85);
  assert.equal(shell.settings.steeringMode, 'buttons');
});

test('AppShell switches UI tabs correctly', () => {
  const shell = new AppShell();
  assert.equal(shell.activeTab, 'play');

  shell.setTab('controls');
  assert.equal(shell.activeTab, 'controls');

  shell.setTab('settings');
  assert.equal(shell.activeTab, 'settings');

  shell.setTab('gamedata');
  assert.equal(shell.activeTab, 'gamedata');
});

test('AppShell applies resolution scaling to canvas dimensions', () => {
  const shell = new AppShell();

  // Mock canvas object
  const mockCanvas = {
    width: 0,
    height: 0,
  } as HTMLCanvasElement;
  shell.canvas = mockCanvas;

  // 100% scale (1280x720)
  shell.applyResolutionScale(1.0);
  assert.equal(shell.canvas.width, 1280);
  assert.equal(shell.canvas.height, 720);
  assert.equal(shell.settings.resolutionScale, 1.0);

  // 75% scale (960x540)
  shell.applyResolutionScale(0.75);
  assert.equal(shell.canvas.width, 960);
  assert.equal(shell.canvas.height, 540);
  assert.equal(shell.settings.resolutionScale, 0.75);

  // 50% scale (640x360)
  shell.applyResolutionScale(0.5);
  assert.equal(shell.canvas.width, 640);
  assert.equal(shell.canvas.height, 360);
  assert.equal(shell.settings.resolutionScale, 0.5);
});

test('AppShell manages settings persistence', () => {
  const fakeStore: Record<string, string> = {};
  const mockLocalStorage = {
    getItem: (k: string) => fakeStore[k] || null,
    setItem: (k: string, v: string) => { fakeStore[k] = v; },
    removeItem: (k: string) => { delete fakeStore[k]; },
    clear: () => { for (const k in fakeStore) delete fakeStore[k]; },
  };

  (globalThis as any).localStorage = mockLocalStorage;

  const shell = new AppShell();
  shell.settings.audioVolume = 50;
  shell.settings.steeringMode = 'stick';
  shell.saveSettings();

  assert.ok(fakeStore['prostreet-web-settings']);

  // Load into new instance
  const shell2 = new AppShell();
  assert.equal(shell2.settings.audioVolume, 50);
  assert.equal(shell2.settings.steeringMode, 'stick');
});

test('AppShell manages startRace and stopRace simulation loop', async () => {
  const shell = new AppShell();

  // Mock loaded engine
  const mockMemory = new WebAssembly.Memory({ initial: 2, maximum: 4 });
  let tickCount = 0;
  shell.loadedEngine = {
    instance: {} as any,
    module: {} as any,
    memory: mockMemory,
    manifest: {
      pages: 2,
      maxPages: 4,
      guestEnd: 65536,
      size: 100,
      opt: '-O3',
      toolchain: 'test',
      shards: 32,
      functions: 31995,
      compiledAt: '',
    },
    exports: {
      memory: mockMemory,
      prostreet_main: () => 0,
      prostreet_tick: () => { tickCount++; return 0; },
    },
  };

  await shell.startRace();
  assert.equal(shell.isRunning, true);
  assert.equal(shell.state, 'running');

  // Verify simulation properties
  assert.ok(shell.sim);
  assert.equal(shell.sim.gear, 1);

  // Stop race
  shell.stopRace();
  assert.equal(shell.isRunning, false);
  assert.equal(shell.state, 'paused');

  // Clean disposal
  await shell.dispose();
  assert.equal(shell.state, 'idle');
});


