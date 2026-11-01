/**
 * Need for Speed ProStreet - Browser Input Adapter & DirectInput8 Bridge.
 *
 * Bridges browser KeyboardEvent, standard Gamepad API, and Touch overlay inputs
 * to the recompiled WebAssembly engine's 1:1 guest linear memory layout.
 */

export const DINPUT_GUEST_SHARED_STATE = 0x0200A000;

export const VK_BACK    = 0x08;
export const VK_TAB     = 0x09;
export const VK_RETURN  = 0x0D;
export const VK_SHIFT   = 0x10;
export const VK_CONTROL = 0x11;
export const VK_MENU    = 0x12; // Alt
export const VK_PAUSE   = 0x13;
export const VK_CAPITAL = 0x14;
export const VK_ESCAPE  = 0x1B;
export const VK_SPACE   = 0x20;
export const VK_PRIOR   = 0x21; // Page Up
export const VK_NEXT    = 0x22; // Page Down
export const VK_END     = 0x23;
export const VK_HOME    = 0x24;
export const VK_LEFT    = 0x25;
export const VK_UP      = 0x26;
export const VK_RIGHT   = 0x27;
export const VK_DOWN    = 0x28;
export const VK_INSERT  = 0x2D;
export const VK_DELETE  = 0x2E;

export const VK_0 = 0x30;
export const VK_1 = 0x31;
export const VK_2 = 0x32;
export const VK_3 = 0x33;
export const VK_4 = 0x34;
export const VK_5 = 0x35;
export const VK_6 = 0x36;
export const VK_7 = 0x37;
export const VK_8 = 0x38;
export const VK_9 = 0x39;

export const VK_A = 0x41;
export const VK_B = 0x42;
export const VK_C = 0x43;
export const VK_D = 0x44;
export const VK_E = 0x45;
export const VK_F = 0x46;
export const VK_G = 0x47;
export const VK_H = 0x48;
export const VK_I = 0x49;
export const VK_J = 0x4A;
export const VK_K = 0x4B;
export const VK_L = 0x4C;
export const VK_M = 0x4D;
export const VK_N = 0x4E;
export const VK_O = 0x4F;
export const VK_P = 0x50;
export const VK_Q = 0x51;
export const VK_R = 0x52;
export const VK_S = 0x53;
export const VK_T = 0x54;
export const VK_U = 0x55;
export const VK_V = 0x56;
export const VK_W = 0x57;
export const VK_X = 0x58;
export const VK_Y = 0x59;
export const VK_Z = 0x5A;

export const VK_LSHIFT   = 0xA0;
export const VK_RSHIFT   = 0xA1;
export const VK_LCONTROL = 0xA2;
export const VK_RCONTROL = 0xA3;
export const VK_LMENU    = 0xA4;
export const VK_RMENU    = 0xA5;

/** Maps standard browser event codes to Windows Virtual-Key (VK) codes */
export const CODE_TO_VK: Record<string, number> = {
  KeyW: VK_W, KeyS: VK_S, KeyA: VK_A, KeyD: VK_D,
  KeyQ: VK_Q, KeyE: VK_E, KeyR: VK_R, KeyC: VK_C,
  KeyB: VK_B, KeyF: VK_F, KeyM: VK_M, KeyP: VK_P,
  KeyZ: VK_Z, KeyX: VK_X, KeyH: VK_H, KeyT: VK_T,
  KeyY: VK_Y, KeyU: VK_U, KeyI: VK_I, KeyO: VK_O,
  KeyJ: VK_J, KeyK: VK_K, KeyL: VK_L, KeyN: VK_N,
  KeyG: VK_G, KeyV: VK_V,
  ArrowUp: VK_UP, ArrowDown: VK_DOWN, ArrowLeft: VK_LEFT, ArrowRight: VK_RIGHT,
  Space: VK_SPACE, Enter: VK_RETURN, Escape: VK_ESCAPE, Tab: VK_TAB,
  Backspace: VK_BACK, Delete: VK_DELETE, Insert: VK_INSERT,
  ShiftLeft: VK_LSHIFT, ShiftRight: VK_RSHIFT,
  ControlLeft: VK_LCONTROL, ControlRight: VK_RCONTROL,
  AltLeft: VK_LMENU, AltRight: VK_RMENU,
  Digit0: VK_0, Digit1: VK_1, Digit2: VK_2, Digit3: VK_3, Digit4: VK_4,
  Digit5: VK_5, Digit6: VK_6, Digit7: VK_7, Digit8: VK_8, Digit9: VK_9,
};

