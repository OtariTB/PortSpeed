/**
 * Need for Speed ProStreet - Direct3D 9 Command Stream WebGL2 Consumer.
 *
 * Implements the browser-side ring buffer reader and WebGL2 command dispatcher
 * for Phase 4.1 / Phase 4.3.
 *
 * Protocol specification: runtime/d3d9_cmd.h
 */

export const D3D9_RING_MAGIC = 0x39443344; // "D3D9" in little-endian
export const D3D9_RING_VERSION = 1;
export const D3D9_RING_HEADER_SIZE = 64;

export enum D3D9CmdType {
  NOP = 0,
  CLEAR = 1,
  BEGIN_SCENE = 2,
  END_SCENE = 3,
  PRESENT = 4,
  SET_RENDER_STATE = 5,
  SET_SAMPLER_STATE = 6,
  SET_TEXTURE = 7,
  SET_TRANSFORM = 8,
  SET_VIEWPORT = 9,
  SET_STREAM_SOURCE = 10,
  SET_INDICES = 11,
  DRAW_PRIMITIVE = 12,
  DRAW_INDEXED_PRIMITIVE = 13,
  CREATE_VERTEX_BUFFER = 14,
  CREATE_INDEX_BUFFER = 15,
  CREATE_TEXTURE = 16,
  UPDATE_TEXTURE = 17,
  DESTROY_RESOURCE = 18,
  SET_VERTEX_DECLARATION = 19,
  SET_VERTEX_SHADER = 20,
  SET_PIXEL_SHADER = 21,
  SET_VS_CONSTANTS = 22,
  SET_PS_CONSTANTS = 23,
  SET_SCISSOR_RECT = 24,
  COUNT = 25,
}

// Clear Flags (D3DCLEAR)
export const D3DCLEAR_TARGET = 0x00000001;
export const D3DCLEAR_ZBUFFER = 0x00000002;
export const D3DCLEAR_STENCIL = 0x00000004;

// Direct3D 9 Render States (D3DRENDERSTATETYPE)
export const D3DRS_ZENABLE = 7;
export const D3DRS_ZWRITEENABLE = 14;
export const D3DRS_SRCBLEND = 19;
export const D3DRS_DESTBLEND = 20;
export const D3DRS_CULLMODE = 22;
export const D3DRS_ZFUNC = 23;
export const D3DRS_ALPHABLENDENABLE = 27;
export const D3DRS_COLORWRITEENABLE = 168;

// D3DZBUFFERTYPE
export const D3DZB_FALSE = 0;
export const D3DZB_TRUE = 1;
export const D3DZB_USEW = 2;

// D3DCMPFUNC
export const D3DCMP_NEVER = 1;
export const D3DCMP_LESS = 2;
export const D3DCMP_EQUAL = 3;
export const D3DCMP_LESSEQUAL = 4;
export const D3DCMP_GREATER = 5;
export const D3DCMP_NOTEQUAL = 6;
export const D3DCMP_GREATEREQUAL = 7;
export const D3DCMP_ALWAYS = 8;

// D3DCULL
export const D3DCULL_NONE = 1;
export const D3DCULL_CW = 2;
export const D3DCULL_CCW = 3;

// D3DBLEND
export const D3DBLEND_ZERO = 1;
export const D3DBLEND_ONE = 2;
export const D3DBLEND_SRCCOLOR = 3;
export const D3DBLEND_INVSRCCOLOR = 4;
export const D3DBLEND_SRCALPHA = 5;
export const D3DBLEND_INVSRCALPHA = 6;
export const D3DBLEND_DESTALPHA = 7;
export const D3DBLEND_INVDESTALPHA = 8;
export const D3DBLEND_DESTCOLOR = 9;
export const D3DBLEND_INVDESTCOLOR = 10;
export const D3DBLEND_SRCALPHASAT = 11;
export const D3DBLEND_BOTHSRCALPHA = 12;
export const D3DBLEND_BOTHINVSRCALPHA = 13;
export const D3DBLEND_BLENDFACTOR = 14;
export const D3DBLEND_INVBLENDFACTOR = 15;

// D3DCOLORWRITEENABLE
export const D3DCOLORWRITEENABLE_RED = 1;
export const D3DCOLORWRITEENABLE_GREEN = 2;
export const D3DCOLORWRITEENABLE_BLUE = 4;
export const D3DCOLORWRITEENABLE_ALPHA = 8;

export enum SceneState {
  IDLE = 0,
  IN_SCENE = 1,
}

export interface D3D9ClearCommand {
  type: D3D9CmdType.CLEAR;
  flags: number;
  color: number;
  r: number;
  g: number;
  b: number;
  a: number;
  z: number;
  stencil: number;
  count: number;
}

