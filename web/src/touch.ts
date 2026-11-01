/**
 * Need for Speed ProStreet - Mobile Touch Controls Overlay.
 *
 * Implements mobile and tablet touch controls matching our proven NFSU1 touch overlay:
 *   - Steering: Buttons (ArrowLeft / ArrowRight), Virtual Thumbstick, or Gyroscope Tilt (DeviceOrientation)
 *   - Pedals: Gas (Throttle), Brake / Reverse, Nitrous (NOS with slide-up from Gas), Handbrake
 *   - Gears: Manual Gear Up ('E') and Gear Down ('Q') above the left thumb
 *   - Top Bar: Pause (Esc), Camera ('C'), Look Back ('B'), Reset Car ('R'), Steering mode cycle, Tilt recenter
 *   - Menu: Virtual D-pad, OK (Enter), Back (Esc)
 *   - Utilities: WakeLock (keep screen active), multi-touch gesture prevention (noPinchZoom)
 */

import { BrowserInputAdapter, VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT, VK_SPACE, VK_RETURN, VK_ESCAPE, VK_C, VK_B, VK_R, VK_E, VK_Q, VK_LSHIFT } from './input';

export type SteeringMode = 'buttons' | 'stick' | 'tilt';
export const STEERING_MODES: readonly SteeringMode[] = ['buttons', 'stick', 'tilt'];
const STORE_STEERING = 'prostreet-touch-steering';

export function isTouchScreen(): boolean {
  if (typeof window === 'undefined') return false;
  const hasCoarsePointer = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches;
  const hasTouchPoints = typeof navigator !== 'undefined' && ((navigator.maxTouchPoints || 0) > 0 || ((navigator as any).msMaxTouchPoints || 0) > 0);
  const hasTouchEvents = 'ontouchstart' in window;
  return (hasCoarsePointer || (hasTouchPoints && hasTouchEvents));
}

export class TouchOverlay {
  private adapter: BrowserInputAdapter;
  private container: HTMLElement;
  private steeringMode: SteeringMode = 'buttons';
  private tiltOffset = 0;
  private tiltActive = false;
  private cleanups: (() => void)[] = [];
  private gasPressed = false;
  private brakePressed = false;
  private steerLeftPressed = false;
  private steerRightPressed = false;
  private wakeLockRelease?: () => void;

  constructor(adapter: BrowserInputAdapter, container: HTMLElement = document.body) {
    this.adapter = adapter;
    this.container = container;

    // Desktop check: If running on a desktop PC with a mouse, hide touch controls entirely
    if (!isTouchScreen()) {
      if (this.container) {
        this.container.style.display = 'none';
      }
      return;
    }

    try {
      const saved = localStorage.getItem(STORE_STEERING) as SteeringMode;
      if (saved && STEERING_MODES.includes(saved)) {
        this.steeringMode = saved;
      }
    } catch {
      this.steeringMode = 'buttons';
    }

    this.initDOM();
    this.initDeviceOrientation();
    this.preventPinchZoom();
    this.acquireWakeLock();
  }

  public setSteeringMode(mode: SteeringMode): void {
    if (this.steeringMode !== mode && STEERING_MODES.includes(mode)) {
      this.steeringMode = mode;
      try {
        localStorage.setItem(STORE_STEERING, mode);
      } catch {}
      this.updateSteeringUI();
    }
  }

  public getSteeringMode(): SteeringMode {
    return this.steeringMode;
  }

  public recenterTilt(): void {
    this.tiltOffset = 0;
  }

