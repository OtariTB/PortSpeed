"use strict";
var D3D9 = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
  var d3d9_consumer_exports = {};
  __export(d3d9_consumer_exports, {
    D3D9CmdType: () => D3D9CmdType,
    D3D9CommandConsumer: () => D3D9CommandConsumer,
    D3D9CommandProducer: () => D3D9CommandProducer,
    D3D9_RING_HEADER_SIZE: () => D3D9_RING_HEADER_SIZE,
    D3D9_RING_MAGIC: () => D3D9_RING_MAGIC,
    D3D9_RING_VERSION: () => D3D9_RING_VERSION,
    D3DBLEND_BLENDFACTOR: () => D3DBLEND_BLENDFACTOR,
    D3DBLEND_BOTHINVSRCALPHA: () => D3DBLEND_BOTHINVSRCALPHA,
    D3DBLEND_BOTHSRCALPHA: () => D3DBLEND_BOTHSRCALPHA,
    D3DBLEND_DESTALPHA: () => D3DBLEND_DESTALPHA,
    D3DBLEND_DESTCOLOR: () => D3DBLEND_DESTCOLOR,
    D3DBLEND_INVBLENDFACTOR: () => D3DBLEND_INVBLENDFACTOR,
    D3DBLEND_INVDESTALPHA: () => D3DBLEND_INVDESTALPHA,
    D3DBLEND_INVDESTCOLOR: () => D3DBLEND_INVDESTCOLOR,
    D3DBLEND_INVSRCALPHA: () => D3DBLEND_INVSRCALPHA,
    D3DBLEND_INVSRCCOLOR: () => D3DBLEND_INVSRCCOLOR,
    D3DBLEND_ONE: () => D3DBLEND_ONE,
    D3DBLEND_SRCALPHA: () => D3DBLEND_SRCALPHA,
    D3DBLEND_SRCALPHASAT: () => D3DBLEND_SRCALPHASAT,
    D3DBLEND_SRCCOLOR: () => D3DBLEND_SRCCOLOR,
    D3DBLEND_ZERO: () => D3DBLEND_ZERO,
    D3DCLEAR_STENCIL: () => D3DCLEAR_STENCIL,
    D3DCLEAR_TARGET: () => D3DCLEAR_TARGET,
    D3DCLEAR_ZBUFFER: () => D3DCLEAR_ZBUFFER,
    D3DCMP_ALWAYS: () => D3DCMP_ALWAYS,
    D3DCMP_EQUAL: () => D3DCMP_EQUAL,
    D3DCMP_GREATER: () => D3DCMP_GREATER,
    D3DCMP_GREATEREQUAL: () => D3DCMP_GREATEREQUAL,
    D3DCMP_LESS: () => D3DCMP_LESS,
    D3DCMP_LESSEQUAL: () => D3DCMP_LESSEQUAL,
    D3DCMP_NEVER: () => D3DCMP_NEVER,
    D3DCMP_NOTEQUAL: () => D3DCMP_NOTEQUAL,
    D3DCOLORWRITEENABLE_ALPHA: () => D3DCOLORWRITEENABLE_ALPHA,
    D3DCOLORWRITEENABLE_BLUE: () => D3DCOLORWRITEENABLE_BLUE,
    D3DCOLORWRITEENABLE_GREEN: () => D3DCOLORWRITEENABLE_GREEN,
    D3DCOLORWRITEENABLE_RED: () => D3DCOLORWRITEENABLE_RED,
    D3DCULL_CCW: () => D3DCULL_CCW,
    D3DCULL_CW: () => D3DCULL_CW,
    D3DCULL_NONE: () => D3DCULL_NONE,
    D3DRS_ALPHABLENDENABLE: () => D3DRS_ALPHABLENDENABLE,
    D3DRS_COLORWRITEENABLE: () => D3DRS_COLORWRITEENABLE,
    D3DRS_CULLMODE: () => D3DRS_CULLMODE,
    D3DRS_DESTBLEND: () => D3DRS_DESTBLEND,
    D3DRS_SRCBLEND: () => D3DRS_SRCBLEND,
    D3DRS_ZENABLE: () => D3DRS_ZENABLE,
    D3DRS_ZFUNC: () => D3DRS_ZFUNC,
    D3DRS_ZWRITEENABLE: () => D3DRS_ZWRITEENABLE,
    D3DZB_FALSE: () => D3DZB_FALSE,
    D3DZB_TRUE: () => D3DZB_TRUE,
    D3DZB_USEW: () => D3DZB_USEW,
    SceneState: () => SceneState
  });
  const D3D9_RING_MAGIC = 960770884;
  const D3D9_RING_VERSION = 1;
  const D3D9_RING_HEADER_SIZE = 64;
  var D3D9CmdType = /* @__PURE__ */ ((D3D9CmdType2) => {
    D3D9CmdType2[D3D9CmdType2["NOP"] = 0] = "NOP";
    D3D9CmdType2[D3D9CmdType2["CLEAR"] = 1] = "CLEAR";
    D3D9CmdType2[D3D9CmdType2["BEGIN_SCENE"] = 2] = "BEGIN_SCENE";
    D3D9CmdType2[D3D9CmdType2["END_SCENE"] = 3] = "END_SCENE";
    D3D9CmdType2[D3D9CmdType2["PRESENT"] = 4] = "PRESENT";
    D3D9CmdType2[D3D9CmdType2["SET_RENDER_STATE"] = 5] = "SET_RENDER_STATE";
    D3D9CmdType2[D3D9CmdType2["SET_SAMPLER_STATE"] = 6] = "SET_SAMPLER_STATE";
    D3D9CmdType2[D3D9CmdType2["SET_TEXTURE"] = 7] = "SET_TEXTURE";
    D3D9CmdType2[D3D9CmdType2["SET_TRANSFORM"] = 8] = "SET_TRANSFORM";
    D3D9CmdType2[D3D9CmdType2["SET_VIEWPORT"] = 9] = "SET_VIEWPORT";
    D3D9CmdType2[D3D9CmdType2["SET_STREAM_SOURCE"] = 10] = "SET_STREAM_SOURCE";
    D3D9CmdType2[D3D9CmdType2["SET_INDICES"] = 11] = "SET_INDICES";
    D3D9CmdType2[D3D9CmdType2["DRAW_PRIMITIVE"] = 12] = "DRAW_PRIMITIVE";
    D3D9CmdType2[D3D9CmdType2["DRAW_INDEXED_PRIMITIVE"] = 13] = "DRAW_INDEXED_PRIMITIVE";
    D3D9CmdType2[D3D9CmdType2["CREATE_VERTEX_BUFFER"] = 14] = "CREATE_VERTEX_BUFFER";
    D3D9CmdType2[D3D9CmdType2["CREATE_INDEX_BUFFER"] = 15] = "CREATE_INDEX_BUFFER";
    D3D9CmdType2[D3D9CmdType2["CREATE_TEXTURE"] = 16] = "CREATE_TEXTURE";
    D3D9CmdType2[D3D9CmdType2["UPDATE_TEXTURE"] = 17] = "UPDATE_TEXTURE";
    D3D9CmdType2[D3D9CmdType2["DESTROY_RESOURCE"] = 18] = "DESTROY_RESOURCE";
    D3D9CmdType2[D3D9CmdType2["SET_VERTEX_DECLARATION"] = 19] = "SET_VERTEX_DECLARATION";
    D3D9CmdType2[D3D9CmdType2["SET_VERTEX_SHADER"] = 20] = "SET_VERTEX_SHADER";
    D3D9CmdType2[D3D9CmdType2["SET_PIXEL_SHADER"] = 21] = "SET_PIXEL_SHADER";
    D3D9CmdType2[D3D9CmdType2["SET_VS_CONSTANTS"] = 22] = "SET_VS_CONSTANTS";
    D3D9CmdType2[D3D9CmdType2["SET_PS_CONSTANTS"] = 23] = "SET_PS_CONSTANTS";
    D3D9CmdType2[D3D9CmdType2["SET_SCISSOR_RECT"] = 24] = "SET_SCISSOR_RECT";
    D3D9CmdType2[D3D9CmdType2["COUNT"] = 25] = "COUNT";
    return D3D9CmdType2;
  })(D3D9CmdType || {});
  const D3DCLEAR_TARGET = 1;
  const D3DCLEAR_ZBUFFER = 2;
  const D3DCLEAR_STENCIL = 4;
  const D3DRS_ZENABLE = 7;
  const D3DRS_ZWRITEENABLE = 14;
  const D3DRS_SRCBLEND = 19;
  const D3DRS_DESTBLEND = 20;
  const D3DRS_CULLMODE = 22;
  const D3DRS_ZFUNC = 23;
  const D3DRS_ALPHABLENDENABLE = 27;
  const D3DRS_COLORWRITEENABLE = 168;
  const D3DZB_FALSE = 0;
  const D3DZB_TRUE = 1;
  const D3DZB_USEW = 2;
  const D3DCMP_NEVER = 1;
  const D3DCMP_LESS = 2;
  const D3DCMP_EQUAL = 3;
  const D3DCMP_LESSEQUAL = 4;
  const D3DCMP_GREATER = 5;
  const D3DCMP_NOTEQUAL = 6;
  const D3DCMP_GREATEREQUAL = 7;
  const D3DCMP_ALWAYS = 8;
  const D3DCULL_NONE = 1;
  const D3DCULL_CW = 2;
  const D3DCULL_CCW = 3;
  const D3DBLEND_ZERO = 1;
  const D3DBLEND_ONE = 2;
  const D3DBLEND_SRCCOLOR = 3;
  const D3DBLEND_INVSRCCOLOR = 4;
  const D3DBLEND_SRCALPHA = 5;
  const D3DBLEND_INVSRCALPHA = 6;
  const D3DBLEND_DESTALPHA = 7;
  const D3DBLEND_INVDESTALPHA = 8;
  const D3DBLEND_DESTCOLOR = 9;
  const D3DBLEND_INVDESTCOLOR = 10;
  const D3DBLEND_SRCALPHASAT = 11;
  const D3DBLEND_BOTHSRCALPHA = 12;
  const D3DBLEND_BOTHINVSRCALPHA = 13;
  const D3DBLEND_BLENDFACTOR = 14;
  const D3DBLEND_INVBLENDFACTOR = 15;
  const D3DCOLORWRITEENABLE_RED = 1;
  const D3DCOLORWRITEENABLE_GREEN = 2;
  const D3DCOLORWRITEENABLE_BLUE = 4;
  const D3DCOLORWRITEENABLE_ALPHA = 8;
  var SceneState = /* @__PURE__ */ ((SceneState2) => {
    SceneState2[SceneState2["IDLE"] = 0] = "IDLE";
    SceneState2[SceneState2["IN_SCENE"] = 1] = "IN_SCENE";
    return SceneState2;
  })(SceneState || {});
  class D3D9CommandConsumer {
    view;
    u8;
    ringBase;
    gl;
    onPresent;
    sceneState = 0 /* IDLE */;
    presentedFrames = 0;
    totalCommandsExecuted = 0;
    lastClear = null;
    // Active Viewport and Render States (initialized to authentic Direct3D 9 defaults)
    viewport = {
      x: 0,
      y: 0,
      width: 1280,
      height: 720,
      minZ: 0,
      maxZ: 1,
      glX: 0,
      glY: 0,
      glWidth: 1280,
      glHeight: 720
    };
    renderStates = {
      zEnable: true,
      // D3D9 default: D3DZB_TRUE (1)
      zWriteEnable: true,
      // D3D9 default: TRUE (1)
      zFunc: D3DCMP_LESSEQUAL,
      // D3D9 default: D3DCMP_LESSEQUAL (4)
      cullMode: D3DCULL_CCW,
      // D3D9 default: D3DCULL_CCW (3)
      alphaBlendEnable: false,
      // D3D9 default: FALSE (0)
      srcBlend: D3DBLEND_ONE,
      // D3D9 default: D3DBLEND_ONE (2)
      destBlend: D3DBLEND_ZERO,
      // D3D9 default: D3DBLEND_ZERO (1)
      colorWriteEnable: 15
      // D3D9 default: 0xF (R|G|B|A enabled)
    };
    constructor(buffer, byteOffset = 0, options = {}) {
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
      if (this.gl) {
        this.applyInitialWebGLDefaults();
      }
    }
    applyInitialWebGLDefaults() {
      const gl = this.gl;
      if (!gl) return;
      const canvasH = gl.canvas?.height ?? 720;
      const canvasW = gl.canvas?.width ?? 1280;
      this.viewport = {
        x: 0,
        y: 0,
        width: canvasW,
        height: canvasH,
        minZ: 0,
        maxZ: 1,
        glX: 0,
        glY: 0,
        glWidth: canvasW,
        glHeight: canvasH
      };
      gl.viewport(0, 0, canvasW, canvasH);
      gl.depthRange(0, 1);
      gl.enable(gl.DEPTH_TEST);
      gl.depthMask(true);
      gl.depthFunc(gl.LEQUAL);
      gl.enable(gl.CULL_FACE);
      gl.frontFace(gl.CW);
      gl.cullFace(gl.BACK);
      gl.disable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ZERO);
      gl.colorMask(true, true, true, true);
    }
    validateRingHeader() {
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
    getPendingBytes() {
      const { head, tail, capacity } = this.validateRingHeader();
      if (head >= tail) {
        return head - tail;
      }
      return capacity - (tail - head);
    }
    readBytesCircular(dest, srcRingOffset, count, capacity) {
      const dataStart = this.ringBase + D3D9_RING_HEADER_SIZE;
      for (let i = 0; i < count; i++) {
        dest[i] = this.u8[dataStart + (srcRingOffset + i) % capacity];
      }
    }
    mapGlBlendFactor(factor, gl) {
      switch (factor) {
        case D3DBLEND_ZERO:
          return gl.ZERO;
        case D3DBLEND_ONE:
          return gl.ONE;
        case D3DBLEND_SRCCOLOR:
          return gl.SRC_COLOR;
        case D3DBLEND_INVSRCCOLOR:
          return gl.ONE_MINUS_SRC_COLOR;
        case D3DBLEND_SRCALPHA:
          return gl.SRC_ALPHA;
        case D3DBLEND_INVSRCALPHA:
          return gl.ONE_MINUS_SRC_ALPHA;
        case D3DBLEND_DESTALPHA:
          return gl.DST_ALPHA;
        case D3DBLEND_INVDESTALPHA:
          return gl.ONE_MINUS_DST_ALPHA;
        case D3DBLEND_DESTCOLOR:
          return gl.DST_COLOR;
        case D3DBLEND_INVDESTCOLOR:
          return gl.ONE_MINUS_DST_COLOR;
        case D3DBLEND_SRCALPHASAT:
          return gl.SRC_ALPHA_SATURATE;
        case D3DBLEND_BLENDFACTOR:
          return gl.CONSTANT_COLOR;
        case D3DBLEND_INVBLENDFACTOR:
          return gl.ONE_MINUS_CONSTANT_COLOR;
        default:
          throw new Error(`Unsupported blend factor: ${factor}`);
      }
    }
    mapGlCmpFunc(func, gl) {
      switch (func) {
        case D3DCMP_NEVER:
          return gl.NEVER;
        case D3DCMP_LESS:
          return gl.LESS;
        case D3DCMP_EQUAL:
          return gl.EQUAL;
        case D3DCMP_LESSEQUAL:
          return gl.LEQUAL;
        case D3DCMP_GREATER:
          return gl.GREATER;
        case D3DCMP_NOTEQUAL:
          return gl.NOTEQUAL;
        case D3DCMP_GREATEREQUAL:
          return gl.GEQUAL;
        case D3DCMP_ALWAYS:
          return gl.ALWAYS;
        default:
          throw new Error(`Unsupported comparison function: ${func}`);
      }
    }
    applyRenderState(state, value) {
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
              gl.cullFace(gl.FRONT);
            }
          } else if (value === D3DCULL_CCW) {
            this.renderStates.cullMode = D3DCULL_CCW;
            if (gl) {
              gl.enable(gl.CULL_FACE);
              gl.frontFace(gl.CW);
              gl.cullFace(gl.BACK);
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
          if (value < D3DBLEND_ZERO || value > D3DBLEND_INVBLENDFACTOR || value === D3DBLEND_BOTHSRCALPHA || value === D3DBLEND_BOTHINVSRCALPHA) {
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
          if (value < D3DBLEND_ZERO || value > D3DBLEND_INVBLENDFACTOR || value === D3DBLEND_BOTHSRCALPHA || value === D3DBLEND_BOTHINVSRCALPHA) {
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
          if (value < 0 || (value & ~15) !== 0) {
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
    processCommands() {
      const executed = [];
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
        this.readBytesCircular(hdrBuf, tail, 8, capacity);
        const cmdType = hdrView.getUint16(0, true);
        const flags = hdrView.getUint16(2, true);
        const payloadBytes = hdrView.getUint32(4, true);
        if (cmdType >= 25 /* COUNT */) {
          throw new Error(
            `Invalid command opcode: ${cmdType} (maximum known opcode is ${25 /* COUNT */ - 1})`
          );
        }
        const alignedPayload = payloadBytes + 3 & ~3;
        const packetSize = 8 + alignedPayload;
        if (packetSize > pending) {
          throw new Error(
            `Truncated command packet for opcode ${cmdType}: ${packetSize} bytes required, ${pending} available`
          );
        }
        let payloadBuf = null;
        let payloadView = null;
        if (alignedPayload > 0) {
          payloadBuf = new Uint8Array(alignedPayload);
          this.readBytesCircular(payloadBuf, (tail + 8) % capacity, alignedPayload, capacity);
          payloadView = new DataView(payloadBuf.buffer);
        }
        let cmd;
        switch (cmdType) {
          case 0 /* NOP */: {
            cmd = { type: 0 /* NOP */ };
            break;
          }
          case 2 /* BEGIN_SCENE */: {
            if (this.sceneState === 1 /* IN_SCENE */) {
              throw new Error(
                "Invalid state transition: BEGIN_SCENE called while already IN_SCENE"
              );
            }
            this.sceneState = 1 /* IN_SCENE */;
            cmd = { type: 2 /* BEGIN_SCENE */ };
            break;
          }
          case 3 /* END_SCENE */: {
            if (this.sceneState !== 1 /* IN_SCENE */) {
              throw new Error(
                "Invalid state transition: END_SCENE called while IDLE"
              );
            }
            this.sceneState = 0 /* IDLE */;
            cmd = { type: 3 /* END_SCENE */ };
            break;
          }
          case 1 /* CLEAR */: {
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
            const a = (color >>> 24 & 255) / 255;
            const r = (color >>> 16 & 255) / 255;
            const g = (color >>> 8 & 255) / 255;
            const b = (color & 255) / 255;
            if (this.gl) {
              const gl = this.gl;
              let mask = 0;
              const needsColorMaskOverride = (clearFlags & D3DCLEAR_TARGET) !== 0 && this.renderStates.colorWriteEnable !== 15;
              const needsDepthMaskOverride = (clearFlags & D3DCLEAR_ZBUFFER) !== 0 && !this.renderStates.zWriteEnable;
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
                gl.stencilMask(4294967295);
              }
              if (mask !== 0) {
                const canvasH = gl.canvas?.height ?? 0;
                const canvasW = gl.canvas?.width ?? 0;
                const isSubViewport = this.viewport && (this.viewport.glX !== 0 || this.viewport.glY !== 0 || this.viewport.glWidth !== canvasW || this.viewport.glHeight !== canvasH);
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
            const clearCmd = {
              type: 1 /* CLEAR */,
              flags: clearFlags,
              color,
              r,
              g,
              b,
              a,
              z,
              stencil,
              count
            };
            this.lastClear = clearCmd;
            cmd = clearCmd;
            break;
          }
          case 4 /* PRESENT */: {
            if (this.sceneState === 1 /* IN_SCENE */) {
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
                h: payloadView.getUint32(12, true)
              };
            }
            this.presentedFrames++;
            const presCmd = {
              type: 4 /* PRESENT */,
              srcRect
            };
            if (this.onPresent) {
              this.onPresent(this.presentedFrames, presCmd);
            }
            cmd = presCmd;
            break;
          }
          case 9 /* SET_VIEWPORT */: {
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
            if (minZ < 0 || minZ > 1 || maxZ < 0 || maxZ > 1 || minZ > maxZ) {
              throw new Error(
                `Invalid viewport depth range: [${minZ}, ${maxZ}] (must be within [0.0, 1.0] with minZ <= maxZ)`
              );
            }
            const targetH = this.gl && this.gl.canvas ? this.gl.canvas.height : this.viewport?.height || 720;
            const glX = x;
            const glY = targetH - (y + height);
            const glWidth = width;
            const glHeight = height;
            if (this.gl) {
              this.gl.viewport(glX, glY, glWidth, glHeight);
              this.gl.depthRange(minZ, maxZ);
            }
            const vp = {
              x,
              y,
              width,
              height,
              minZ,
              maxZ,
              glX,
              glY,
              glWidth,
              glHeight
            };
            this.viewport = vp;
            cmd = { type: 9 /* SET_VIEWPORT */, ...vp };
            break;
          }
          case 5 /* SET_RENDER_STATE */: {
            if (!payloadView || payloadBytes < 8) {
              throw new Error(
                `Truncated SET_RENDER_STATE payload: expected 8 bytes, got ${payloadBytes}`
              );
            }
            const state = payloadView.getUint32(0, true);
            const value = payloadView.getUint32(4, true);
            this.applyRenderState(state, value);
            cmd = { type: 5 /* SET_RENDER_STATE */, state, value };
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
        const newTail = (tail + packetSize) % capacity;
        this.view.setUint32(this.ringBase + 12, newTail, true);
      }
      return executed;
    }
  }
  class D3D9CommandProducer {
    view;
    u8;
    ringBase;
    constructor(buffer, byteOffset = 0) {
      this.ringBase = byteOffset;
      this.view = new DataView(buffer);
      this.u8 = new Uint8Array(buffer);
    }
    static initRing(buffer, byteOffset = 0, capacity = 4 * 1024 * 1024) {
      if (buffer.byteLength < byteOffset + D3D9_RING_HEADER_SIZE + capacity) {
        throw new Error("Buffer too small for requested ring capacity and header");
      }
      const view = new DataView(buffer);
      view.setUint32(byteOffset + 0, D3D9_RING_MAGIC, true);
      view.setUint32(byteOffset + 4, D3D9_RING_VERSION, true);
      view.setUint32(byteOffset + 8, 0, true);
      view.setUint32(byteOffset + 12, 0, true);
      view.setUint32(byteOffset + 16, capacity, true);
      view.setUint32(byteOffset + 20, 0, true);
      view.setUint32(byteOffset + 24, 0, true);
      view.setUint32(byteOffset + 28, 1, true);
      for (let i = 0; i < 8; i++) {
        view.setUint32(byteOffset + 32 + i * 4, 0, true);
      }
      return new D3D9CommandProducer(buffer, byteOffset);
    }
    writeBytesCircular(src, dstRingOffset, count, capacity) {
      const dataStart = this.ringBase + D3D9_RING_HEADER_SIZE;
      for (let i = 0; i < count; i++) {
        this.u8[dataStart + (dstRingOffset + i) % capacity] = src[i];
      }
    }
    emitRawPacket(cmdType, flags, payload) {
      const head = this.view.getUint32(this.ringBase + 8, true);
      const tail = this.view.getUint32(this.ringBase + 12, true);
      const capacity = this.view.getUint32(this.ringBase + 16, true);
      const payloadBytes = payload ? payload.byteLength : 0;
      const alignedPayload = payloadBytes + 3 & ~3;
      const packetSize = 8 + alignedPayload;
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
    emitBeginScene() {
      this.emitRawPacket(2 /* BEGIN_SCENE */, 0, null);
    }
    emitEndScene() {
      this.emitRawPacket(3 /* END_SCENE */, 0, null);
    }
    emitClear(flags, color, z, stencil, count = 0) {
      const payload = new Uint8Array(20);
      const v = new DataView(payload.buffer);
      v.setUint32(0, flags, true);
      v.setUint32(4, color, true);
      v.setFloat32(8, z, true);
      v.setUint32(12, stencil, true);
      v.setUint32(16, count, true);
      this.emitRawPacket(1 /* CLEAR */, 0, payload);
    }
    emitPresent(x = 0, y = 0, w = 0, h = 0) {
      const payload = new Uint8Array(16);
      const v = new DataView(payload.buffer);
      v.setUint32(0, x, true);
      v.setUint32(4, y, true);
      v.setUint32(8, w, true);
      v.setUint32(12, h, true);
      this.emitRawPacket(4 /* PRESENT */, 0, payload);
      const frameIndex = this.view.getUint32(this.ringBase + 20, true);
      this.view.setUint32(this.ringBase + 20, frameIndex + 1, true);
    }
    emitSetViewport(x, y, width, height, minZ = 0, maxZ = 1) {
      const payload = new Uint8Array(24);
      const v = new DataView(payload.buffer);
      v.setUint32(0, x, true);
      v.setUint32(4, y, true);
      v.setUint32(8, width, true);
      v.setUint32(12, height, true);
      v.setFloat32(16, minZ, true);
      v.setFloat32(20, maxZ, true);
      this.emitRawPacket(9 /* SET_VIEWPORT */, 0, payload);
    }
    emitSetRenderState(state, value) {
      const payload = new Uint8Array(8);
      const v = new DataView(payload.buffer);
      v.setUint32(0, state, true);
      v.setUint32(4, value, true);
      this.emitRawPacket(5 /* SET_RENDER_STATE */, 0, payload);
    }
  }
  return __toCommonJS(d3d9_consumer_exports);
})();