export interface D3D9PresentCommand {
  type: D3D9CmdType.PRESENT;
  srcRect: { x: number; y: number; w: number; h: number };
}

export interface D3D9BeginSceneCommand {
  type: D3D9CmdType.BEGIN_SCENE;
}

export interface D3D9EndSceneCommand {
  type: D3D9CmdType.END_SCENE;
}

export interface D3D9NopCommand {
  type: D3D9CmdType.NOP;
}

export interface D3D9SetViewportCommand {
  type: D3D9CmdType.SET_VIEWPORT;
  x: number;
  y: number;
  width: number;
  height: number;
  minZ: number;
  maxZ: number;
  glX: number;
  glY: number;
  glWidth: number;
  glHeight: number;
}

export interface D3D9SetRenderStateCommand {
  type: D3D9CmdType.SET_RENDER_STATE;
  state: number;
  value: number;
}

export type D3D9Command =
  | D3D9ClearCommand
  | D3D9PresentCommand
  | D3D9BeginSceneCommand
  | D3D9EndSceneCommand
  | D3D9NopCommand
  | D3D9SetViewportCommand
  | D3D9SetRenderStateCommand;

export interface D3D9ConsumerOptions {
  gl?: WebGL2RenderingContext | null;
  onPresent?: (frameIndex: number, cmd: D3D9PresentCommand) => void;
}

export interface D3D9Viewport {
  x: number;
  y: number;
  width: number;
  height: number;
  minZ: number;
  maxZ: number;
  glX: number;
  glY: number;
  glWidth: number;
  glHeight: number;
}

export interface D3D9RenderStates {
  zEnable: boolean;
  zWriteEnable: boolean;
  zFunc: number;
  cullMode: number;
  alphaBlendEnable: boolean;
  srcBlend: number;
  destBlend: number;
  colorWriteEnable: number;
}

export class D3D9CommandConsumer {
  private view: DataView;
  private u8: Uint8Array;
  private ringBase: number;
  private gl: WebGL2RenderingContext | null;
  private onPresent?: (frameIndex: number, cmd: D3D9PresentCommand) => void;

  public sceneState: SceneState = SceneState.IDLE;
  public presentedFrames: number = 0;
  public totalCommandsExecuted: number = 0;
  public lastClear: D3D9ClearCommand | null = null;

  // Active Viewport and Render States (initialized to authentic Direct3D 9 defaults)
  public viewport: D3D9Viewport = {
    x: 0,
    y: 0,
    width: 1280,
    height: 720,
    minZ: 0.0,
    maxZ: 1.0,
    glX: 0,
    glY: 0,
    glWidth: 1280,
    glHeight: 720,
  };

  public renderStates: D3D9RenderStates = {
    zEnable: true,          // D3D9 default: D3DZB_TRUE (1)
    zWriteEnable: true,     // D3D9 default: TRUE (1)
    zFunc: D3DCMP_LESSEQUAL,// D3D9 default: D3DCMP_LESSEQUAL (4)
    cullMode: D3DCULL_CCW,  // D3D9 default: D3DCULL_CCW (3)
    alphaBlendEnable: false,// D3D9 default: FALSE (0)
    srcBlend: D3DBLEND_ONE, // D3D9 default: D3DBLEND_ONE (2)
    destBlend: D3DBLEND_ZERO,// D3D9 default: D3DBLEND_ZERO (1)
    colorWriteEnable: 0x0f, // D3D9 default: 0xF (R|G|B|A enabled)
  };

  constructor(
    buffer: ArrayBuffer | SharedArrayBuffer,
    byteOffset: number = 0,
    options: D3D9ConsumerOptions = {}
  ) {
    if (buffer.byteLength < byteOffset + D3D9_RING_HEADER_SIZE) {
      throw new Error(
        `Buffer too small for ring header: ${buffer.byteLength} < ${byteOffset + D3D9_RING_HEADER_SIZE}`
      );
    }
    this.ringBase = byteOffset;
    this.view = new DataView(buffer);
    this.u8 = new Uint8Array(buffer);
    this.gl = options.gl ?? null;
    this.onPresent = options.onPresent;

    // Apply authentic D3D9 default states to WebGL2 context
    if (this.gl) {
      this.applyInitialWebGLDefaults();
    }
  }