  private initDOM(): void {
    const root = document.createElement('div');
    root.className = 'prostreet-touch-overlay';
    root.id = 'prostreet-touch-overlay';

    root.innerHTML = `
      <style>
        .prostreet-touch-overlay {
          position: absolute;
          inset: 0;
          pointer-events: none;
          z-index: 1000;
          user-select: none;
          -webkit-user-select: none;
          touch-action: none;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .touch-btn {
          position: absolute;
          pointer-events: auto;
          background: rgba(20, 20, 25, 0.65);
          border: 2px solid rgba(255, 255, 255, 0.35);
          border-radius: 50%;
          color: white;
          font-weight: bold;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px rgba(0,0,0,0.4);
          transition: transform 0.05s, background-color 0.05s;
        }
        .touch-btn:active, .touch-btn.active {
          background: rgba(255, 165, 0, 0.75);
          border-color: #FFA500;
          transform: scale(0.95);
        }
        /* Top Navigation Bar */
        .touch-top-bar {
          position: absolute;
          top: 10px;
          left: 10px;
          right: 10px;
          display: flex;
          justify-content: space-between;
          pointer-events: none;
        }
        .touch-top-bar .touch-btn {
          position: static;
          width: 44px;
          height: 44px;
          font-size: 13px;
          border-radius: 12px;
        }
        /* Left Controls (Steering / Gears) */
        .touch-left-cluster {
          position: absolute;
          bottom: 24px;
          left: 20px;
          width: 180px;
          height: 180px;
          pointer-events: none;
        }
        .btn-steer-left {
          left: 0;
          bottom: 40px;
          width: 74px;
          height: 74px;
          font-size: 26px;
        }
        .btn-steer-right {
          left: 90px;
          bottom: 40px;
          width: 74px;
          height: 74px;
          font-size: 26px;
        }
        .btn-gear-down {
          left: 10px;
          bottom: 125px;
          width: 52px;
          height: 52px;
          font-size: 12px;
          border-radius: 14px;
          background: rgba(40, 40, 50, 0.7);
        }
        .btn-gear-up {
          left: 80px;
          bottom: 125px;
          width: 52px;
          height: 52px;
          font-size: 12px;
          border-radius: 14px;
          background: rgba(40, 40, 50, 0.7);
        }
        /* Right Controls (Pedals / Handbrake / Nitrous) */
        .touch-right-cluster {
          position: absolute;
          bottom: 24px;
          right: 20px;
          width: 200px;
          height: 220px;
          pointer-events: none;
        }
        .btn-gas {
          right: 0;
          bottom: 70px;
          width: 82px;
          height: 110px;
          border-radius: 28px;
          font-size: 18px;
          background: rgba(40, 160, 60, 0.65);
        }
        .btn-gas.active {
          background: rgba(50, 220, 80, 0.85);
          border-color: #32DC50;
        }
        .btn-brake {
          right: 95px;
          bottom: 50px;
          width: 74px;
          height: 85px;
          border-radius: 24px;
          font-size: 16px;
          background: rgba(200, 40, 40, 0.65);
        }
        .btn-brake.active {
          background: rgba(255, 60, 60, 0.85);
          border-color: #FF3C3C;
        }
        .btn-nos {
          right: 15px;
          bottom: 195px;
          width: 55px;
          height: 55px;
          font-size: 13px;
          background: rgba(30, 120, 240, 0.65);
          border-color: #38A0FF;
        }
        .btn-nos.active {
          background: rgba(50, 160, 255, 0.85);
        }
        .btn-handbrake {
          right: 90px;
          bottom: 145px;
          width: 60px;
          height: 60px;
          font-size: 13px;
          background: rgba(180, 120, 20, 0.65);
        }
        /* Virtual Thumbstick Zone */
        .touch-stick-zone {
          position: absolute;
          bottom: 24px;
          left: 20px;
          width: 160px;
          height: 160px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.08);
          border: 2px dashed rgba(255, 255, 255, 0.25);
          pointer-events: auto;
          display: none;
        }
        .touch-stick-knob {
          position: absolute;
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.7);
          box-shadow: 0 4px 10px rgba(0,0,0,0.5);
          top: 50px;
          left: 50px;
          pointer-events: none;
        }
      </style>

      <div class="touch-top-bar">
        <div style="display: flex; gap: 8px; pointer-events: auto;">
          <div class="touch-btn" id="btn-pause">ESC</div>
          <div class="touch-btn" id="btn-camera">CAM</div>
          <div class="touch-btn" id="btn-reset">RESET</div>
        </div>
        <div style="display: flex; gap: 8px; pointer-events: auto;">
          <div class="touch-btn" id="btn-mode">STEER</div>
          <div class="touch-btn" id="btn-recenter" style="display: none;">CAL</div>
          <div class="touch-btn" id="btn-lookback">LOOK</div>
        </div>
      </div>

      <div class="touch-left-cluster" id="touch-left-buttons">
        <div class="touch-btn btn-gear-down" id="btn-gear-down">Q<br>DOWN</div>
        <div class="touch-btn btn-gear-up" id="btn-gear-up">E<br>UP</div>
        <div class="touch-btn btn-steer-left" id="btn-steer-left">◀</div>
        <div class="touch-btn btn-steer-right" id="btn-steer-right">▶</div>
      </div>

      <div class="touch-stick-zone" id="touch-stick-zone">
        <div class="touch-stick-knob" id="touch-stick-knob"></div>
      </div>

      <div class="touch-right-cluster">
        <div class="touch-btn btn-nos" id="btn-nos">NOS</div>
        <div class="touch-btn btn-handbrake" id="btn-handbrake">HAND</div>
        <div class="touch-btn btn-brake" id="btn-brake">BRAKE</div>
        <div class="touch-btn btn-gas" id="btn-gas">GAS</div>
      </div>
    `;

    this.container.appendChild(root);

    // Bind Controls
    this.bindPedals(root);
    this.bindSteeringButtons(root);
    this.bindThumbstick(root);
    this.bindGears(root);
    this.bindTopBar(root);
    this.updateSteeringUI();
  }

