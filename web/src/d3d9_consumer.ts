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
  UPDATE_VERTEX_BUFFER = 25,
  DESTROY_VERTEX_BUFFER = 26,
  UPDATE_INDEX_BUFFER = 27,
  DESTROY_INDEX_BUFFER = 28,
  CREATE_VERTEX_DECLARATION = 29,
  COUNT = 30,
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

// Direct3D 9 Resource Usage Flags (D3DUSAGE)
export const D3DUSAGE_WRITEONLY = 0x00000008;
export const D3DUSAGE_DYNAMIC = 0x00000200;

// Direct3D 9 Memory Pools (D3DPOOL)
export const D3DPOOL_DEFAULT = 0;
export const D3DPOOL_MANAGED = 1;
export const D3DPOOL_SYSTEMMEM = 2;
export const D3DPOOL_SCRATCH = 3;

// Direct3D 9 Formats (D3DFORMAT)
export const D3DFMT_A8R8G8B8 = 21;
export const D3DFMT_X8R8G8B8 = 22;
export const D3DFMT_A8B8G8R8 = 32;
export const D3DFMT_L8 = 50;
export const D3DFMT_INDEX16 = 101;
export const D3DFMT_INDEX32 = 102;
export const D3DFMT_DXT1 = 0x31545844; // 'DXT1'
export const D3DFMT_DXT3 = 0x33545844; // 'DXT3'
export const D3DFMT_DXT5 = 0x35545844; // 'DXT5'

// Direct3D 9 Primitive Types (D3DPRIMITIVETYPE)
export const D3DPT_POINTLIST = 1;
export const D3DPT_LINELIST = 2;
export const D3DPT_LINESTRIP = 3;
export const D3DPT_TRIANGLELIST = 4;
export const D3DPT_TRIANGLESTRIP = 5;
export const D3DPT_TRIANGLEFAN = 6;

// Direct3D 9 Vertex Element Types (D3DDECLTYPE)
export const D3DDECLTYPE_FLOAT1 = 0;
export const D3DDECLTYPE_FLOAT2 = 1;
export const D3DDECLTYPE_FLOAT3 = 2;
export const D3DDECLTYPE_FLOAT4 = 3;
export const D3DDECLTYPE_D3DCOLOR = 4;
export const D3DDECLTYPE_UBYTE4 = 5;
export const D3DDECLTYPE_SHORT2 = 6;
export const D3DDECLTYPE_SHORT4 = 7;
export const D3DDECLTYPE_UBYTE4N = 8;
export const D3DDECLTYPE_SHORT2N = 9;
export const D3DDECLTYPE_SHORT4N = 10;
export const D3DDECLTYPE_USHORT2N = 11;
export const D3DDECLTYPE_USHORT4N = 12;
export const D3DDECLTYPE_FLOAT16_2 = 15;
export const D3DDECLTYPE_FLOAT16_4 = 16;
export const D3DDECLTYPE_UNUSED = 17;

// Direct3D 9 Vertex Element Usages (D3DDECLUSAGE)
export const D3DDECLUSAGE_POSITION = 0;
export const D3DDECLUSAGE_BLENDWEIGHT = 1;
export const D3DDECLUSAGE_BLENDINDICES = 2;
export const D3DDECLUSAGE_NORMAL = 3;
export const D3DDECLUSAGE_PSIZE = 4;
export const D3DDECLUSAGE_TEXCOORD = 5;
export const D3DDECLUSAGE_TANGENT = 6;
export const D3DDECLUSAGE_BINORMAL = 7;
export const D3DDECLUSAGE_TESSFACTOR = 8;
export const D3DDECLUSAGE_POSITIONT = 9;
export const D3DDECLUSAGE_COLOR = 10;
export const D3DDECLUSAGE_FOG = 11;
export const D3DDECLUSAGE_DEPTH = 12;
export const D3DDECLUSAGE_SAMPLE = 13;

// Direct3D 9 Sampler State Types (D3DSAMPLERSTATETYPE)
export const D3DSAMP_ADDRESSU = 1;
export const D3DSAMP_ADDRESSV = 2;
export const D3DSAMP_ADDRESSW = 3;
export const D3DSAMP_BORDERCOLOR = 4;
export const D3DSAMP_MAGFILTER = 5;
export const D3DSAMP_MINFILTER = 6;
export const D3DSAMP_MIPFILTER = 7;
export const D3DSAMP_MAXANISOTROPY = 10;

// Direct3D 9 Texture Address Modes (D3DTEXTUREADDRESS)
export const D3DTADDRESS_WRAP = 1;
export const D3DTADDRESS_MIRROR = 2;
export const D3DTADDRESS_CLAMP = 3;
export const D3DTADDRESS_BORDER = 4;

// Direct3D 9 Texture Filter Types (D3DTEXTUREFILTERTYPE)
export const D3DTEXF_NONE = 0;
export const D3DTEXF_POINT = 1;
export const D3DTEXF_LINEAR = 2;
export const D3DTEXF_ANISOTROPIC = 3;

// Direct3D 9 Limits
export const D3D9_MAX_STREAMS = 16;
export const D3D9_MAX_SAMPLERS = 16;

// WebGL2 Constants
export const GL_STATIC_DRAW = 0x88e4;
export const GL_DYNAMIC_DRAW = 0x88e8;
export const GL_BYTE = 0x1400;
export const GL_UNSIGNED_BYTE = 0x1401;
export const GL_SHORT = 0x1402;
export const GL_UNSIGNED_SHORT = 0x1403;
export const GL_UNSIGNED_INT = 0x1405;
export const GL_FLOAT = 0x1406;
export const GL_HALF_FLOAT = 0x140b;
export const GL_POINTS = 0x0000;
export const GL_LINES = 0x0001;
export const GL_LINE_STRIP = 0x0003;
export const GL_TRIANGLES = 0x0004;
export const GL_TRIANGLE_STRIP = 0x0005;
export const GL_TRIANGLE_FAN = 0x0006;
export const GL_NEAREST = 0x2600;
export const GL_LINEAR = 0x2601;
export const GL_NEAREST_MIPMAP_NEAREST = 0x2700;
export const GL_LINEAR_MIPMAP_NEAREST = 0x2701;
export const GL_NEAREST_MIPMAP_LINEAR = 0x2702;
export const GL_LINEAR_MIPMAP_LINEAR = 0x2703;
export const GL_REPEAT = 0x2901;
export const GL_CLAMP_TO_EDGE = 0x812f;
export const GL_MIRRORED_REPEAT = 0x8370;

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

export interface D3D9CreateVertexBufferCommand {
  type: D3D9CmdType.CREATE_VERTEX_BUFFER;
  bufferId: number;
  length: number;
  usage: number;
  fvf: number;
  pool: number;
}

export interface D3D9UpdateVertexBufferCommand {
  type: D3D9CmdType.UPDATE_VERTEX_BUFFER;
  bufferId: number;
  offset: number;
  size: number;
  data: Uint8Array;
}

export interface D3D9SetStreamSourceCommand {
  type: D3D9CmdType.SET_STREAM_SOURCE;
  streamNumber: number;
  bufferId: number;
  offset: number;
  stride: number;
}

export interface D3D9DestroyVertexBufferCommand {
  type: D3D9CmdType.DESTROY_VERTEX_BUFFER;
  bufferId: number;
}

export interface D3D9CreateIndexBufferCommand {
  type: D3D9CmdType.CREATE_INDEX_BUFFER;
  bufferId: number;
  length: number;
  usage: number;
  format: number;
  pool: number;
}

export interface D3D9UpdateIndexBufferCommand {
  type: D3D9CmdType.UPDATE_INDEX_BUFFER;
  bufferId: number;
  offset: number;
  size: number;
  data: Uint8Array;
}

export interface D3D9SetIndicesCommand {
  type: D3D9CmdType.SET_INDICES;
  bufferId: number;
}

export interface D3D9DestroyIndexBufferCommand {
  type: D3D9CmdType.DESTROY_INDEX_BUFFER;
  bufferId: number;
}

export interface D3D9VertexElement {
  stream: number;
  offset: number;
  type: number;
  method: number;
  usage: number;
  usageIndex: number;
}

export interface D3D9CreateVertexDeclarationCommand {
  type: D3D9CmdType.CREATE_VERTEX_DECLARATION;
  declId: number;
  elements: D3D9VertexElement[];
}

export interface D3D9SetVertexDeclarationCommand {
  type: D3D9CmdType.SET_VERTEX_DECLARATION;
  declId: number;
}

export interface D3D9CreateTextureCommand {
  type: D3D9CmdType.CREATE_TEXTURE;
  textureId: number;
  width: number;
  height: number;
  levels: number;
  usage: number;
  format: number;
  pool: number;
}

export interface D3D9UpdateTextureCommand {
  type: D3D9CmdType.UPDATE_TEXTURE;
  textureId: number;
  level: number;
  pitch: number;
  dataBytes: number;
  width: number;
  height: number;
  rgbaData: Uint8Array;
}