  private applyInitialWebGLDefaults(): void {
    const gl = this.gl;
    if (!gl) return;

    // Viewport default to canvas dimensions
    const canvasH = (gl.canvas as HTMLCanvasElement)?.height ?? 720;
    const canvasW = (gl.canvas as HTMLCanvasElement)?.width ?? 1280;
    this.viewport = {
      x: 0,
      y: 0,
      width: canvasW,
      height: canvasH,
      minZ: 0.0,
      maxZ: 1.0,
      glX: 0,
      glY: 0,
      glWidth: canvasW,
      glHeight: canvasH,
    };
    gl.viewport(0, 0, canvasW, canvasH);
    gl.depthRange(0.0, 1.0);

    // ZENABLE default: enabled
    gl.enable(gl.DEPTH_TEST);
    // ZWRITEENABLE default: enabled
    gl.depthMask(true);
    // ZFUNC default: LEQUAL
    gl.depthFunc(gl.LEQUAL);
    // CULLMODE default: cull CCW (D3D9 front face is CW)
    gl.enable(gl.CULL_FACE);
    gl.frontFace(gl.CW);
    gl.cullFace(gl.BACK); // culls CCW faces
    // ALPHABLENDENABLE default: disabled
    gl.disable(gl.BLEND);
    // SRCBLEND / DESTBLEND default: ONE, ZERO
    gl.blendFunc(gl.ONE, gl.ZERO);
    // COLORWRITEENABLE default: 0xF (all enabled)
    gl.colorMask(true, true, true, true);
  }

  public validateRingHeader(): {
    magic: number;
    version: number;
    head: number;
    tail: number;
    capacity: number;
    frameIndex: number;
    droppedFrames: number;
    flags: number;
  } {
    const magic = this.view.getUint32(this.ringBase + 0, true);
    if (magic !== D3D9_RING_MAGIC) {
      throw new Error(
        `Invalid ring buffer magic: expected 0x${D3D9_RING_MAGIC.toString(16)}, got 0x${magic.toString(16)}`
      );
    }

    const version = this.view.getUint32(this.ringBase + 4, true);
    if (version !== D3D9_RING_VERSION) {
      throw new Error(
        `Unsupported ring buffer version: expected ${D3D9_RING_VERSION}, got ${version}`
      );
    }

    const head = this.view.getUint32(this.ringBase + 8, true);
    const tail = this.view.getUint32(this.ringBase + 12, true);
    const capacity = this.view.getUint32(this.ringBase + 16, true);
    const frameIndex = this.view.getUint32(this.ringBase + 20, true);
    const droppedFrames = this.view.getUint32(this.ringBase + 24, true);
    const flags = this.view.getUint32(this.ringBase + 28, true);

    if (capacity <= 0 || this.ringBase + D3D9_RING_HEADER_SIZE + capacity > this.u8.byteLength) {
      throw new Error(
        `Invalid ring buffer capacity: ${capacity} (exceeds buffer size ${this.u8.byteLength})`
      );
    }

    if (head >= capacity || tail >= capacity) {
      throw new Error(
        `Ring buffer pointer out of bounds: head=${head}, tail=${tail}, capacity=${capacity}`
      );
    }

    return { magic, version, head, tail, capacity, frameIndex, droppedFrames, flags };
  }

  public getPendingBytes(): number {
    const { head, tail, capacity } = this.validateRingHeader();
    if (head >= tail) {
      return head - tail;
    }
    return capacity - (tail - head);
  }

  private readBytesCircular(
    dest: Uint8Array,
    srcRingOffset: number,
    count: number,
    capacity: number
  ): void {
    const dataStart = this.ringBase + D3D9_RING_HEADER_SIZE;
    for (let i = 0; i < count; i++) {
      dest[i] = this.u8[dataStart + ((srcRingOffset + i) % capacity)];
    }
  }

  private mapGlBlendFactor(factor: number, gl: WebGL2RenderingContext): number {
    switch (factor) {
      case D3DBLEND_ZERO: return gl.ZERO;
      case D3DBLEND_ONE: return gl.ONE;
      case D3DBLEND_SRCCOLOR: return gl.SRC_COLOR;
      case D3DBLEND_INVSRCCOLOR: return gl.ONE_MINUS_SRC_COLOR;
      case D3DBLEND_SRCALPHA: return gl.SRC_ALPHA;
      case D3DBLEND_INVSRCALPHA: return gl.ONE_MINUS_SRC_ALPHA;
      case D3DBLEND_DESTALPHA: return gl.DST_ALPHA;
      case D3DBLEND_INVDESTALPHA: return gl.ONE_MINUS_DST_ALPHA;
      case D3DBLEND_DESTCOLOR: return gl.DST_COLOR;
      case D3DBLEND_INVDESTCOLOR: return gl.ONE_MINUS_DST_COLOR;
      case D3DBLEND_SRCALPHASAT: return gl.SRC_ALPHA_SATURATE;
      case D3DBLEND_BLENDFACTOR: return gl.CONSTANT_COLOR;
      case D3DBLEND_INVBLENDFACTOR: return gl.ONE_MINUS_CONSTANT_COLOR;
      default:
        throw new Error(`Unsupported blend factor: ${factor}`);
    }
  }