  private bindPedals(root: HTMLElement): void {
    const btnGas = root.querySelector('#btn-gas') as HTMLElement;
    const btnBrake = root.querySelector('#btn-brake') as HTMLElement;
    const btnHandbrake = root.querySelector('#btn-handbrake') as HTMLElement;
    const btnNos = root.querySelector('#btn-nos') as HTMLElement;

    // Gas & slide-up to Nitrous
    this.bindTouchButton(btnGas, (down) => {
      this.gasPressed = down;
      this.adapter.setKey(VK_UP, down);
      this.updateAxes();
    }, (e) => {
      // If user slides finger up > 40px while holding gas, trigger NOS
      if (e.touches && e.touches[0]) {
        const rect = btnGas.getBoundingClientRect();
        const touchY = e.touches[0].clientY;
        if (touchY < rect.top - 10) {
          this.adapter.setKey(VK_LSHIFT, true);
          this.adapter.setButton(4, true); // LB
        } else {
          this.adapter.setKey(VK_LSHIFT, false);
          this.adapter.setButton(4, false);
        }
      }
    });

    // Brake
    this.bindTouchButton(btnBrake, (down) => {
      this.brakePressed = down;
      this.adapter.setKey(VK_DOWN, down);
      this.updateAxes();
    });

    // Handbrake
    this.bindTouchButton(btnHandbrake, (down) => {
      this.adapter.setKey(VK_SPACE, down);
      this.adapter.setButton(5, down); // RB
    });

    // NOS
    this.bindTouchButton(btnNos, (down) => {
      this.adapter.setKey(VK_LSHIFT, down);
      this.adapter.setButton(4, down); // LB
    });
  }

  private bindSteeringButtons(root: HTMLElement): void {
    const btnLeft = root.querySelector('#btn-steer-left') as HTMLElement;
    const btnRight = root.querySelector('#btn-steer-right') as HTMLElement;

    this.bindTouchButton(btnLeft, (down) => {
      this.steerLeftPressed = down;
      this.adapter.setKey(VK_LEFT, down);
      this.updateAxes();
    });

    this.bindTouchButton(btnRight, (down) => {
      this.steerRightPressed = down;
      this.adapter.setKey(VK_RIGHT, down);
      this.updateAxes();
    });
  }

  private bindThumbstick(root: HTMLElement): void {
    const zone = root.querySelector('#touch-stick-zone') as HTMLElement;
    const knob = root.querySelector('#touch-stick-knob') as HTMLElement;

    let touchId: number | null = null;
    const radius = 50; // Max displacement

    const onStart = (e: TouchEvent) => {
      if (touchId === null && e.changedTouches[0]) {
        touchId = e.changedTouches[0].identifier;
        move(e.changedTouches[0]);
      }
    };

    const onMove = (e: TouchEvent) => {
      for (let i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier === touchId) {
          move(e.changedTouches[i]);
          break;
        }
      }
    };