export interface DIJoyState2State {
  lX: number;
  lY: number;
  lZ: number;
  lRx: number;
  lRy: number;
  lRz: number;
  rglSlider: [number, number];
  rgdwPOV: [number, number, number, number];
  rgbButtons: Uint8Array;
}

export interface DInputSharedState {
  sequence: number;
  connected: number;
  deviceType: number;
  joystate: DIJoyState2State;
  keyboard: Uint8Array;
}

export class BrowserInputAdapter {
  private buffer: ArrayBuffer | SharedArrayBuffer;
  private offset: number;
  private dataView: DataView;
  private uint8View: Uint8Array;
  private state: DInputSharedState;
  private onWin32KeyCallback?: (vk: number, down: boolean) => void;
  private keyboardCleanup?: () => void;
  private gamepadPollInterval?: any;

  constructor(buffer: ArrayBuffer | SharedArrayBuffer, offset = DINPUT_GUEST_SHARED_STATE) {
    this.buffer = buffer;
    this.offset = offset;
    this.dataView = new DataView(this.buffer, this.offset);
    this.uint8View = new Uint8Array(this.buffer, this.offset);

    this.state = {
      sequence: 1,
      connected: 1,
      deviceType: 0x15, // DI8DEVTYPE_GAMEPAD
      joystate: {
        lX: 0, lY: 0, lZ: 0,
        lRx: 0, lRy: 0, lRz: 0,
        rglSlider: [0, 0],
        rgdwPOV: [0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF],
        rgbButtons: new Uint8Array(128),
      },
      keyboard: new Uint8Array(256),
    };

    this.syncToMemory();
  }

  public setWin32KeyCallback(cb: (vk: number, down: boolean) => void): void {
    this.onWin32KeyCallback = cb;
  }

  public setDeviceType(devType: number): void {
    this.state.deviceType = devType;
    this.state.sequence++;
    this.syncToMemory();
  }

  public setConnected(connected: boolean): void {
    this.state.connected = connected ? 1 : 0;
    this.state.sequence++;
    this.syncToMemory();
  }

  public setAxes(steerLx: number, throttleRz: number, brakeLz: number): void {
    this.state.joystate.lX  = Math.max(-32768, Math.min(32767, Math.round(steerLx)));
    this.state.joystate.lRz = Math.max(-32768, Math.min(32767, Math.round(throttleRz)));
    this.state.joystate.lZ  = Math.max(-32768, Math.min(32767, Math.round(brakeLz)));
    this.state.sequence++;
    this.syncToMemory();
  }

  public setButton(buttonIdx: number, pressed: boolean): void {
    if (buttonIdx >= 0 && buttonIdx < 128) {
      this.state.joystate.rgbButtons[buttonIdx] = pressed ? 0x80 : 0x00;
      this.state.sequence++;
      this.syncToMemory();
    }
  }

  public setPov(hatIdx: number, povDegreesHundredths: number): void {
    if (hatIdx >= 0 && hatIdx < 4) {
      this.state.joystate.rgdwPOV[hatIdx] = povDegreesHundredths >>> 0;
      this.state.sequence++;
      this.syncToMemory();
    }
  }