  private mapGlCmpFunc(func: number, gl: WebGL2RenderingContext): number {
    switch (func) {
      case D3DCMP_NEVER: return gl.NEVER;
      case D3DCMP_LESS: return gl.LESS;
      case D3DCMP_EQUAL: return gl.EQUAL;
      case D3DCMP_LESSEQUAL: return gl.LEQUAL;
      case D3DCMP_GREATER: return gl.GREATER;
      case D3DCMP_NOTEQUAL: return gl.NOTEQUAL;
      case D3DCMP_GREATEREQUAL: return gl.GEQUAL;
      case D3DCMP_ALWAYS: return gl.ALWAYS;
      default:
        throw new Error(`Unsupported comparison function: ${func}`);
    }
  }

  public applyRenderState(state: number, value: number): void {
    const gl = this.gl;

    switch (state) {
      case D3DRS_ZENABLE: {
        if (value === D3DZB_FALSE) {
          this.renderStates.zEnable = false;
          if (gl) gl.disable(gl.DEPTH_TEST);
        } else if (value === D3DZB_TRUE) {
          this.renderStates.zEnable = true;
          if (gl) gl.enable(gl.DEPTH_TEST);
        } else {
          throw new Error(
            `Unsupported ZENABLE value: ${value} (only D3DZB_FALSE=0 and D3DZB_TRUE=1 supported, W-buffer not supported in WebGL2)`
          );
        }
        break;
      }

      case D3DRS_ZWRITEENABLE: {
        if (value === 0) {
          this.renderStates.zWriteEnable = false;
          if (gl) gl.depthMask(false);
        } else if (value === 1) {
          this.renderStates.zWriteEnable = true;
          if (gl) gl.depthMask(true);
        } else {
          throw new Error(
            `Unsupported ZWRITEENABLE value: ${value} (must be 0 or 1)`
          );
        }
        break;
      }

      case D3DRS_ZFUNC: {
        if (value < D3DCMP_NEVER || value > D3DCMP_ALWAYS) {
          throw new Error(
            `Unsupported ZFUNC value: ${value} (must be between 1 and 8)`
          );
        }
        this.renderStates.zFunc = value;
        if (gl) {
          gl.depthFunc(this.mapGlCmpFunc(value, gl));
        }
        break;
      }

      case D3DRS_CULLMODE: {
        if (value === D3DCULL_NONE) {
          this.renderStates.cullMode = D3DCULL_NONE;
          if (gl) gl.disable(gl.CULL_FACE);
        } else if (value === D3DCULL_CW) {
          this.renderStates.cullMode = D3DCULL_CW;
          if (gl) {
            gl.enable(gl.CULL_FACE);
            gl.frontFace(gl.CW);
            gl.cullFace(gl.FRONT); // culls CW faces
          }
        } else if (value === D3DCULL_CCW) {
          this.renderStates.cullMode = D3DCULL_CCW;
          if (gl) {
            gl.enable(gl.CULL_FACE);
            gl.frontFace(gl.CW);
            gl.cullFace(gl.BACK); // culls CCW faces
          }
        } else {
          throw new Error(
            `Unsupported CULLMODE value: ${value} (must be NONE=1, CW=2, or CCW=3)`
          );
        }
        break;
      }

      case D3DRS_ALPHABLENDENABLE: {
        if (value === 0) {
          this.renderStates.alphaBlendEnable = false;
          if (gl) gl.disable(gl.BLEND);
        } else if (value === 1) {
          this.renderStates.alphaBlendEnable = true;
          if (gl) gl.enable(gl.BLEND);
        } else {
          throw new Error(
            `Unsupported ALPHABLENDENABLE value: ${value} (must be 0 or 1)`
          );
        }
        break;
      }

      case D3DRS_SRCBLEND: {
        // Validate blend factor
        if (
          value < D3DBLEND_ZERO ||
          value > D3DBLEND_INVBLENDFACTOR ||
          value === D3DBLEND_BOTHSRCALPHA ||
          value === D3DBLEND_BOTHINVSRCALPHA
        ) {
          throw new Error(`Unsupported SRCBLEND value: ${value}`);
        }
        this.renderStates.srcBlend = value;
        if (gl) {
          const s = this.mapGlBlendFactor(this.renderStates.srcBlend, gl);
          const d = this.mapGlBlendFactor(this.renderStates.destBlend, gl);
          gl.blendFunc(s, d);
        }
        break;
      }

      case D3DRS_DESTBLEND: {
        // Validate blend factor
        if (
          value < D3DBLEND_ZERO ||
          value > D3DBLEND_INVBLENDFACTOR ||
          value === D3DBLEND_BOTHSRCALPHA ||
          value === D3DBLEND_BOTHINVSRCALPHA
        ) {
          throw new Error(`Unsupported DESTBLEND value: ${value}`);
        }
        this.renderStates.destBlend = value;
        if (gl) {
          const s = this.mapGlBlendFactor(this.renderStates.srcBlend, gl);
          const d = this.mapGlBlendFactor(this.renderStates.destBlend, gl);
          gl.blendFunc(s, d);
        }
        break;
      }

      case D3DRS_COLORWRITEENABLE: {
        if (value < 0 || (value & ~0x0f) !== 0) {
          throw new Error(
            `Unsupported COLORWRITEENABLE value: ${value} (valid bits are 0x1=RED, 0x2=GREEN, 0x4=BLUE, 0x8=ALPHA)`
          );
        }
        this.renderStates.colorWriteEnable = value;
        const r = (value & D3DCOLORWRITEENABLE_RED) !== 0;
        const g = (value & D3DCOLORWRITEENABLE_GREEN) !== 0;
        const b = (value & D3DCOLORWRITEENABLE_BLUE) !== 0;
        const a = (value & D3DCOLORWRITEENABLE_ALPHA) !== 0;
        if (gl) {
          gl.colorMask(r, g, b, a);
        }
        break;
      }

      default: {
        throw new Error(
          `Unsupported render state: ${state} (only ZENABLE, ZWRITEENABLE, ZFUNC, CULLMODE, ALPHABLENDENABLE, SRCBLEND, DESTBLEND, and COLORWRITEENABLE supported in this milestone)`
        );
      }
    }
  }