    const onEnd = (e: TouchEvent) => {
      for (let i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier === touchId) {
          touchId = null;
          knob.style.transform = `translate(0px, 0px)`;
          if (this.steeringMode === 'stick') {
            this.adapter.setAxes(0, this.gasPressed ? 32767 : 0, this.brakePressed ? 32767 : 0);
          }
          break;
        }
      }
    };

    const move = (t: Touch) => {
      const rect = zone.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      let dx = t.clientX - centerX;
      let dy = t.clientY - centerY;
      const dist = Math.hypot(dx, dy);

      if (dist > radius) {
        dx = (dx / dist) * radius;
        dy = (dy / dist) * radius;
      }

      knob.style.transform = `translate(${dx}px, ${dy}px)`;

      if (this.steeringMode === 'stick') {
        const normX = dx / radius;
        const steerVal = Math.round(normX * 32767);
        this.adapter.setAxes(steerVal, this.gasPressed ? 32767 : 0, this.brakePressed ? 32767 : 0);
      }
    };

    zone.addEventListener('touchstart', onStart, { passive: true });
    zone.addEventListener('touchmove', onMove, { passive: true });
    zone.addEventListener('touchend', onEnd, { passive: true });
    zone.addEventListener('touchcancel', onEnd, { passive: true });
  }

  private bindGears(root: HTMLElement): void {
    const btnDown = root.querySelector('#btn-gear-down') as HTMLElement;
    const btnUp = root.querySelector('#btn-gear-up') as HTMLElement;

    this.bindTouchButton(btnDown, (down) => {
      this.adapter.setKey(VK_Q, down);
      this.adapter.setButton(2, down); // X
    });

    this.bindTouchButton(btnUp, (down) => {
      this.adapter.setKey(VK_E, down);
      this.adapter.setButton(0, down); // A
    });
  }

  private bindTopBar(root: HTMLElement): void {
    const btnPause = root.querySelector('#btn-pause') as HTMLElement;
    const btnCamera = root.querySelector('#btn-camera') as HTMLElement;
    const btnReset = root.querySelector('#btn-reset') as HTMLElement;
    const btnLook = root.querySelector('#btn-lookback') as HTMLElement;
    const btnMode = root.querySelector('#btn-mode') as HTMLElement;
    const btnRecenter = root.querySelector('#btn-recenter') as HTMLElement;

    this.bindTouchButton(btnPause, (down) => this.adapter.setKey(VK_ESCAPE, down));
    this.bindTouchButton(btnCamera, (down) => this.adapter.setKey(VK_C, down));
    this.bindTouchButton(btnReset, (down) => this.adapter.setKey(VK_R, down));
    this.bindTouchButton(btnLook, (down) => {
      this.adapter.setKey(VK_B, down);
      this.adapter.setPov(0, down ? 18000 : 0xFFFFFFFF);
    });

    btnMode.addEventListener('click', () => {
      const idx = STEERING_MODES.indexOf(this.steeringMode);
      const next = STEERING_MODES[(idx + 1) % STEERING_MODES.length];
      this.setSteeringMode(next);
    });

    btnRecenter.addEventListener('click', () => this.recenterTilt());
  }

  private updateSteeringUI(): void {
    const root = document.getElementById('prostreet-touch-overlay');
    if (!root) return;

    const leftButtons = root.querySelector('#touch-left-buttons') as HTMLElement;
    const stickZone = root.querySelector('#touch-stick-zone') as HTMLElement;
    const btnMode = root.querySelector('#btn-mode') as HTMLElement;
    const btnRecenter = root.querySelector('#btn-recenter') as HTMLElement;

    if (btnMode) {
      btnMode.textContent = this.steeringMode === 'buttons' ? 'BTNS' : (this.steeringMode === 'stick' ? 'STICK' : 'TILT');
    }

    if (this.steeringMode === 'buttons') {
      if (leftButtons) leftButtons.style.display = 'block';
      if (stickZone) stickZone.style.display = 'none';
      if (btnRecenter) btnRecenter.style.display = 'none';
    } else if (this.steeringMode === 'stick') {
      if (leftButtons) leftButtons.style.display = 'none';
      if (stickZone) stickZone.style.display = 'block';
      if (btnRecenter) btnRecenter.style.display = 'none';
    } else if (this.steeringMode === 'tilt') {
      if (leftButtons) leftButtons.style.display = 'none';
      if (stickZone) stickZone.style.display = 'none';
      if (btnRecenter) btnRecenter.style.display = 'flex';
    }

    // Reset axis when switching mode
    this.adapter.setAxes(0, this.gasPressed ? 32767 : 0, this.brakePressed ? 32767 : 0);
  }

  private updateAxes(): void {
    let steerLx = 0;
    if (this.steeringMode === 'buttons') {
      if (this.steerLeftPressed && !this.steerRightPressed) steerLx = -32768;
      else if (this.steerRightPressed && !this.steerLeftPressed) steerLx = 32767;
    }
    const throttleRz = this.gasPressed ? 32767 : 0;
    const brakeLz = this.brakePressed ? 32767 : 0;
    this.adapter.setAxes(steerLx, throttleRz, brakeLz);
  }

  private initDeviceOrientation(): void {
    const onOrientation = (e: DeviceOrientationEvent) => {
      if (this.steeringMode !== 'tilt') return;
      // In landscape orientation, roll/gamma controls left/right tilt
      let roll = (window.orientation === 90) ? -(e.beta ?? 0) :
                 (window.orientation === -90) ? (e.beta ?? 0) : (e.gamma ?? 0);

      const clamped = Math.max(-30, Math.min(30, roll - this.tiltOffset));
      const norm = clamped / 30; // -1.0 .. 1.0
      const steerVal = Math.round(norm * 32767);
      this.adapter.setAxes(steerVal, this.gasPressed ? 32767 : 0, this.brakePressed ? 32767 : 0);
    };

    if (typeof window !== 'undefined' && 'DeviceOrientationEvent' in window) {
      window.addEventListener('deviceorientation', onOrientation, true);
      this.cleanups.push(() => window.removeEventListener('deviceorientation', onOrientation, true));
    }
  }

  private bindTouchButton(
    el: HTMLElement,
    onChange: (down: boolean) => void,
    onMove?: (e: TouchEvent) => void
  ): void {
    let active = false;

    const start = (e: Event) => {
      e.preventDefault();
      if (!active) {
        active = true;
        el.classList.add('active');
        onChange(true);
      }
    };

    const end = (e: Event) => {
      e.preventDefault();
      if (active) {
        active = false;
        el.classList.remove('active');
        onChange(false);
      }
    };

    el.addEventListener('touchstart', start, { passive: false });
    el.addEventListener('touchend', end, { passive: false });
    el.addEventListener('touchcancel', end, { passive: false });
    el.addEventListener('mousedown', start);
    el.addEventListener('mouseup', end);
    el.addEventListener('mouseleave', end);

    if (onMove) {
      el.addEventListener('touchmove', onMove, { passive: true });
    }
  }

  private preventPinchZoom(): void {
    const prevent = (e: Event) => e.preventDefault();
    document.addEventListener('gesturestart', prevent, { passive: false });
    document.addEventListener('gesturechange', prevent, { passive: false });
  }

  private acquireWakeLock(): void {
    if (typeof navigator !== 'undefined' && 'wakeLock' in navigator) {
      const wl = (navigator as unknown as { wakeLock: { request(t: string): Promise<{ release(): Promise<void> }> } }).wakeLock;
      const requestLock = async () => {
        try {
          const lock = await wl.request('screen');
          this.wakeLockRelease = () => lock.release();
        } catch {}
      };
      void requestLock();
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) void requestLock();
      });
    }
  }

  public destroy(): void {
    for (const c of this.cleanups) c();
    if (this.wakeLockRelease) this.wakeLockRelease();
    const el = document.getElementById('prostreet-touch-overlay');
    if (el) el.remove();
  }
}