export interface D3D9SetTextureCommand {
  type: D3D9CmdType.SET_TEXTURE;
  stage: number;
  textureId: number;
}

export interface D3D9SetSamplerStateCommand {
  type: D3D9CmdType.SET_SAMPLER_STATE;
  sampler: number;
  stateType: number;
  value: number;
}

export interface D3D9DrawPrimitiveCommand {
  type: D3D9CmdType.DRAW_PRIMITIVE;
  primitiveType: number;
  startVertex: number;
  primitiveCount: number;
  glMode: number;
  vertexCount: number;
}

export interface D3D9DrawIndexedPrimitiveCommand {
  type: D3D9CmdType.DRAW_INDEXED_PRIMITIVE;
  primitiveType: number;
  baseVertexIndex: number;
  minVertexIndex: number;
  numVertices: number;
  startIndex: number;
  primitiveCount: number;
  glMode: number;
  vertexCount: number;
  glIndexType: number;
  indexByteOffset: number;
}

export interface D3D9DestroyResourceCommand {
  type: D3D9CmdType.DESTROY_RESOURCE;
  resourceType: number;
  resourceId: number;
}

export type D3D9Command =
  | D3D9ClearCommand
  | D3D9PresentCommand
  | D3D9BeginSceneCommand
  | D3D9EndSceneCommand
  | D3D9NopCommand
  | D3D9SetViewportCommand
  | D3D9SetRenderStateCommand
  | D3D9CreateVertexBufferCommand
  | D3D9UpdateVertexBufferCommand
  | D3D9SetStreamSourceCommand
  | D3D9DestroyVertexBufferCommand
  | D3D9CreateIndexBufferCommand
  | D3D9UpdateIndexBufferCommand
  | D3D9SetIndicesCommand
  | D3D9DestroyIndexBufferCommand
  | D3D9CreateVertexDeclarationCommand
  | D3D9SetVertexDeclarationCommand
  | D3D9CreateTextureCommand
  | D3D9UpdateTextureCommand
  | D3D9SetTextureCommand
  | D3D9SetSamplerStateCommand
  | D3D9DrawPrimitiveCommand
  | D3D9DrawIndexedPrimitiveCommand
  | D3D9DestroyResourceCommand;

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

export interface D3D9VertexBufferEntry {
  bufferId: number;
  glBuffer: WebGLBuffer | null;
  length: number;
  usage: number;
  fvf: number;
  pool: number;
  glUsage: number;
  shadowData: Uint8Array;
}

export interface D3D9IndexBufferEntry {
  bufferId: number;
  glBuffer: WebGLBuffer | null;
  length: number;
  usage: number;
  format: number;
  pool: number;
  glUsage: number;
  glIndexType: number;
  bytesPerIndex: number;
  shadowData: Uint8Array;
}

export interface D3D9StreamSourceBinding {
  streamNumber: number;
  bufferId: number;
  offset: number;
  stride: number;
}

export interface D3D9VertexElementSpec {
  size: number;
  glType: number;
  normalized: boolean;
  byteSize: number;
}

export interface D3D9VertexDeclarationEntry {
  declId: number;
  elements: (D3D9VertexElement & { spec: D3D9VertexElementSpec })[];
}

export interface D3D9TextureEntry {
  textureId: number;
  glTexture: WebGLTexture | null;
  width: number;
  height: number;
  levels: number;
  usage: number;
  format: number;
  pool: number;
  levelData: Map<number, Uint8Array>;
}

export interface D3D9SamplerState {
  addressU: number;
  addressV: number;
  addressW: number;
  magFilter: number;
  minFilter: number;
  mipFilter: number;
  maxAnisotropy: number;
  glWrapS: number;
  glWrapT: number;
  glMagFilter: number;
  glMinFilter: number;
}

/**
 * Software decompression helpers for BC1 (DXT1), BC2 (DXT3), and BC3 (DXT5) blocks to RGBA8.
 */
function unpackRgb565(c: number): [number, number, number] {
  const r5 = (c >>> 11) & 0x1f;
  const g6 = (c >>> 5) & 0x3f;
  const b5 = c & 0x1f;
  return [
    (r5 << 3) | (r5 >>> 2),
    (g6 << 2) | (g6 >>> 4),
    (b5 << 3) | (b5 >>> 2),
  ];
}

function decodeDxtColorBlock(
  src: Uint8Array,
  srcOffset: number,
  isDxt1: boolean
): [number, number, number, number][] {
  const c0 = src[srcOffset] | (src[srcOffset + 1] << 8);
  const c1 = src[srcOffset + 2] | (src[srcOffset + 3] << 8);
  const [r0, g0, b0] = unpackRgb565(c0);
  const [r1, g1, b1] = unpackRgb565(c1);

  const palette: [number, number, number, number][] = [
    [r0, g0, b0, 255],
    [r1, g1, b1, 255],
    [0, 0, 0, 255],
    [0, 0, 0, 255],
  ];

  if (!isDxt1 || c0 > c1) {
    palette[2] = [
      Math.floor((2 * r0 + r1 + 1) / 3),
      Math.floor((2 * g0 + g1 + 1) / 3),
      Math.floor((2 * b0 + b1 + 1) / 3),
      255,
    ];
    palette[3] = [
      Math.floor((r0 + 2 * r1 + 1) / 3),
      Math.floor((g0 + 2 * g1 + 1) / 3),
      Math.floor((b0 + 2 * b1 + 1) / 3),
      255,
    ];
  } else {
    palette[2] = [
      Math.floor((r0 + r1) / 2),
      Math.floor((g0 + g1) / 2),
      Math.floor((b0 + b1) / 2),
      255,
    ];
    palette[3] = [0, 0, 0, 0];
  }

  return palette;
}