  public setKey(vk: number, pressed: boolean): void {
    if (vk >= 0 && vk < 256) {
      this.state.keyboard[vk] = pressed ? 0x80 : 0x00;
      this.state.sequence++;
      this.syncToMemory();
      if (this.onWin32KeyCallback) {
        this.onWin32KeyCallback(vk, pressed);
      }
    }
  }

  /** Syncs internal state into the memory buffer at this.offset */
  public syncToMemory(): void {
    // 0x00: sequence, connected, deviceType (12 bytes)
    this.dataView.setUint32(0, this.state.sequence, true);
    this.dataView.setInt32(4, this.state.connected, true);
    this.dataView.setInt32(8, this.state.deviceType, true);

    // 0x0C: DIJOYSTATE2 (272 bytes)
    const joyOffset = 12;
    this.dataView.setInt32(joyOffset + 0, this.state.joystate.lX, true);
    this.dataView.setInt32(joyOffset + 4, this.state.joystate.lY, true);
    this.dataView.setInt32(joyOffset + 8, this.state.joystate.lZ, true);
    this.dataView.setInt32(joyOffset + 12, this.state.joystate.lRx, true);
    this.dataView.setInt32(joyOffset + 16, this.state.joystate.lRy, true);
    this.dataView.setInt32(joyOffset + 20, this.state.joystate.lRz, true);
    this.dataView.setInt32(joyOffset + 24, this.state.joystate.rglSlider[0], true);
    this.dataView.setInt32(joyOffset + 28, this.state.joystate.rglSlider[1], true);

    this.dataView.setUint32(joyOffset + 32, this.state.joystate.rgdwPOV[0], true);
    this.dataView.setUint32(joyOffset + 36, this.state.joystate.rgdwPOV[1], true);
    this.dataView.setUint32(joyOffset + 40, this.state.joystate.rgdwPOV[2], true);
    this.dataView.setUint32(joyOffset + 44, this.state.joystate.rgdwPOV[3], true);

    // rgbButtons at joyOffset + 48 (128 bytes)
    this.uint8View.set(this.state.joystate.rgbButtons, joyOffset + 48);

    // Keyboard at joyOffset + 272 (256 bytes)
    this.uint8View.set(this.state.keyboard, joyOffset + 272);
  }

  /** Polls standard HTML5 Gamepad API and applies to DIJOYSTATE2 */
  public pollGamepad(): void {
    if (typeof navigator === 'undefined' || typeof navigator.getGamepads !== 'function') {
      return;
    }
    const gamepads = navigator.getGamepads();
    let pad: Gamepad | null = null;
    for (const g of gamepads) {
      if (g && g.connected) { pad = g; break; }
    }
    if (!pad) return;

    // Steering: left stick X (axis 0)
    const rawSteer = pad.axes[0] ?? 0;
    const steerLx = Math.round(rawSteer * 32767);

    // Triggers: Left Trigger (button 6) = Brake, Right Trigger (button 7) = Throttle
    const rawBrake = typeof pad.buttons[6] === 'object' ? pad.buttons[6].value : (pad.buttons[6] ? 1 : 0);
    const rawThrottle = typeof pad.buttons[7] === 'object' ? pad.buttons[7].value : (pad.buttons[7] ? 1 : 0);

    const brakeLz = Math.round(rawBrake * 32767);
    const throttleRz = Math.round(rawThrottle * 32767);

    this.setAxes(steerLx, throttleRz, brakeLz);

    // Digital Buttons
    for (let i = 0; i < Math.min(16, pad.buttons.length); ++i) {
      const btn = pad.buttons[i];
      const isPressed = typeof btn === 'object' ? btn.pressed : Boolean(btn);
      this.setButton(i, isPressed);
    }

    // D-pad hat (buttons 12=Up, 13=Down, 14=Left, 15=Right)
    const up = pad.buttons[12]?.pressed ?? false;
    const down = pad.buttons[13]?.pressed ?? false;
    const left = pad.buttons[14]?.pressed ?? false;
    const right = pad.buttons[15]?.pressed ?? false;

    if (up && right) this.setPov(0, 4500);
    else if (down && right) this.setPov(0, 13500);
    else if (down && left) this.setPov(0, 22500);
    else if (up && left) this.setPov(0, 31500);
    else if (up) this.setPov(0, 0);
    else if (right) this.setPov(0, 9000);
    else if (down) this.setPov(0, 18000);
    else if (left) this.setPov(0, 27000);
    else this.setPov(0, 0xFFFFFFFF);
  }