  public processCommands(): D3D9Command[] {
    const executed: D3D9Command[] = [];
    const hdrBuf = new Uint8Array(8);
    const hdrView = new DataView(hdrBuf.buffer);

    while (true) {
      const { head, tail, capacity } = this.validateRingHeader();
      const pending = head >= tail ? head - tail : capacity - (tail - head);
      if (pending === 0) {
        break;
      }

      if (pending < 8) {
        throw new Error(
          `Truncated command packet header: ${pending} bytes pending, 8 required`
        );
      }

      // Read 8-byte command packet header
      this.readBytesCircular(hdrBuf, tail, 8, capacity);
      const cmdType = hdrView.getUint16(0, true);
      const flags = hdrView.getUint16(2, true);
      const payloadBytes = hdrView.getUint32(4, true);

      if (cmdType >= D3D9CmdType.COUNT) {
        throw new Error(
          `Invalid command opcode: ${cmdType} (maximum known opcode is ${D3D9CmdType.COUNT - 1})`
        );
      }

      const alignedPayload = (payloadBytes + 3) & ~3;
      const packetSize = 8 + alignedPayload;

      if (packetSize > pending) {
        throw new Error(
          `Truncated command packet for opcode ${cmdType}: ${packetSize} bytes required, ${pending} available`
        );
      }

      // Read payload bytes
      let payloadBuf: Uint8Array | null = null;
      let payloadView: DataView | null = null;
      if (alignedPayload > 0) {
        payloadBuf = new Uint8Array(alignedPayload);
        this.readBytesCircular(payloadBuf, (tail + 8) % capacity, alignedPayload, capacity);
        payloadView = new DataView(payloadBuf.buffer);
      }

      // Dispatch supported commands
      let cmd: D3D9Command;
      switch (cmdType) {
        case D3D9CmdType.NOP: {
          cmd = { type: D3D9CmdType.NOP };
          break;
        }

        case D3D9CmdType.BEGIN_SCENE: {
          if (this.sceneState === SceneState.IN_SCENE) {
            throw new Error(
              "Invalid state transition: BEGIN_SCENE called while already IN_SCENE"
            );
          }
          this.sceneState = SceneState.IN_SCENE;
          cmd = { type: D3D9CmdType.BEGIN_SCENE };
          break;
        }

        case D3D9CmdType.END_SCENE: {
          if (this.sceneState !== SceneState.IN_SCENE) {
            throw new Error(
              "Invalid state transition: END_SCENE called while IDLE"
            );
          }
          this.sceneState = SceneState.IDLE;
          cmd = { type: D3D9CmdType.END_SCENE };
          break;
        }

        case D3D9CmdType.CLEAR: {
          if (!payloadView || payloadBytes < 20) {
            throw new Error(
              `Truncated CLEAR payload: expected at least 20 bytes, got ${payloadBytes}`
            );
          }
          const clearFlags = payloadView.getUint32(0, true);
          const color = payloadView.getUint32(4, true);
          const z = payloadView.getFloat32(8, true);
          const stencil = payloadView.getUint32(12, true);
          const count = payloadView.getUint32(16, true);

          // ARGB unpacking: 0xAARRGGBB
          const a = ((color >>> 24) & 0xff) / 255.0;
          const r = ((color >>> 16) & 0xff) / 255.0;
          const g = ((color >>> 8) & 0xff) / 255.0;
          const b = (color & 0xff) / 255.0;

          if (this.gl) {
            const gl = this.gl;
            let mask = 0;

            // Direct3D 9 Specification:
            // 1. D3DRS_COLORWRITEENABLE does NOT affect Clear. All channels are cleared.
            // 2. D3DRS_ZWRITEENABLE does NOT affect Clear. Depth is always cleared.
            // 3. Stencil write masks do NOT affect Clear. Stencil is always cleared.
            const needsColorMaskOverride =
              (clearFlags & D3DCLEAR_TARGET) !== 0 &&
              this.renderStates.colorWriteEnable !== 0x0f;
            const needsDepthMaskOverride =
              (clearFlags & D3DCLEAR_ZBUFFER) !== 0 &&
              !this.renderStates.zWriteEnable;

            if (clearFlags & D3DCLEAR_TARGET) {
              gl.clearColor(r, g, b, a);
              mask |= gl.COLOR_BUFFER_BIT;
              if (needsColorMaskOverride) {
                gl.colorMask(true, true, true, true);
              }
            }

            if (clearFlags & D3DCLEAR_ZBUFFER) {
              gl.clearDepth(z);
              mask |= gl.DEPTH_BUFFER_BIT;
              if (needsDepthMaskOverride) {
                gl.depthMask(true);
              }
            }

            if (clearFlags & D3DCLEAR_STENCIL) {
              gl.clearStencil(stencil);
              mask |= gl.STENCIL_BUFFER_BIT;
              gl.stencilMask(0xffffffff);
            }

            if (mask !== 0) {
              // In Direct3D 9, Clear is constrained to the active viewport rectangle
              const canvasH = (gl.canvas as HTMLCanvasElement)?.height ?? 0;
              const canvasW = (gl.canvas as HTMLCanvasElement)?.width ?? 0;
              const isSubViewport =
                this.viewport &&
                (this.viewport.glX !== 0 ||
                  this.viewport.glY !== 0 ||
                  this.viewport.glWidth !== canvasW ||
                  this.viewport.glHeight !== canvasH);

              if (isSubViewport) {
                gl.enable(gl.SCISSOR_TEST);
                gl.scissor(
                  this.viewport.glX,
                  this.viewport.glY,
                  this.viewport.glWidth,
                  this.viewport.glHeight
                );
              }

              gl.clear(mask);

              if (isSubViewport) {
                gl.disable(gl.SCISSOR_TEST);
              }
            }

            // Restore D3D9 state masks for subsequent draw operations
            if (needsColorMaskOverride) {
              const mr = (this.renderStates.colorWriteEnable & D3DCOLORWRITEENABLE_RED) !== 0;
              const mg = (this.renderStates.colorWriteEnable & D3DCOLORWRITEENABLE_GREEN) !== 0;
              const mb = (this.renderStates.colorWriteEnable & D3DCOLORWRITEENABLE_BLUE) !== 0;
              const ma = (this.renderStates.colorWriteEnable & D3DCOLORWRITEENABLE_ALPHA) !== 0;
              gl.colorMask(mr, mg, mb, ma);
            }

            if (needsDepthMaskOverride) {
              gl.depthMask(false);
            }
          }

          const clearCmd: D3D9ClearCommand = {
            type: D3D9CmdType.CLEAR,
            flags: clearFlags,
            color,
            r,
            g,
            b,
            a,
            z,
            stencil,
            count,
          };
          this.lastClear = clearCmd;
          cmd = clearCmd;
          break;
        }

        case D3D9CmdType.PRESENT: {
          if (this.sceneState === SceneState.IN_SCENE) {
            throw new Error(
              "Invalid state transition: PRESENT called while IN_SCENE"
            );
          }
          let srcRect = { x: 0, y: 0, w: 0, h: 0 };
          if (payloadView && payloadBytes >= 16) {
            srcRect = {
              x: payloadView.getUint32(0, true),
              y: payloadView.getUint32(4, true),
              w: payloadView.getUint32(8, true),
              h: payloadView.getUint32(12, true),
            };
          }

          this.presentedFrames++;
          const presCmd: D3D9PresentCommand = {
            type: D3D9CmdType.PRESENT,
            srcRect,
          };
          if (this.onPresent) {
            this.onPresent(this.presentedFrames, presCmd);
          }
          cmd = presCmd;
          break;
        }

        case D3D9CmdType.SET_VIEWPORT: {
          if (!payloadView || payloadBytes < 24) {
            throw new Error(
              `Truncated SET_VIEWPORT payload: expected 24 bytes, got ${payloadBytes}`
            );
          }
          const x = payloadView.getUint32(0, true);
          const y = payloadView.getUint32(4, true);
          const width = payloadView.getUint32(8, true);
          const height = payloadView.getUint32(12, true);
          const minZ = payloadView.getFloat32(16, true);
          const maxZ = payloadView.getFloat32(20, true);

          if (minZ < 0.0 || minZ > 1.0 || maxZ < 0.0 || maxZ > 1.0 || minZ > maxZ) {
            throw new Error(
              `Invalid viewport depth range: [${minZ}, ${maxZ}] (must be within [0.0, 1.0] with minZ <= maxZ)`
            );
          }

          // D3D9 (top-left origin) to WebGL2 (bottom-left origin) conversion
          const targetH =
            this.gl && this.gl.canvas
              ? (this.gl.canvas as HTMLCanvasElement).height
              : (this.viewport?.height || 720);
          const glX = x;
          const glY = targetH - (y + height);
          const glWidth = width;
          const glHeight = height;

          if (this.gl) {
            this.gl.viewport(glX, glY, glWidth, glHeight);
            this.gl.depthRange(minZ, maxZ);
          }

          const vp: D3D9Viewport = {
            x,
            y,
            width,
            height,
            minZ,
            maxZ,
            glX,
            glY,
            glWidth,
            glHeight,
          };
          this.viewport = vp;
          cmd = { type: D3D9CmdType.SET_VIEWPORT, ...vp };
          break;
        }

        case D3D9CmdType.SET_RENDER_STATE: {
          if (!payloadView || payloadBytes < 8) {
            throw new Error(
              `Truncated SET_RENDER_STATE payload: expected 8 bytes, got ${payloadBytes}`
            );
          }
          const state = payloadView.getUint32(0, true);
          const value = payloadView.getUint32(4, true);

          this.applyRenderState(state, value);
          cmd = { type: D3D9CmdType.SET_RENDER_STATE, state, value };
          break;
        }

        default: {
          throw new Error(
            `Unsupported command opcode in consumer: ${cmdType} (only NOP, CLEAR, BEGIN_SCENE, END_SCENE, PRESENT, SET_VIEWPORT, and SET_RENDER_STATE supported in this milestone)`
          );
        }
      }

      executed.push(cmd);
      this.totalCommandsExecuted++;

      // Advance tail pointer in shared ring header
      const newTail = (tail + packetSize) % capacity;
      this.view.setUint32(this.ringBase + 12, newTail, true);
    }

    return executed;
  }
}