export function convertTextureToRgba8(
  format: number,
  width: number,
  height: number,
  src: Uint8Array
): Uint8Array {
  const dst = new Uint8Array(width * height * 4);

  if (format === D3DFMT_A8R8G8B8 || format === D3DFMT_X8R8G8B8) {
    const pixelCount = width * height;
    const forceOpaque = format === D3DFMT_X8R8G8B8;
    for (let i = 0; i < pixelCount; i++) {
      const si = i * 4;
      const b = src[si] ?? 0;
      const g = src[si + 1] ?? 0;
      const r = src[si + 2] ?? 0;
      const a = forceOpaque ? 255 : (src[si + 3] ?? 255);
      dst[si] = r;
      dst[si + 1] = g;
      dst[si + 2] = b;
      dst[si + 3] = a;
    }
    return dst;
  }

  if (format === D3DFMT_A8B8G8R8) {
    dst.set(src.subarray(0, Math.min(src.byteLength, dst.byteLength)));
    return dst;
  }

  if (format === D3DFMT_L8) {
    const pixelCount = width * height;
    for (let i = 0; i < pixelCount; i++) {
      const lum = src[i] ?? 0;
      const di = i * 4;
      dst[di] = lum;
      dst[di + 1] = lum;
      dst[di + 2] = lum;
      dst[di + 3] = 255;
    }
    return dst;
  }

  if (
    format === D3DFMT_DXT1 ||
    format === D3DFMT_DXT3 ||
    format === D3DFMT_DXT5
  ) {
    const blocksX = Math.max(1, Math.ceil(width / 4));
    const blocksY = Math.max(1, Math.ceil(height / 4));
    const blockBytes = format === D3DFMT_DXT1 ? 8 : 16;
    let blockOffset = 0;

    for (let by = 0; by < blocksY; by++) {
      for (let bx = 0; bx < blocksX; bx++) {
        if (blockOffset + blockBytes > src.byteLength) {
          break;
        }
        const colorOffset =
          format === D3DFMT_DXT1 ? blockOffset : blockOffset + 8;
        const palette = decodeDxtColorBlock(
          src,
          colorOffset,
          format === D3DFMT_DXT1
        );
        const indices =
          (src[colorOffset + 4] |
            (src[colorOffset + 5] << 8) |
            (src[colorOffset + 6] << 16) |
            (src[colorOffset + 7] << 24)) >>>
          0;

        // Decode alpha table for DXT5 if applicable
        const alphaPalette = new Uint8Array(8);
        if (format === D3DFMT_DXT5) {
          const a0 = src[blockOffset];
          const a1 = src[blockOffset + 1];
          alphaPalette[0] = a0;
          alphaPalette[1] = a1;
          if (a0 > a1) {
            for (let k = 1; k <= 6; k++) {
              alphaPalette[k + 1] = Math.floor(
                ((7 - k) * a0 + k * a1 + 3) / 7
              );
            }
          } else {
            for (let k = 1; k <= 4; k++) {
              alphaPalette[k + 1] = Math.floor(
                ((5 - k) * a0 + k * a1 + 2) / 5
              );
            }
            alphaPalette[6] = 0;
            alphaPalette[7] = 255;
          }
        }

        for (let py = 0; py < 4; py++) {
          const y = by * 4 + py;
          if (y >= height) continue;
          for (let px = 0; px < 4; px++) {
            const x = bx * 4 + px;
            if (x >= width) continue;
            const pixelIdx = py * 4 + px;
            const colorIdx = (indices >>> (pixelIdx * 2)) & 0x03;
            const [r, g, b, aDefault] = palette[colorIdx];
            let a = aDefault;

            if (format === D3DFMT_DXT3) {
              const alphaByte = src[blockOffset + (pixelIdx >> 1)];
              const a4 =
                (pixelIdx & 1) === 0 ? alphaByte & 0x0f : alphaByte >>> 4;
              a = (a4 << 4) | a4;
            } else if (format === D3DFMT_DXT5) {
              const bitPos = pixelIdx * 3;
              const bytePos = blockOffset + 2 + (bitPos >> 3);
              const shift = bitPos & 7;
              const raw =
                src[bytePos] | ((src[bytePos + 1] ?? 0) << 8);
              const aIdx = (raw >>> shift) & 0x07;
              a = alphaPalette[aIdx];
            }

            const di = (y * width + x) * 4;
            dst[di] = r;
            dst[di + 1] = g;
            dst[di + 2] = b;
            dst[di + 3] = a;
          }
        }

        blockOffset += blockBytes;
      }
    }
    return dst;
  }

  throw new Error(`Unsupported texture format: 0x${format.toString(16)}`);
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
  public drawCallsExecuted: number = 0;
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

  // Active Resources & Pipeline Bindings (Phase 4.3)
  public vertexBuffers: Map<number, D3D9VertexBufferEntry> = new Map();
  public indexBuffers: Map<number, D3D9IndexBufferEntry> = new Map();
  public streamSources: Map<number, D3D9StreamSourceBinding> = new Map();
  public boundIndexBufferId: number = 0;
  public vertexDeclarations: Map<number, D3D9VertexDeclarationEntry> = new Map();
  public activeVertexDeclarationId: number = 0;
  public textures: Map<number, D3D9TextureEntry> = new Map();
  public textureStages: Map<number, number> = new Map();
  public samplerStates: Map<number, D3D9SamplerState> = new Map();

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

  public dispose(): void {
    if (this.gl) {
      for (const vb of this.vertexBuffers.values()) {
        if (vb.glBuffer) this.gl.deleteBuffer(vb.glBuffer);
      }
      for (const ib of this.indexBuffers.values()) {
        if (ib.glBuffer) this.gl.deleteBuffer(ib.glBuffer);
      }
      for (const tex of this.textures.values()) {
        if (tex.glTexture) this.gl.deleteTexture(tex.glTexture);
      }
    }
    this.vertexBuffers.clear();
    this.indexBuffers.clear();
    this.textures.clear();
    this.streamSources.clear();
    this.vertexDeclarations.clear();
  }

  public getVertexBuffer(bufferId: number): D3D9VertexBufferEntry | undefined {
    return this.vertexBuffers.get(bufferId);
  }

  public getIndexBuffer(bufferId: number): D3D9IndexBufferEntry | undefined {
    return this.indexBuffers.get(bufferId);
  }

  public getStreamSource(streamNumber: number): D3D9StreamSourceBinding | undefined {
    return this.streamSources.get(streamNumber);
  }

  public getVertexDeclaration(declId: number): D3D9VertexDeclarationEntry | undefined {
    return this.vertexDeclarations.get(declId);
  }

  public getTexture(textureId: number): D3D9TextureEntry | undefined {
    return this.textures.get(textureId);
  }

  public getSamplerState(sampler: number): D3D9SamplerState {
    let st = this.samplerStates.get(sampler);
    if (!st) {
      st = {
        addressU: D3DTADDRESS_WRAP,
        addressV: D3DTADDRESS_WRAP,
        addressW: D3DTADDRESS_WRAP,
        magFilter: D3DTEXF_POINT,
        minFilter: D3DTEXF_POINT,
        mipFilter: D3DTEXF_NONE,
        maxAnisotropy: 1,
        glWrapS: GL_REPEAT,
        glWrapT: GL_REPEAT,
        glMagFilter: GL_NEAREST,
        glMinFilter: GL_NEAREST,
      };
      this.samplerStates.set(sampler, st);
    }
    return st;
  }

  private destroyVertexBuffer(bufferId: number): void {
    const entry = this.vertexBuffers.get(bufferId);
    if (!entry) {
      throw new Error(
        `Unknown vertex buffer ID in DESTROY_VERTEX_BUFFER: ${bufferId}`
      );
    }

    if (this.gl && entry.glBuffer) {
      this.gl.deleteBuffer(entry.glBuffer);
    }

    this.vertexBuffers.delete(bufferId);

    // Unbind any stream source slots currently referencing this vertex buffer
    for (const [slot, binding] of this.streamSources.entries()) {
      if (binding.bufferId === bufferId) {
        this.streamSources.set(slot, {
          streamNumber: slot,
          bufferId: 0,
          offset: 0,
          stride: 0,
        });
        if (this.gl && slot === 0) {
          this.gl.bindBuffer(this.gl.ARRAY_BUFFER, null);
        }
      }
    }
  }

  private destroyIndexBuffer(bufferId: number): void {
    const entry = this.indexBuffers.get(bufferId);
    if (!entry) {
      throw new Error(
        `Unknown index buffer ID in DESTROY_INDEX_BUFFER: ${bufferId}`
      );
    }

    if (this.gl && entry.glBuffer) {
      this.gl.deleteBuffer(entry.glBuffer);
    }

    this.indexBuffers.delete(bufferId);

    if (this.boundIndexBufferId === bufferId) {
      this.boundIndexBufferId = 0;
      if (this.gl) {
        this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, null);
      }
    }
  }

  private destroyTexture(textureId: number): void {
    const entry = this.textures.get(textureId);
    if (!entry) {
      throw new Error(`Unknown texture ID in DESTROY_RESOURCE: ${textureId}`);
    }

    if (this.gl && entry.glTexture) {
      this.gl.deleteTexture(entry.glTexture);
    }

    this.textures.delete(textureId);

    for (const [stage, boundId] of this.textureStages.entries()) {
      if (boundId === textureId) {
        this.textureStages.set(stage, 0);
        if (this.gl) {
          this.gl.activeTexture(this.gl.TEXTURE0 + stage);
          this.gl.bindTexture(this.gl.TEXTURE_2D, null);
        }
      }
    }
  }

  private destroyVertexDeclaration(declId: number): void {
    if (!this.vertexDeclarations.has(declId)) {
      throw new Error(
        `Unknown vertex declaration ID in DESTROY_RESOURCE: ${declId}`
      );
    }
    this.vertexDeclarations.delete(declId);
    if (this.activeVertexDeclarationId === declId) {
      this.activeVertexDeclarationId = 0;
    }
  }

  private mapDeclElementType(declType: number): D3D9VertexElementSpec {
    switch (declType) {
      case D3DDECLTYPE_FLOAT1:
        return { size: 1, glType: GL_FLOAT, normalized: false, byteSize: 4 };
      case D3DDECLTYPE_FLOAT2:
        return { size: 2, glType: GL_FLOAT, normalized: false, byteSize: 8 };
      case D3DDECLTYPE_FLOAT3:
        return { size: 3, glType: GL_FLOAT, normalized: false, byteSize: 12 };
      case D3DDECLTYPE_FLOAT4:
        return { size: 4, glType: GL_FLOAT, normalized: false, byteSize: 16 };
      case D3DDECLTYPE_D3DCOLOR:
        return { size: 4, glType: GL_UNSIGNED_BYTE, normalized: true, byteSize: 4 };
      case D3DDECLTYPE_UBYTE4:
        return { size: 4, glType: GL_UNSIGNED_BYTE, normalized: false, byteSize: 4 };
      case D3DDECLTYPE_SHORT2:
        return { size: 2, glType: GL_SHORT, normalized: false, byteSize: 4 };
      case D3DDECLTYPE_SHORT4:
        return { size: 4, glType: GL_SHORT, normalized: false, byteSize: 8 };
      case D3DDECLTYPE_UBYTE4N:
        return { size: 4, glType: GL_UNSIGNED_BYTE, normalized: true, byteSize: 4 };
      case D3DDECLTYPE_SHORT2N:
        return { size: 2, glType: GL_SHORT, normalized: true, byteSize: 4 };
      case D3DDECLTYPE_SHORT4N:
        return { size: 4, glType: GL_SHORT, normalized: true, byteSize: 8 };
      case D3DDECLTYPE_USHORT2N:
        return { size: 2, glType: GL_UNSIGNED_SHORT, normalized: true, byteSize: 4 };
      case D3DDECLTYPE_USHORT4N:
        return { size: 4, glType: GL_UNSIGNED_SHORT, normalized: true, byteSize: 8 };
      case D3DDECLTYPE_FLOAT16_2:
        return { size: 2, glType: GL_HALF_FLOAT, normalized: false, byteSize: 4 };
      case D3DDECLTYPE_FLOAT16_4:
        return { size: 4, glType: GL_HALF_FLOAT, normalized: false, byteSize: 8 };
      default:
        throw new Error(`Unsupported D3DDECLTYPE: ${declType}`);
    }
  }

  private mapGlWrapMode(addrMode: number): number {
    switch (addrMode) {
      case D3DTADDRESS_WRAP:
        return GL_REPEAT;
      case D3DTADDRESS_MIRROR:
        return GL_MIRRORED_REPEAT;
      case D3DTADDRESS_CLAMP:
      case D3DTADDRESS_BORDER:
        return GL_CLAMP_TO_EDGE;
      default:
        throw new Error(`Unsupported texture address mode: ${addrMode}`);
    }
  }

  private updateSamplerGlFilters(st: D3D9SamplerState): void {
    if (st.magFilter === D3DTEXF_POINT || st.magFilter === D3DTEXF_NONE) {
      st.glMagFilter = GL_NEAREST;
    } else if (
      st.magFilter === D3DTEXF_LINEAR ||
      st.magFilter === D3DTEXF_ANISOTROPIC
    ) {
      st.glMagFilter = GL_LINEAR;
    } else {
      throw new Error(`Unsupported MAGFILTER value: ${st.magFilter}`);
    }

    const minLinear =
      st.minFilter === D3DTEXF_LINEAR || st.minFilter === D3DTEXF_ANISOTROPIC;
    const minPoint =
      st.minFilter === D3DTEXF_POINT || st.minFilter === D3DTEXF_NONE;
    if (!minLinear && !minPoint) {
      throw new Error(`Unsupported MINFILTER value: ${st.minFilter}`);
    }

    if (st.mipFilter === D3DTEXF_NONE) {
      st.glMinFilter = minLinear ? GL_LINEAR : GL_NEAREST;
    } else if (st.mipFilter === D3DTEXF_POINT) {
      st.glMinFilter = minLinear
        ? GL_LINEAR_MIPMAP_NEAREST
        : GL_NEAREST_MIPMAP_NEAREST;
    } else if (
      st.mipFilter === D3DTEXF_LINEAR ||
      st.mipFilter === D3DTEXF_ANISOTROPIC
    ) {
      st.glMinFilter = minLinear
        ? GL_LINEAR_MIPMAP_LINEAR
        : GL_NEAREST_MIPMAP_LINEAR;
    } else {
      throw new Error(`Unsupported MIPFILTER value: ${st.mipFilter}`);
    }
  }

  private applySamplerStateToBoundTexture(stage: number): void {
    if (!this.gl) return;
    const texId = this.textureStages.get(stage) ?? 0;
    if (texId === 0) return;
    const texEntry = this.textures.get(texId);
    if (!texEntry || !texEntry.glTexture) return;

    const st = this.getSamplerState(stage);
    const gl = this.gl;
    gl.activeTexture(gl.TEXTURE0 + stage);
    gl.bindTexture(gl.TEXTURE_2D, texEntry.glTexture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, st.glWrapS);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, st.glWrapT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, st.glMagFilter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, st.glMinFilter);
  }

  private mapPrimitiveTypeAndCount(
    primitiveType: number,
    primitiveCount: number
  ): { glMode: number; vertexCount: number } {
    if (primitiveCount <= 0) {
      throw new Error(
        `Invalid primitive count: ${primitiveCount} (must be > 0)`
      );
    }
    switch (primitiveType) {
      case D3DPT_POINTLIST:
        return { glMode: GL_POINTS, vertexCount: primitiveCount };
      case D3DPT_LINELIST:
        return { glMode: GL_LINES, vertexCount: primitiveCount * 2 };
      case D3DPT_LINESTRIP:
        return { glMode: GL_LINE_STRIP, vertexCount: primitiveCount + 1 };
      case D3DPT_TRIANGLELIST:
        return { glMode: GL_TRIANGLES, vertexCount: primitiveCount * 3 };
      case D3DPT_TRIANGLESTRIP:
        return { glMode: GL_TRIANGLE_STRIP, vertexCount: primitiveCount + 2 };
      case D3DPT_TRIANGLEFAN:
        return { glMode: GL_TRIANGLE_FAN, vertexCount: primitiveCount + 2 };
      default:
        throw new Error(`Unsupported D3DPRIMITIVETYPE: ${primitiveType}`);
    }
  }

  private bindVertexDeclarationForDraw(baseVertexIndex: number): void {
    if (this.activeVertexDeclarationId === 0) return;
    const decl = this.vertexDeclarations.get(this.activeVertexDeclarationId);
    if (!decl) {
      throw new Error(
        `Active vertex declaration ID ${this.activeVertexDeclarationId} not found`
      );
    }

    for (let attrIdx = 0; attrIdx < decl.elements.length; attrIdx++) {
      const elem = decl.elements[attrIdx];
      const stream = this.streamSources.get(elem.stream);
      if (!stream || stream.bufferId === 0 || stream.stride === 0) {
        throw new Error(
          `Vertex declaration element ${attrIdx} references unbound stream ${elem.stream}`
        );
      }
      const vb = this.vertexBuffers.get(stream.bufferId);
      if (!vb) {
        throw new Error(
          `Stream ${elem.stream} references unknown vertex buffer ${stream.bufferId}`
        );
      }
      const attrByteOffset =
        stream.offset + baseVertexIndex * stream.stride + elem.offset;
      if (attrByteOffset < 0 || attrByteOffset + elem.spec.byteSize > vb.length) {
        throw new Error(
          `Vertex attribute ${attrIdx} offset (${attrByteOffset}) out of bounds for vertex buffer ${vb.bufferId} (length ${vb.length})`
        );
      }
      if (this.gl && vb.glBuffer) {
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, vb.glBuffer);
        this.gl.enableVertexAttribArray(attrIdx);
        this.gl.vertexAttribPointer(
          attrIdx,
          elem.spec.size,
          elem.spec.glType,
          elem.spec.normalized,
          stream.stride,
          attrByteOffset
        );
      }
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

  public initRingHeader(capacity: number = 4 * 1024 * 1024): void {
    const maxCap = Math.max(256, Math.min(capacity, this.u8.byteLength - this.ringBase - D3D9_RING_HEADER_SIZE));
    this.view.setUint32(this.ringBase + 0, D3D9_RING_MAGIC, true);
    this.view.setUint32(this.ringBase + 4, D3D9_RING_VERSION, true);
    this.view.setUint32(this.ringBase + 8, 0, true); // head
    this.view.setUint32(this.ringBase + 12, 0, true); // tail
    this.view.setUint32(this.ringBase + 16, maxCap, true); // capacity
    this.view.setUint32(this.ringBase + 20, 0, true); // frameIndex
    this.view.setUint32(this.ringBase + 24, 0, true); // droppedFrames
    this.view.setUint32(this.ringBase + 28, 0, true); // flags
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
    let magic = this.view.getUint32(this.ringBase + 0, true);
    if (magic === 0) {
      this.initRingHeader();
      magic = D3D9_RING_MAGIC;
    } else if (magic !== D3D9_RING_MAGIC) {
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

        case D3D9CmdType.CREATE_VERTEX_BUFFER: {
          if (!payloadView || payloadBytes < 16) {
            throw new Error(
              `Truncated CREATE_VERTEX_BUFFER payload: expected at least 16 bytes, got ${payloadBytes}`
            );
          }
          const bufferId = payloadView.getUint32(0, true);
          const length = payloadView.getUint32(4, true);
          const usage = payloadView.getUint32(8, true);
          const fvf = payloadView.getUint32(12, true);
          const pool = payloadBytes >= 20 ? payloadView.getUint32(16, true) : 0;

          if (bufferId === 0) {
            throw new Error(
              "Invalid vertex buffer ID: 0 (0 is reserved for null/unbind)"
            );
          }
          if (length === 0) {
            throw new Error(
              "Invalid vertex buffer length: 0 (must be > 0)"
            );
          }
          if (this.vertexBuffers.has(bufferId)) {
            throw new Error(
              `Duplicate vertex buffer ID: ${bufferId} already exists`
            );
          }

          const isDynamic = (usage & D3DUSAGE_DYNAMIC) !== 0;
          const glUsage = isDynamic
            ? (this.gl ? this.gl.DYNAMIC_DRAW : GL_DYNAMIC_DRAW)
            : (this.gl ? this.gl.STATIC_DRAW : GL_STATIC_DRAW);

          let glBuffer: WebGLBuffer | null = null;
          if (this.gl) {
            glBuffer = this.gl.createBuffer();
            if (!glBuffer) {
              throw new Error(
                `Failed to allocate WebGLBuffer for vertex buffer ${bufferId}`
              );
            }
            this.gl.bindBuffer(this.gl.ARRAY_BUFFER, glBuffer);
            this.gl.bufferData(this.gl.ARRAY_BUFFER, length, glUsage);
          }

          this.vertexBuffers.set(bufferId, {
            bufferId,
            glBuffer,
            length,
            usage,
            fvf,
            pool,
            glUsage,
            shadowData: new Uint8Array(length),
          });

          cmd = {
            type: D3D9CmdType.CREATE_VERTEX_BUFFER,
            bufferId,
            length,
            usage,
            fvf,
            pool,
          };
          break;
        }

        case D3D9CmdType.UPDATE_VERTEX_BUFFER: {
          if (!payloadView || !payloadBuf || payloadBytes < 12) {
            throw new Error(
              `Truncated UPDATE_VERTEX_BUFFER payload: expected at least 12 bytes, got ${payloadBytes}`
            );
          }
          const bufferId = payloadView.getUint32(0, true);
          const offset = payloadView.getUint32(4, true);
          const size = payloadView.getUint32(8, true);

          if (size === 0) {
            throw new Error(
              "Invalid UPDATE_VERTEX_BUFFER size: 0 (must be > 0)"
            );
          }
          if (payloadBytes < 12 + size) {
            throw new Error(
              `Truncated UPDATE_VERTEX_BUFFER data payload: expected ${12 + size} bytes, got ${payloadBytes}`
            );
          }

          const entry = this.vertexBuffers.get(bufferId);
          if (!entry) {
            throw new Error(
              `Unknown vertex buffer ID in UPDATE_VERTEX_BUFFER: ${bufferId}`
            );
          }

          if (offset + size > entry.length) {
            throw new Error(
              `Vertex buffer update out of bounds: offset (${offset}) + size (${size}) > buffer length (${entry.length})`
            );
          }

          const data = payloadBuf.slice(12, 12 + size);
          entry.shadowData.set(data, offset);

          if (this.gl && entry.glBuffer) {
            this.gl.bindBuffer(this.gl.ARRAY_BUFFER, entry.glBuffer);
            this.gl.bufferSubData(this.gl.ARRAY_BUFFER, offset, data);
          }

          cmd = {
            type: D3D9CmdType.UPDATE_VERTEX_BUFFER,
            bufferId,
            offset,
            size,
            data,
          };
          break;
        }

        case D3D9CmdType.SET_STREAM_SOURCE: {
          if (!payloadView || payloadBytes < 16) {
            throw new Error(
              `Truncated SET_STREAM_SOURCE payload: expected 16 bytes, got ${payloadBytes}`
            );
          }
          const streamNumber = payloadView.getUint32(0, true);
          const bufferId = payloadView.getUint32(4, true);
          const offset = payloadView.getUint32(8, true);
          const stride = payloadView.getUint32(12, true);

          if (streamNumber >= D3D9_MAX_STREAMS) {
            throw new Error(
              `Invalid stream number: ${streamNumber} (max streams is ${D3D9_MAX_STREAMS})`
            );
          }

          if (bufferId === 0) {
            this.streamSources.set(streamNumber, {
              streamNumber,
              bufferId: 0,
              offset: 0,
              stride: 0,
            });
            if (this.gl && streamNumber === 0) {
              this.gl.bindBuffer(this.gl.ARRAY_BUFFER, null);
            }
          } else {
            const entry = this.vertexBuffers.get(bufferId);
            if (!entry) {
              throw new Error(
                `Unknown vertex buffer ID in SET_STREAM_SOURCE: ${bufferId}`
              );
            }
            if (offset > entry.length) {
              throw new Error(
                `Stream source offset (${offset}) exceeds vertex buffer length (${entry.length})`
              );
            }
            this.streamSources.set(streamNumber, {
              streamNumber,
              bufferId,
              offset,
              stride,
            });
            if (this.gl && entry.glBuffer && streamNumber === 0) {
              this.gl.bindBuffer(this.gl.ARRAY_BUFFER, entry.glBuffer);
            }
          }

          cmd = {
            type: D3D9CmdType.SET_STREAM_SOURCE,
            streamNumber,
            bufferId,
            offset,
            stride,
          };
          break;
        }

        case D3D9CmdType.DESTROY_VERTEX_BUFFER: {
          if (!payloadView || payloadBytes < 4) {
            throw new Error(
              `Truncated DESTROY_VERTEX_BUFFER payload: expected 4 bytes, got ${payloadBytes}`
            );
          }
          const bufferId = payloadView.getUint32(0, true);
          this.destroyVertexBuffer(bufferId);
          cmd = {
            type: D3D9CmdType.DESTROY_VERTEX_BUFFER,
            bufferId,
          };
          break;
        }

        case D3D9CmdType.CREATE_INDEX_BUFFER: {
          if (!payloadView || payloadBytes < 16) {
            throw new Error(
              `Truncated CREATE_INDEX_BUFFER payload: expected at least 16 bytes, got ${payloadBytes}`
            );
          }
          const bufferId = payloadView.getUint32(0, true);
          const length = payloadView.getUint32(4, true);
          const usage = payloadView.getUint32(8, true);
          const format = payloadView.getUint32(12, true);
          const pool = payloadBytes >= 20 ? payloadView.getUint32(16, true) : 0;

          if (bufferId === 0) {
            throw new Error(
              "Invalid index buffer ID: 0 (0 is reserved for null/unbind)"
            );
          }
          if (length === 0) {
            throw new Error("Invalid index buffer length: 0 (must be > 0)");
          }
          if (format !== D3DFMT_INDEX16 && format !== D3DFMT_INDEX32) {
            throw new Error(
              `Unsupported index buffer format: ${format} (must be D3DFMT_INDEX16=101 or D3DFMT_INDEX32=102)`
            );
          }
          if (this.indexBuffers.has(bufferId)) {
            throw new Error(
              `Duplicate index buffer ID: ${bufferId} already exists`
            );
          }

          const isDynamic = (usage & D3DUSAGE_DYNAMIC) !== 0;
          const glUsage = isDynamic
            ? (this.gl ? this.gl.DYNAMIC_DRAW : GL_DYNAMIC_DRAW)
            : (this.gl ? this.gl.STATIC_DRAW : GL_STATIC_DRAW);
          const glIndexType =
            format === D3DFMT_INDEX32 ? GL_UNSIGNED_INT : GL_UNSIGNED_SHORT;
          const bytesPerIndex = format === D3DFMT_INDEX32 ? 4 : 2;

          let glBuffer: WebGLBuffer | null = null;
          if (this.gl) {
            glBuffer = this.gl.createBuffer();
            if (!glBuffer) {
              throw new Error(
                `Failed to allocate WebGLBuffer for index buffer ${bufferId}`
              );
            }
            this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, glBuffer);
            this.gl.bufferData(this.gl.ELEMENT_ARRAY_BUFFER, length, glUsage);
          }

          this.indexBuffers.set(bufferId, {
            bufferId,
            glBuffer,
            length,
            usage,
            format,
            pool,
            glUsage,
            glIndexType,
            bytesPerIndex,
            shadowData: new Uint8Array(length),
          });

          cmd = {
            type: D3D9CmdType.CREATE_INDEX_BUFFER,
            bufferId,
            length,
            usage,
            format,
            pool,
          };
          break;
        }

        case D3D9CmdType.UPDATE_INDEX_BUFFER: {
          if (!payloadView || !payloadBuf || payloadBytes < 12) {
            throw new Error(
              `Truncated UPDATE_INDEX_BUFFER payload: expected at least 12 bytes, got ${payloadBytes}`
            );
          }
          const bufferId = payloadView.getUint32(0, true);
          const offset = payloadView.getUint32(4, true);
          const size = payloadView.getUint32(8, true);

          if (size === 0) {
            throw new Error(
              "Invalid UPDATE_INDEX_BUFFER size: 0 (must be > 0)"
            );
          }
          if (payloadBytes < 12 + size) {
            throw new Error(
              `Truncated UPDATE_INDEX_BUFFER data payload: expected ${12 + size} bytes, got ${payloadBytes}`
            );
          }

          const entry = this.indexBuffers.get(bufferId);
          if (!entry) {
            throw new Error(
              `Unknown index buffer ID in UPDATE_INDEX_BUFFER: ${bufferId}`
            );
          }

          if (offset + size > entry.length) {
            throw new Error(
              `Index buffer update out of bounds: offset (${offset}) + size (${size}) > buffer length (${entry.length})`
            );
          }

          const data = payloadBuf.slice(12, 12 + size);
          entry.shadowData.set(data, offset);

          if (this.gl && entry.glBuffer) {
            this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, entry.glBuffer);
            this.gl.bufferSubData(this.gl.ELEMENT_ARRAY_BUFFER, offset, data);
          }

          cmd = {
            type: D3D9CmdType.UPDATE_INDEX_BUFFER,
            bufferId,
            offset,
            size,
            data,
          };
          break;
        }

        case D3D9CmdType.SET_INDICES: {
          if (!payloadView || payloadBytes < 4) {
            throw new Error(
              `Truncated SET_INDICES payload: expected 4 bytes, got ${payloadBytes}`
            );
          }
          const bufferId = payloadView.getUint32(0, true);
          if (bufferId === 0) {
            this.boundIndexBufferId = 0;
            if (this.gl) {
              this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, null);
            }
          } else {
            const entry = this.indexBuffers.get(bufferId);
            if (!entry) {
              throw new Error(
                `Unknown index buffer ID in SET_INDICES: ${bufferId}`
              );
            }
            this.boundIndexBufferId = bufferId;
            if (this.gl && entry.glBuffer) {
              this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, entry.glBuffer);
            }
          }
          cmd = {
            type: D3D9CmdType.SET_INDICES,
            bufferId,
          };
          break;
        }

        case D3D9CmdType.DESTROY_INDEX_BUFFER: {
          if (!payloadView || payloadBytes < 4) {
            throw new Error(
              `Truncated DESTROY_INDEX_BUFFER payload: expected 4 bytes, got ${payloadBytes}`
            );
          }
          const bufferId = payloadView.getUint32(0, true);
          this.destroyIndexBuffer(bufferId);
          cmd = {
            type: D3D9CmdType.DESTROY_INDEX_BUFFER,
            bufferId,
          };
          break;
        }

        case D3D9CmdType.CREATE_VERTEX_DECLARATION: {
          if (!payloadView || payloadBytes < 8) {
            throw new Error(
              `Truncated CREATE_VERTEX_DECLARATION payload: expected at least 8 bytes, got ${payloadBytes}`
            );
          }
          const declId = payloadView.getUint32(0, true);
          const elementCount = payloadView.getUint32(4, true);

          if (declId === 0) {
            throw new Error(
              "Invalid vertex declaration ID: 0 (0 is reserved for null/unbind)"
            );
          }
          if (elementCount === 0) {
            throw new Error(
              "Invalid vertex declaration element count: 0 (must be > 0)"
            );
          }
          if (payloadBytes < 8 + elementCount * 8) {
            throw new Error(
              `Truncated CREATE_VERTEX_DECLARATION elements: expected ${8 + elementCount * 8} bytes, got ${payloadBytes}`
            );
          }
          if (this.vertexDeclarations.has(declId)) {
            throw new Error(
              `Duplicate vertex declaration ID: ${declId} already exists`
            );
          }

          const parsedElements: (D3D9VertexElement & {
            spec: D3D9VertexElementSpec;
          })[] = [];
          const outElements: D3D9VertexElement[] = [];

          for (let i = 0; i < elementCount; i++) {
            const base = 8 + i * 8;
            const stream = payloadView.getUint16(base + 0, true);
            const offset = payloadView.getUint16(base + 2, true);
            const type = payloadView.getUint8(base + 4);
            const method = payloadView.getUint8(base + 5);
            const usage = payloadView.getUint8(base + 6);
            const usageIndex = payloadView.getUint8(base + 7);

            // Skip D3DDECL_END sentinel if included
            if (stream === 0xff || type === D3DDECLTYPE_UNUSED) {
              break;
            }
            if (stream >= D3D9_MAX_STREAMS) {
              throw new Error(
                `Invalid stream index ${stream} in vertex declaration ${declId}`
              );
            }
            const spec = this.mapDeclElementType(type);
            const elem: D3D9VertexElement = {
              stream,
              offset,
              type,
              method,
              usage,
              usageIndex,
            };
            outElements.push(elem);
            parsedElements.push({ ...elem, spec });
          }

          this.vertexDeclarations.set(declId, {
            declId,
            elements: parsedElements,
          });

          cmd = {
            type: D3D9CmdType.CREATE_VERTEX_DECLARATION,
            declId,
            elements: outElements,
          };
          break;
        }

        case D3D9CmdType.SET_VERTEX_DECLARATION: {
          if (!payloadView || payloadBytes < 4) {
            throw new Error(
              `Truncated SET_VERTEX_DECLARATION payload: expected 4 bytes, got ${payloadBytes}`
            );
          }
          const declId = payloadView.getUint32(0, true);
          if (declId !== 0 && !this.vertexDeclarations.has(declId)) {
            throw new Error(
              `Unknown vertex declaration ID in SET_VERTEX_DECLARATION: ${declId}`
            );
          }
          this.activeVertexDeclarationId = declId;
          cmd = {
            type: D3D9CmdType.SET_VERTEX_DECLARATION,
            declId,
          };
          break;
        }

        case D3D9CmdType.CREATE_TEXTURE: {
          if (!payloadView || payloadBytes < 28) {
            throw new Error(
              `Truncated CREATE_TEXTURE payload: expected 28 bytes, got ${payloadBytes}`
            );
          }
          const textureId = payloadView.getUint32(0, true);
          const width = payloadView.getUint32(4, true);
          const height = payloadView.getUint32(8, true);
          const levels = payloadView.getUint32(12, true) || 1;
          const usage = payloadView.getUint32(16, true);
          const format = payloadView.getUint32(20, true);
          const pool = payloadView.getUint32(24, true);

          if (textureId === 0) {
            throw new Error(
              "Invalid texture ID: 0 (0 is reserved for null/unbind)"
            );
          }
          if (width === 0 || height === 0) {
            throw new Error(
              `Invalid texture dimensions: ${width}x${height} (must be > 0)`
            );
          }
          if (this.textures.has(textureId)) {
            throw new Error(
              `Duplicate texture ID: ${textureId} already exists`
            );
          }

          // Validate supported texture format
          if (
            format !== D3DFMT_A8R8G8B8 &&
            format !== D3DFMT_X8R8G8B8 &&
            format !== D3DFMT_A8B8G8R8 &&
            format !== D3DFMT_L8 &&
            format !== D3DFMT_DXT1 &&
            format !== D3DFMT_DXT3 &&
            format !== D3DFMT_DXT5
          ) {
            throw new Error(`Unsupported texture format: 0x${format.toString(16)}`);
          }

          let glTexture: WebGLTexture | null = null;
          if (this.gl) {
            const gl = this.gl;
            glTexture = gl.createTexture();
            if (!glTexture) {
              throw new Error(`Failed to allocate WebGLTexture ${textureId}`);
            }
            gl.bindTexture(gl.TEXTURE_2D, glTexture);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
            gl.texImage2D(
              gl.TEXTURE_2D,
              0,
              gl.RGBA8,
              width,
              height,
              0,
              gl.RGBA,
              gl.UNSIGNED_BYTE,
              null
            );
          }

          this.textures.set(textureId, {
            textureId,
            glTexture,
            width,
            height,
            levels,
            usage,
            format,
            pool,
            levelData: new Map(),
          });

          cmd = {
            type: D3D9CmdType.CREATE_TEXTURE,
            textureId,
            width,
            height,
            levels,
            usage,
            format,
            pool,
          };
          break;
        }

        case D3D9CmdType.UPDATE_TEXTURE: {
          if (!payloadView || !payloadBuf || payloadBytes < 24) {
            throw new Error(
              `Truncated UPDATE_TEXTURE payload: expected at least 24 bytes, got ${payloadBytes}`
            );
          }
          const textureId = payloadView.getUint32(0, true);
          const level = payloadView.getUint32(4, true);
          const pitch = payloadView.getUint32(8, true);
          const dataBytes = payloadView.getUint32(12, true);
          const width = payloadView.getUint32(16, true);
          const height = payloadView.getUint32(20, true);

          if (dataBytes === 0 || width === 0 || height === 0) {
            throw new Error(
              `Invalid UPDATE_TEXTURE dimensions or size: ${width}x${height} (${dataBytes} bytes)`
            );
          }
          if (payloadBytes < 24 + dataBytes) {
            throw new Error(
              `Truncated UPDATE_TEXTURE pixel payload: expected ${24 + dataBytes} bytes, got ${payloadBytes}`
            );
          }

          const entry = this.textures.get(textureId);
          if (!entry) {
            throw new Error(
              `Unknown texture ID in UPDATE_TEXTURE: ${textureId}`
            );
          }

          const rawData = payloadBuf.subarray(24, 24 + dataBytes);
          const rgbaData = convertTextureToRgba8(
            entry.format,
            width,
            height,
            rawData
          );
          entry.levelData.set(level, rgbaData);

          if (this.gl && entry.glTexture) {
            const gl = this.gl;
            gl.bindTexture(gl.TEXTURE_2D, entry.glTexture);
            gl.texImage2D(
              gl.TEXTURE_2D,
              level,
              gl.RGBA8,
              width,
              height,
              0,
              gl.RGBA,
              gl.UNSIGNED_BYTE,
              rgbaData
            );
          }

          cmd = {
            type: D3D9CmdType.UPDATE_TEXTURE,
            textureId,
            level,
            pitch,
            dataBytes,
            width,
            height,
            rgbaData,
          };
          break;
        }

        case D3D9CmdType.SET_TEXTURE: {
          if (!payloadView || payloadBytes < 8) {
            throw new Error(
              `Truncated SET_TEXTURE payload: expected 8 bytes, got ${payloadBytes}`
            );
          }
          const stage = payloadView.getUint32(0, true);
          const textureId = payloadView.getUint32(4, true);

          if (stage >= D3D9_MAX_SAMPLERS) {
            throw new Error(
              `Invalid texture stage: ${stage} (max sampler stages is ${D3D9_MAX_SAMPLERS})`
            );
          }

          if (textureId === 0) {
            this.textureStages.set(stage, 0);
            if (this.gl) {
              this.gl.activeTexture(this.gl.TEXTURE0 + stage);
              this.gl.bindTexture(this.gl.TEXTURE_2D, null);
            }
          } else {
            const entry = this.textures.get(textureId);
            if (!entry) {
              throw new Error(`Unknown texture ID in SET_TEXTURE: ${textureId}`);
            }
            this.textureStages.set(stage, textureId);
            if (this.gl && entry.glTexture) {
              this.applySamplerStateToBoundTexture(stage);
            }
          }

          cmd = {
            type: D3D9CmdType.SET_TEXTURE,
            stage,
            textureId,
          };
          break;
        }

        case D3D9CmdType.SET_SAMPLER_STATE: {
          if (!payloadView || payloadBytes < 12) {
            throw new Error(
              `Truncated SET_SAMPLER_STATE payload: expected 12 bytes, got ${payloadBytes}`
            );
          }
          const sampler = payloadView.getUint32(0, true);
          const stateType = payloadView.getUint32(4, true);
          const value = payloadView.getUint32(8, true);

          if (sampler >= D3D9_MAX_SAMPLERS) {
            throw new Error(
              `Invalid sampler index: ${sampler} (max samplers is ${D3D9_MAX_SAMPLERS})`
            );
          }

          const st = this.getSamplerState(sampler);
          switch (stateType) {
            case D3DSAMP_ADDRESSU:
              st.glWrapS = this.mapGlWrapMode(value);
              st.addressU = value;
              break;
            case D3DSAMP_ADDRESSV:
              st.glWrapT = this.mapGlWrapMode(value);
              st.addressV = value;
              break;
            case D3DSAMP_ADDRESSW:
              this.mapGlWrapMode(value);
              st.addressW = value;
              break;
            case D3DSAMP_MAGFILTER:
              st.magFilter = value;
              this.updateSamplerGlFilters(st);
              break;
            case D3DSAMP_MINFILTER:
              st.minFilter = value;
              this.updateSamplerGlFilters(st);
              break;
            case D3DSAMP_MIPFILTER:
              st.mipFilter = value;
              this.updateSamplerGlFilters(st);
              break;
            case D3DSAMP_MAXANISOTROPY:
              if (value < 1) {
                throw new Error(`Invalid MAXANISOTROPY value: ${value}`);
              }
              st.maxAnisotropy = value;
              break;
            default:
              throw new Error(`Unsupported sampler state type: ${stateType}`);
          }

          this.applySamplerStateToBoundTexture(sampler);

          cmd = {
            type: D3D9CmdType.SET_SAMPLER_STATE,
            sampler,
            stateType,
            value,
          };
          break;
        }

        case D3D9CmdType.DRAW_PRIMITIVE: {
          if (!payloadView || payloadBytes < 12) {
            throw new Error(
              `Truncated DRAW_PRIMITIVE payload: expected 12 bytes, got ${payloadBytes}`
            );
          }
          if (this.sceneState !== SceneState.IN_SCENE) {
            throw new Error(
              "Invalid state: DRAW_PRIMITIVE called outside BEGIN_SCENE..END_SCENE"
            );
          }

          const primitiveType = payloadView.getUint32(0, true);
          const startVertex = payloadView.getUint32(4, true);
          const primitiveCount = payloadView.getUint32(8, true);

          const { glMode, vertexCount } = this.mapPrimitiveTypeAndCount(
            primitiveType,
            primitiveCount
          );

          const stream0 = this.streamSources.get(0);
          if (!stream0 || stream0.bufferId === 0 || stream0.stride === 0) {
            throw new Error(
              "Invalid draw state: stream 0 must be bound with non-zero stride before DRAW_PRIMITIVE"
            );
          }
          const vb0 = this.vertexBuffers.get(stream0.bufferId);
          if (!vb0) {
            throw new Error(
              `Stream 0 references unknown vertex buffer ${stream0.bufferId}`
            );
          }
          const requiredBytes =
            stream0.offset + (startVertex + vertexCount) * stream0.stride;
          if (requiredBytes > vb0.length) {
            throw new Error(
              `DRAW_PRIMITIVE vertex range (${requiredBytes} bytes) exceeds vertex buffer ${vb0.bufferId} length (${vb0.length})`
            );
          }

          this.bindVertexDeclarationForDraw(0);

          if (this.gl) {
            this.gl.drawArrays(glMode, startVertex, vertexCount);
          }
          this.drawCallsExecuted++;

          cmd = {
            type: D3D9CmdType.DRAW_PRIMITIVE,
            primitiveType,
            startVertex,
            primitiveCount,
            glMode,
            vertexCount,
          };
          break;
        }

        case D3D9CmdType.DRAW_INDEXED_PRIMITIVE: {
          if (!payloadView || payloadBytes < 24) {
            throw new Error(
              `Truncated DRAW_INDEXED_PRIMITIVE payload: expected 24 bytes, got ${payloadBytes}`
            );
          }
          if (this.sceneState !== SceneState.IN_SCENE) {
            throw new Error(
              "Invalid state: DRAW_INDEXED_PRIMITIVE called outside BEGIN_SCENE..END_SCENE"
            );
          }

          const primitiveType = payloadView.getUint32(0, true);
          const baseVertexIndex = payloadView.getInt32(4, true);
          const minVertexIndex = payloadView.getUint32(8, true);
          const numVertices = payloadView.getUint32(12, true);
          const startIndex = payloadView.getUint32(16, true);
          const primitiveCount = payloadView.getUint32(20, true);

          const { glMode, vertexCount } = this.mapPrimitiveTypeAndCount(
            primitiveType,
            primitiveCount
          );

          const stream0 = this.streamSources.get(0);
          if (!stream0 || stream0.bufferId === 0 || stream0.stride === 0) {
            throw new Error(
              "Invalid draw state: stream 0 must be bound with non-zero stride before DRAW_INDEXED_PRIMITIVE"
            );
          }
          if (this.boundIndexBufferId === 0) {
            throw new Error(
              "Invalid draw state: index buffer must be bound via SET_INDICES before DRAW_INDEXED_PRIMITIVE"
            );
          }
          const ibEntry = this.indexBuffers.get(this.boundIndexBufferId);
          if (!ibEntry) {
            throw new Error(
              `Bound index buffer ${this.boundIndexBufferId} not found`
            );
          }

          const indexByteOffset = startIndex * ibEntry.bytesPerIndex;
          const requiredIndexBytes =
            indexByteOffset + vertexCount * ibEntry.bytesPerIndex;
          if (requiredIndexBytes > ibEntry.length) {
            throw new Error(
              `DRAW_INDEXED_PRIMITIVE index range (${requiredIndexBytes} bytes) exceeds index buffer ${ibEntry.bufferId} length (${ibEntry.length})`
            );
          }

          this.bindVertexDeclarationForDraw(baseVertexIndex);

          if (this.gl && ibEntry.glBuffer) {
            this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, ibEntry.glBuffer);
            this.gl.drawElements(
              glMode,
              vertexCount,
              ibEntry.glIndexType,
              indexByteOffset
            );
          }
          this.drawCallsExecuted++;

          cmd = {
            type: D3D9CmdType.DRAW_INDEXED_PRIMITIVE,
            primitiveType,
            baseVertexIndex,
            minVertexIndex,
            numVertices,
            startIndex,
            primitiveCount,
            glMode,
            vertexCount,
            glIndexType: ibEntry.glIndexType,
            indexByteOffset,
          };
          break;
        }

        case D3D9CmdType.DESTROY_RESOURCE: {
          if (!payloadView || payloadBytes < 8) {
            throw new Error(
              `Truncated DESTROY_RESOURCE payload: expected 8 bytes, got ${payloadBytes}`
            );
          }
          const resourceType = payloadView.getUint32(0, true);
          const resourceId = payloadView.getUint32(4, true);

          if (resourceType === 1) {
            this.destroyVertexBuffer(resourceId);
          } else if (resourceType === 2) {
            this.destroyIndexBuffer(resourceId);
          } else if (resourceType === 3) {
            this.destroyTexture(resourceId);
          } else if (resourceType === 4) {
            this.destroyVertexDeclaration(resourceId);
          } else {
            throw new Error(
              `Unsupported resource type in DESTROY_RESOURCE: ${resourceType}`
            );
          }

          cmd = {
            type: D3D9CmdType.DESTROY_RESOURCE,
            resourceType,
            resourceId,
          };
          break;
        }

        default: {
          throw new Error(
            `Unsupported command opcode in consumer: ${cmdType}`
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
    payload: Uint8Array | null,
    explicitPayloadBytes?: number
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
    hdrView.setUint32(4, explicitPayloadBytes ?? alignedPayload, true);

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

  public emitCreateVertexBuffer(
    bufferId: number,
    length: number,
    usage: number = 0,
    fvf: number = 0,
    pool: number = 0
  ): void {
    const payload = new Uint8Array(20);
    const v = new DataView(payload.buffer);
    v.setUint32(0, bufferId, true);
    v.setUint32(4, length, true);
    v.setUint32(8, usage, true);
    v.setUint32(12, fvf, true);
    v.setUint32(16, pool, true);
    this.emitRawPacket(D3D9CmdType.CREATE_VERTEX_BUFFER, 0, payload);
  }

  public emitUpdateVertexBuffer(
    bufferId: number,
    offset: number,
    data: Uint8Array | ArrayBufferView
  ): void {
    const bytes =
      data instanceof Uint8Array
        ? data
        : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    const payload = new Uint8Array(12 + bytes.byteLength);
    const v = new DataView(payload.buffer);
    v.setUint32(0, bufferId, true);
    v.setUint32(4, offset, true);
    v.setUint32(8, bytes.byteLength, true);
    payload.set(bytes, 12);
    this.emitRawPacket(D3D9CmdType.UPDATE_VERTEX_BUFFER, 0, payload);
  }

  public emitSetStreamSource(
    streamNumber: number,
    bufferId: number,
    offset: number,
    stride: number
  ): void {
    const payload = new Uint8Array(16);
    const v = new DataView(payload.buffer);
    v.setUint32(0, streamNumber, true);
    v.setUint32(4, bufferId, true);
    v.setUint32(8, offset, true);
    v.setUint32(12, stride, true);
    this.emitRawPacket(D3D9CmdType.SET_STREAM_SOURCE, 0, payload);
  }

  public emitDestroyVertexBuffer(bufferId: number): void {
    const payload = new Uint8Array(4);
    const v = new DataView(payload.buffer);
    v.setUint32(0, bufferId, true);
    this.emitRawPacket(D3D9CmdType.DESTROY_VERTEX_BUFFER, 0, payload);
  }

  public emitCreateIndexBuffer(
    bufferId: number,
    length: number,
    usage: number = 0,
    format: number = D3DFMT_INDEX16,
    pool: number = 0
  ): void {
    const payload = new Uint8Array(20);
    const v = new DataView(payload.buffer);
    v.setUint32(0, bufferId, true);
    v.setUint32(4, length, true);
    v.setUint32(8, usage, true);
    v.setUint32(12, format, true);
    v.setUint32(16, pool, true);
    this.emitRawPacket(D3D9CmdType.CREATE_INDEX_BUFFER, 0, payload);
  }

  public emitUpdateIndexBuffer(
    bufferId: number,
    offset: number,
    data: Uint8Array | ArrayBufferView
  ): void {
    const bytes =
      data instanceof Uint8Array
        ? data
        : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    const payload = new Uint8Array(12 + bytes.byteLength);
    const v = new DataView(payload.buffer);
    v.setUint32(0, bufferId, true);
    v.setUint32(4, offset, true);
    v.setUint32(8, bytes.byteLength, true);
    payload.set(bytes, 12);
    this.emitRawPacket(D3D9CmdType.UPDATE_INDEX_BUFFER, 0, payload);
  }

  public emitSetIndices(bufferId: number): void {
    const payload = new Uint8Array(4);
    const v = new DataView(payload.buffer);
    v.setUint32(0, bufferId, true);
    this.emitRawPacket(D3D9CmdType.SET_INDICES, 0, payload);
  }

  public emitDestroyIndexBuffer(bufferId: number): void {
    const payload = new Uint8Array(4);
    const v = new DataView(payload.buffer);
    v.setUint32(0, bufferId, true);
    this.emitRawPacket(D3D9CmdType.DESTROY_INDEX_BUFFER, 0, payload);
  }

  public emitCreateVertexDeclaration(
    declId: number,
    elements: D3D9VertexElement[]
  ): void {
    const payload = new Uint8Array(8 + elements.length * 8);
    const v = new DataView(payload.buffer);
    v.setUint32(0, declId, true);
    v.setUint32(4, elements.length, true);
    for (let i = 0; i < elements.length; i++) {
      const base = 8 + i * 8;
      const e = elements[i];
      v.setUint16(base + 0, e.stream, true);
      v.setUint16(base + 2, e.offset, true);
      v.setUint8(base + 4, e.type);
      v.setUint8(base + 5, e.method ?? 0);
      v.setUint8(base + 6, e.usage);
      v.setUint8(base + 7, e.usageIndex ?? 0);
    }
    this.emitRawPacket(D3D9CmdType.CREATE_VERTEX_DECLARATION, 0, payload);
  }

  public emitSetVertexDeclaration(declId: number): void {
    const payload = new Uint8Array(4);
    const v = new DataView(payload.buffer);
    v.setUint32(0, declId, true);
    this.emitRawPacket(D3D9CmdType.SET_VERTEX_DECLARATION, 0, payload);
  }

  public emitCreateTexture(
    textureId: number,
    width: number,
    height: number,
    levels: number = 1,
    usage: number = 0,
    format: number = D3DFMT_A8R8G8B8,
    pool: number = 0
  ): void {
    const payload = new Uint8Array(28);
    const v = new DataView(payload.buffer);
    v.setUint32(0, textureId, true);
    v.setUint32(4, width, true);
    v.setUint32(8, height, true);
    v.setUint32(12, levels, true);
    v.setUint32(16, usage, true);
    v.setUint32(20, format, true);
    v.setUint32(24, pool, true);
    this.emitRawPacket(D3D9CmdType.CREATE_TEXTURE, 0, payload);
  }

  public emitUpdateTexture(
    textureId: number,
    level: number,
    pitch: number,
    width: number,
    height: number,
    data: Uint8Array | ArrayBufferView
  ): void {
    const bytes =
      data instanceof Uint8Array
        ? data
        : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    const payload = new Uint8Array(24 + bytes.byteLength);
    const v = new DataView(payload.buffer);
    v.setUint32(0, textureId, true);
    v.setUint32(4, level, true);
    v.setUint32(8, pitch, true);
    v.setUint32(12, bytes.byteLength, true);
    v.setUint32(16, width, true);
    v.setUint32(20, height, true);
    payload.set(bytes, 24);
    this.emitRawPacket(D3D9CmdType.UPDATE_TEXTURE, 0, payload);
  }

  public emitSetTexture(stage: number, textureId: number): void {
    const payload = new Uint8Array(8);
    const v = new DataView(payload.buffer);
    v.setUint32(0, stage, true);
    v.setUint32(4, textureId, true);
    this.emitRawPacket(D3D9CmdType.SET_TEXTURE, 0, payload);
  }

  public emitSetSamplerState(
    sampler: number,
    stateType: number,
    value: number
  ): void {
    const payload = new Uint8Array(12);
    const v = new DataView(payload.buffer);
    v.setUint32(0, sampler, true);
    v.setUint32(4, stateType, true);
    v.setUint32(8, value, true);
    this.emitRawPacket(D3D9CmdType.SET_SAMPLER_STATE, 0, payload);
  }

  public emitDrawPrimitive(
    primitiveType: number,
    startVertex: number,
    primitiveCount: number
  ): void {
    const payload = new Uint8Array(12);
    const v = new DataView(payload.buffer);
    v.setUint32(0, primitiveType, true);
    v.setUint32(4, startVertex, true);
    v.setUint32(8, primitiveCount, true);
    this.emitRawPacket(D3D9CmdType.DRAW_PRIMITIVE, 0, payload);
  }

  public emitDrawIndexedPrimitive(
    primitiveType: number,
    baseVertexIndex: number,
    minVertexIndex: number,
    numVertices: number,
    startIndex: number,
    primitiveCount: number
  ): void {
    const payload = new Uint8Array(24);
    const v = new DataView(payload.buffer);
    v.setUint32(0, primitiveType, true);
    v.setInt32(4, baseVertexIndex, true);
    v.setUint32(8, minVertexIndex, true);
    v.setUint32(12, numVertices, true);
    v.setUint32(16, startIndex, true);
    v.setUint32(20, primitiveCount, true);
    this.emitRawPacket(D3D9CmdType.DRAW_INDEXED_PRIMITIVE, 0, payload);
  }

  public emitDestroyResource(resourceType: number, resourceId: number): void {
    const payload = new Uint8Array(8);
    const v = new DataView(payload.buffer);
    v.setUint32(0, resourceType, true);
    v.setUint32(4, resourceId, true);
    this.emitRawPacket(D3D9CmdType.DESTROY_RESOURCE, 0, payload);
  }
}
