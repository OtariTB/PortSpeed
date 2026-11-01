import test from 'node:test';
import assert from 'node:assert/strict';
import {
  BrowserInputAdapter,
  DINPUT_GUEST_SHARED_STATE,
  VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT, VK_SPACE, VK_LSHIFT, VK_W, VK_S
} from '../src/input.js';

test('BrowserInputAdapter initializes shared memory state correctly', () => {
  const mem = new ArrayBuffer(0x28000000);
  const adapter = new BrowserInputAdapter(mem, DINPUT_GUEST_SHARED_STATE);

  const view = new DataView(mem, DINPUT_GUEST_SHARED_STATE);
  assert.equal(view.getUint32(0, true), 1); // sequence
  assert.equal(view.getInt32(4, true), 1);  // connected
  assert.equal(view.getInt32(8, true), 0x15); // deviceType (DI8DEVTYPE_GAMEPAD)

  // DIJOYSTATE2 centered
  const joyOffset = 12;
  assert.equal(view.getInt32(joyOffset + 0, true), 0); // lX
  assert.equal(view.getInt32(joyOffset + 8, true), 0); // lZ
  assert.equal(view.getInt32(joyOffset + 20, true), 0); // lRz
  assert.equal(view.getUint32(joyOffset + 32, true), 0xFFFFFFFF); // POV 0
});

test('BrowserInputAdapter packs analog axes and triggers into DIJOYSTATE2', () => {
  const mem = new ArrayBuffer(0x28000000);
  const adapter = new BrowserInputAdapter(mem, DINPUT_GUEST_SHARED_STATE);

  // Steer full left (-32768), throttle 100% (32767), brake 50% (16384)
  adapter.setAxes(-32768, 32767, 16384);

  const view = new DataView(mem, DINPUT_GUEST_SHARED_STATE);
  assert.equal(view.getUint32(0, true), 2); // sequence incremented
  const joyOffset = 12;
  assert.equal(view.getInt32(joyOffset + 0, true), -32768); // lX
  assert.equal(view.getInt32(joyOffset + 8, true), 16384);  // lZ
  assert.equal(view.getInt32(joyOffset + 20, true), 32767); // lRz
});

test('BrowserInputAdapter handles button clicks and POV directions', () => {
  const mem = new ArrayBuffer(0x28000000);
  const adapter = new BrowserInputAdapter(mem, DINPUT_GUEST_SHARED_STATE);

  adapter.setButton(0, true);  // Button 0 (A)
  adapter.setButton(4, true);  // Button 4 (LB / NOS)
  adapter.setPov(0, 9000);     // Right POV hat

  const view = new DataView(mem, DINPUT_GUEST_SHARED_STATE);
  const uint8 = new Uint8Array(mem, DINPUT_GUEST_SHARED_STATE);
  const joyOffset = 12;

  assert.equal(uint8[joyOffset + 48 + 0], 0x80); // Button 0 pressed
  assert.equal(uint8[joyOffset + 48 + 4], 0x80); // Button 4 pressed
  assert.equal(uint8[joyOffset + 48 + 1], 0x00); // Button 1 released
  assert.equal(view.getUint32(joyOffset + 32, true), 9000);

  // Release button
  adapter.setButton(0, false);
  assert.equal(uint8[joyOffset + 48 + 0], 0x00);
});

test('BrowserInputAdapter updates virtual keyboard state and fires Win32 callback', () => {
  const mem = new ArrayBuffer(0x28000000);
  const adapter = new BrowserInputAdapter(mem, DINPUT_GUEST_SHARED_STATE);

  const fired: { vk: number; down: boolean }[] = [];
  adapter.setWin32KeyCallback((vk, down) => {
    fired.push({ vk, down });
  });

  adapter.setKey(VK_SPACE, true);
  adapter.setKey(VK_UP, true);
  adapter.setKey(VK_SPACE, false);

  const uint8 = new Uint8Array(mem, DINPUT_GUEST_SHARED_STATE);
  const kbdOffset = 12 + 272;

  assert.equal(uint8[kbdOffset + VK_UP], 0x80);
  assert.equal(uint8[kbdOffset + VK_SPACE], 0x00);

  assert.deepEqual(fired, [
    { vk: VK_SPACE, down: true },
    { vk: VK_UP, down: true },
    { vk: VK_SPACE, down: false },
  ]);
});

test('BrowserInputAdapter polls simulated HTML5 Gamepad API', () => {
  const mem = new ArrayBuffer(0x28000000);
  const adapter = new BrowserInputAdapter(mem, DINPUT_GUEST_SHARED_STATE);

  // Mock global navigator.getGamepads
  const fakeGamepad = {
    connected: true,
    axes: [0.75, 0], // steer right 75%
    buttons: [
      { pressed: true, value: 1.0 },  // 0: A
      { pressed: false, value: 0.0 }, // 1: B
      { pressed: false, value: 0.0 }, // 2: X
      { pressed: false, value: 0.0 }, // 3: Y
      { pressed: false, value: 0.0 }, // 4: LB
      { pressed: true, value: 1.0 },  // 5: RB
      { pressed: false, value: 0.5 }, // 6: LT (Brake 50%)
      { pressed: true, value: 1.0 },  // 7: RT (Throttle 100%)
      { pressed: false, value: 0 },
      { pressed: false, value: 0 },
      { pressed: false, value: 0 },
      { pressed: false, value: 0 },
      { pressed: true, value: 1.0 },  // 12: D-pad Up
      { pressed: false, value: 0 },   // 13: Down
      { pressed: false, value: 0 },   // 14: Left
      { pressed: false, value: 0 },   // 15: Right
    ],
  };

  if (!('navigator' in globalThis) || !globalThis.navigator) {
    Object.defineProperty(globalThis, 'navigator', {
      value: { getGamepads: () => [fakeGamepad] },
      configurable: true,
      writable: true,
    });
  } else {
    Object.defineProperty(globalThis.navigator, 'getGamepads', {
      value: () => [fakeGamepad],
      configurable: true,
      writable: true,
    });
  }

  adapter.pollGamepad();

  const state = adapter.getState();
  assert.equal(Math.round(state.joystate.lX / 32767 * 100), 75);
  assert.equal(state.joystate.lRz, 32767); // Throttle
  assert.equal(state.joystate.lZ, Math.round(0.5 * 32767)); // Brake
  assert.equal(state.joystate.rgbButtons[0], 0x80);
  assert.equal(state.joystate.rgbButtons[5], 0x80);
  assert.equal(state.joystate.rgdwPOV[0], 0); // POV Up
});