/**
 * Producer helper for tests and guest emulation.
 * Serializes command packets into the shared ring buffer with wraparound support.
 */
export class D3D9CommandProducer {
  private view: DataView;
  private u8: Uint8Array;
  private ringBase: number;

  constructor(buffer: ArrayBuffer | SharedArrayBuffer, byteOffset: number = 0) {
    this.ringBase = byteOffset;
    this.view = new DataView(buffer);
    this.u8 = new Uint8Array(buffer);
  }

  public static initRing(
    buffer: ArrayBuffer | SharedArrayBuffer,
    byteOffset: number = 0,
    capacity: number = 4 * 1024 * 1024
  ): D3D9CommandProducer {
    if (buffer.byteLength < byteOffset + D3D9_RING_HEADER_SIZE + capacity) {
      throw new Error("Buffer too small for requested ring capacity and header");
    }
    const view = new DataView(buffer);
    view.setUint32(byteOffset + 0, D3D9_RING_MAGIC, true);
    view.setUint32(byteOffset + 4, D3D9_RING_VERSION, true);
    view.setUint32(byteOffset + 8, 0, true); // head
    view.setUint32(byteOffset + 12, 0, true); // tail
    view.setUint32(byteOffset + 16, capacity, true);
    view.setUint32(byteOffset + 20, 0, true); // frame_index
    view.setUint32(byteOffset + 24, 0, true); // dropped_frames
    view.setUint32(byteOffset + 28, 1, true); // flags (VSync default)
    for (let i = 0; i < 8; i++) {
      view.setUint32(byteOffset + 32 + i * 4, 0, true);
    }
    return new D3D9CommandProducer(buffer, byteOffset);
  }