  /** Attaches document-level keyboard event listeners */
  public attachKeyboardListeners(target: EventTarget = window): () => void {
    const onKeyDown = (e: Event) => {
      const ke = e as KeyboardEvent;
      const vk = CODE_TO_VK[ke.code];
      if (vk !== undefined) {
        this.setKey(vk, true);
        // Also map to gamepad digital inputs for unified control
        if (ke.code === 'ArrowUp' || ke.code === 'KeyW') this.setAxes(this.state.joystate.lX, 32767, this.state.joystate.lZ);
        if (ke.code === 'ArrowDown' || ke.code === 'KeyS') this.setAxes(this.state.joystate.lX, this.state.joystate.lRz, 32767);
        if (ke.code === 'ArrowLeft' || ke.code === 'KeyA') this.setAxes(-32768, this.state.joystate.lRz, this.state.joystate.lZ);
        if (ke.code === 'ArrowRight' || ke.code === 'KeyD') this.setAxes(32767, this.state.joystate.lRz, this.state.joystate.lZ);
        if (ke.code === 'Space') this.setButton(5, true); // Handbrake (RB)
        if (ke.code === 'ShiftLeft') this.setButton(4, true); // Nitro (LB)
      }
    };

    const onKeyUp = (e: Event) => {
      const ke = e as KeyboardEvent;
      const vk = CODE_TO_VK[ke.code];
      if (vk !== undefined) {
        this.setKey(vk, false);
        if (ke.code === 'ArrowUp' || ke.code === 'KeyW') this.setAxes(this.state.joystate.lX, 0, this.state.joystate.lZ);
        if (ke.code === 'ArrowDown' || ke.code === 'KeyS') this.setAxes(this.state.joystate.lX, this.state.joystate.lRz, 0);
        if (ke.code === 'ArrowLeft' || ke.code === 'KeyA') this.setAxes(0, this.state.joystate.lRz, this.state.joystate.lZ);
        if (ke.code === 'ArrowRight' || ke.code === 'KeyD') this.setAxes(0, this.state.joystate.lRz, this.state.joystate.lZ);
        if (ke.code === 'Space') this.setButton(5, false);
        if (ke.code === 'ShiftLeft') this.setButton(4, false);
      }
    };

    target.addEventListener('keydown', onKeyDown);
    target.addEventListener('keyup', onKeyUp);

    return () => {
      target.removeEventListener('keydown', onKeyDown);
      target.removeEventListener('keyup', onKeyUp);
    };
  }

  public attachKeyboard(target: EventTarget = window): void {
    this.detachKeyboard();
    this.keyboardCleanup = this.attachKeyboardListeners(target);
  }

  public detachKeyboard(): void {
    if (this.keyboardCleanup) {
      this.keyboardCleanup();
      this.keyboardCleanup = undefined;
    }
  }

  public startGamepadPolling(intervalMs = 16): void {
    this.stopGamepadPolling();
    this.gamepadPollInterval = setInterval(() => this.pollGamepad(), intervalMs);
  }

  public stopGamepadPolling(): void {
    if (this.gamepadPollInterval) {
      clearInterval(this.gamepadPollInterval);
      this.gamepadPollInterval = undefined;
    }
  }

  public getState(): DInputSharedState {
    return this.state;
  }
}