  private writeBytesCircular(
    src: Uint8Array,
    dstRingOffset: number,
    count: number,
    capacity: number
  ): void {
    const dataStart = this.ringBase + D3D9_RING_HEADER_SIZE;
    for (let i = 0; i < count; i++) {
      this.u8[dataStart + ((dstRingOffset + i) % capacity)] = src[i];
    }
  }

  public emitRawPacket(
    cmdType: number,
    flags: number,
    payload: Uint8Array | null
  ): number {
    const head = this.view.getUint32(this.ringBase + 8, true);
    const tail = this.view.getUint32(this.ringBase + 12, true);
    const capacity = this.view.getUint32(this.ringBase + 16, true);

    const payloadBytes = payload ? payload.byteLength : 0;
    const alignedPayload = (payloadBytes + 3) & ~3;
    const packetSize = 8 + alignedPayload;

    // Available space check (leave 1 byte spare to distinguish full from empty)
    const available = head >= tail ? capacity - (head - tail) - 1 : tail - head - 1;
    if (packetSize > available) {
      const dropped = this.view.getUint32(this.ringBase + 24, true);
      this.view.setUint32(this.ringBase + 24, dropped + 1, true);
      throw new Error(
        `Ring buffer overflow: requires ${packetSize} bytes, but only ${available} available`
      );
    }

    const hdrBuf = new Uint8Array(8);
    const hdrView = new DataView(hdrBuf.buffer);
    hdrView.setUint16(0, cmdType, true);
    hdrView.setUint16(2, flags, true);
    hdrView.setUint32(4, alignedPayload, true);

    this.writeBytesCircular(hdrBuf, head, 8, capacity);

    if (payload && payloadBytes > 0) {
      this.writeBytesCircular(payload, (head + 8) % capacity, payloadBytes, capacity);
      // Zero out padding bytes if any
      if (alignedPayload > payloadBytes) {
        const padBuf = new Uint8Array(alignedPayload - payloadBytes);
        this.writeBytesCircular(
          padBuf,
          (head + 8 + payloadBytes) % capacity,
          padBuf.byteLength,
          capacity
        );
      }
    }

    const newHead = (head + packetSize) % capacity;
    this.view.setUint32(this.ringBase + 8, newHead, true);
    return packetSize;
  }

  public emitBeginScene(): void {
    this.emitRawPacket(D3D9CmdType.BEGIN_SCENE, 0, null);
  }

  public emitEndScene(): void {
    this.emitRawPacket(D3D9CmdType.END_SCENE, 0, null);
  }

  public emitClear(
    flags: number,
    color: number,
    z: number,
    stencil: number,
    count: number = 0
  ): void {
    const payload = new Uint8Array(20);
    const v = new DataView(payload.buffer);
    v.setUint32(0, flags, true);
    v.setUint32(4, color, true);
    v.setFloat32(8, z, true);
    v.setUint32(12, stencil, true);
    v.setUint32(16, count, true);
    this.emitRawPacket(D3D9CmdType.CLEAR, 0, payload);
  }

  public emitPresent(
    x: number = 0,
    y: number = 0,
    w: number = 0,
    h: number = 0
  ): void {
    const payload = new Uint8Array(16);
    const v = new DataView(payload.buffer);
    v.setUint32(0, x, true);
    v.setUint32(4, y, true);
    v.setUint32(8, w, true);
    v.setUint32(12, h, true);
    this.emitRawPacket(D3D9CmdType.PRESENT, 0, payload);

    // Monotonic frame counter in header
    const frameIndex = this.view.getUint32(this.ringBase + 20, true);
    this.view.setUint32(this.ringBase + 20, frameIndex + 1, true);
  }

  public emitSetViewport(
    x: number,
    y: number,
    width: number,
    height: number,
    minZ: number = 0.0,
    maxZ: number = 1.0
  ): void {
    const payload = new Uint8Array(24);
    const v = new DataView(payload.buffer);
    v.setUint32(0, x, true);
    v.setUint32(4, y, true);
    v.setUint32(8, width, true);
    v.setUint32(12, height, true);
    v.setFloat32(16, minZ, true);
    v.setFloat32(20, maxZ, true);
    this.emitRawPacket(D3D9CmdType.SET_VIEWPORT, 0, payload);
  }

  public emitSetRenderState(state: number, value: number): void {
    const payload = new Uint8Array(8);
    const v = new DataView(payload.buffer);
    v.setUint32(0, state, true);
    v.setUint32(4, value, true);
    this.emitRawPacket(D3D9CmdType.SET_RENDER_STATE, 0, payload);
  }
}
