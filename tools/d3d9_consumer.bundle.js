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

  // web/src/d3d9_consumer.ts
  var d3d9_consumer_exports = {};
  __export(d3d9_consumer_exports, {
    D3D9CmdType: () => D3D9CmdType,
    D3D9CommandConsumer: () => D3D9CommandConsumer,
    D3D9CommandProducer: () => D3D9CommandProducer,
    D3D9_MAX_SAMPLERS: () => D3D9_MAX_SAMPLERS,
    D3D9_MAX_STREAMS: () => D3D9_MAX_STREAMS,
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
    D3DDECLTYPE_D3DCOLOR: () => D3DDECLTYPE_D3DCOLOR,
    D3DDECLTYPE_FLOAT1: () => D3DDECLTYPE_FLOAT1,
    D3DDECLTYPE_FLOAT16_2: () => D3DDECLTYPE_FLOAT16_2,
    D3DDECLTYPE_FLOAT16_4: () => D3DDECLTYPE_FLOAT16_4,
    D3DDECLTYPE_FLOAT2: () => D3DDECLTYPE_FLOAT2,
    D3DDECLTYPE_FLOAT3: () => D3DDECLTYPE_FLOAT3,
    D3DDECLTYPE_FLOAT4: () => D3DDECLTYPE_FLOAT4,
    D3DDECLTYPE_SHORT2: () => D3DDECLTYPE_SHORT2,
    D3DDECLTYPE_SHORT2N: () => D3DDECLTYPE_SHORT2N,
    D3DDECLTYPE_SHORT4: () => D3DDECLTYPE_SHORT4,
    D3DDECLTYPE_SHORT4N: () => D3DDECLTYPE_SHORT4N,
    D3DDECLTYPE_UBYTE4: () => D3DDECLTYPE_UBYTE4,
    D3DDECLTYPE_UBYTE4N: () => D3DDECLTYPE_UBYTE4N,
    D3DDECLTYPE_UNUSED: () => D3DDECLTYPE_UNUSED,
    D3DDECLTYPE_USHORT2N: () => D3DDECLTYPE_USHORT2N,
    D3DDECLTYPE_USHORT4N: () => D3DDECLTYPE_USHORT4N,
    D3DDECLUSAGE_BINORMAL: () => D3DDECLUSAGE_BINORMAL,
    D3DDECLUSAGE_BLENDINDICES: () => D3DDECLUSAGE_BLENDINDICES,
    D3DDECLUSAGE_BLENDWEIGHT: () => D3DDECLUSAGE_BLENDWEIGHT,
    D3DDECLUSAGE_COLOR: () => D3DDECLUSAGE_COLOR,
    D3DDECLUSAGE_DEPTH: () => D3DDECLUSAGE_DEPTH,
    D3DDECLUSAGE_FOG: () => D3DDECLUSAGE_FOG,
    D3DDECLUSAGE_NORMAL: () => D3DDECLUSAGE_NORMAL,
    D3DDECLUSAGE_POSITION: () => D3DDECLUSAGE_POSITION,
    D3DDECLUSAGE_POSITIONT: () => D3DDECLUSAGE_POSITIONT,
    D3DDECLUSAGE_PSIZE: () => D3DDECLUSAGE_PSIZE,
    D3DDECLUSAGE_SAMPLE: () => D3DDECLUSAGE_SAMPLE,
    D3DDECLUSAGE_TANGENT: () => D3DDECLUSAGE_TANGENT,
    D3DDECLUSAGE_TESSFACTOR: () => D3DDECLUSAGE_TESSFACTOR,
    D3DDECLUSAGE_TEXCOORD: () => D3DDECLUSAGE_TEXCOORD,
    D3DFMT_A8B8G8R8: () => D3DFMT_A8B8G8R8,
    D3DFMT_A8R8G8B8: () => D3DFMT_A8R8G8B8,
    D3DFMT_DXT1: () => D3DFMT_DXT1,
    D3DFMT_DXT3: () => D3DFMT_DXT3,
    D3DFMT_DXT5: () => D3DFMT_DXT5,
    D3DFMT_INDEX16: () => D3DFMT_INDEX16,
    D3DFMT_INDEX32: () => D3DFMT_INDEX32,
    D3DFMT_L8: () => D3DFMT_L8,
    D3DFMT_X8R8G8B8: () => D3DFMT_X8R8G8B8,
    D3DPOOL_DEFAULT: () => D3DPOOL_DEFAULT,
    D3DPOOL_MANAGED: () => D3DPOOL_MANAGED,
    D3DPOOL_SCRATCH: () => D3DPOOL_SCRATCH,
    D3DPOOL_SYSTEMMEM: () => D3DPOOL_SYSTEMMEM,
    D3DPT_LINELIST: () => D3DPT_LINELIST,
    D3DPT_LINESTRIP: () => D3DPT_LINESTRIP,
    D3DPT_POINTLIST: () => D3DPT_POINTLIST,
    D3DPT_TRIANGLEFAN: () => D3DPT_TRIANGLEFAN,
    D3DPT_TRIANGLELIST: () => D3DPT_TRIANGLELIST,
    D3DPT_TRIANGLESTRIP: () => D3DPT_TRIANGLESTRIP,
    D3DRS_ALPHABLENDENABLE: () => D3DRS_ALPHABLENDENABLE,
    D3DRS_COLORWRITEENABLE: () => D3DRS_COLORWRITEENABLE,
    D3DRS_CULLMODE: () => D3DRS_CULLMODE,
    D3DRS_DESTBLEND: () => D3DRS_DESTBLEND,
    D3DRS_SRCBLEND: () => D3DRS_SRCBLEND,
    D3DRS_ZENABLE: () => D3DRS_ZENABLE,
    D3DRS_ZFUNC: () => D3DRS_ZFUNC,
    D3DRS_ZWRITEENABLE: () => D3DRS_ZWRITEENABLE,
    D3DSAMP_ADDRESSU: () => D3DSAMP_ADDRESSU,
    D3DSAMP_ADDRESSV: () => D3DSAMP_ADDRESSV,
    D3DSAMP_ADDRESSW: () => D3DSAMP_ADDRESSW,
    D3DSAMP_BORDERCOLOR: () => D3DSAMP_BORDERCOLOR,
    D3DSAMP_MAGFILTER: () => D3DSAMP_MAGFILTER,
    D3DSAMP_MAXANISOTROPY: () => D3DSAMP_MAXANISOTROPY,
    D3DSAMP_MINFILTER: () => D3DSAMP_MINFILTER,
    D3DSAMP_MIPFILTER: () => D3DSAMP_MIPFILTER,
    D3DTADDRESS_BORDER: () => D3DTADDRESS_BORDER,
    D3DTADDRESS_CLAMP: () => D3DTADDRESS_CLAMP,
    D3DTADDRESS_MIRROR: () => D3DTADDRESS_MIRROR,
    D3DTADDRESS_WRAP: () => D3DTADDRESS_WRAP,
    D3DTEXF_ANISOTROPIC: () => D3DTEXF_ANISOTROPIC,
    D3DTEXF_LINEAR: () => D3DTEXF_LINEAR,
    D3DTEXF_NONE: () => D3DTEXF_NONE,
    D3DTEXF_POINT: () => D3DTEXF_POINT,
    D3DUSAGE_DYNAMIC: () => D3DUSAGE_DYNAMIC,
    D3DUSAGE_WRITEONLY: () => D3DUSAGE_WRITEONLY,
    D3DZB_FALSE: () => D3DZB_FALSE,
    D3DZB_TRUE: () => D3DZB_TRUE,
    D3DZB_USEW: () => D3DZB_USEW,
    GL_BYTE: () => GL_BYTE,
    GL_CLAMP_TO_EDGE: () => GL_CLAMP_TO_EDGE,
    GL_DYNAMIC_DRAW: () => GL_DYNAMIC_DRAW,
    GL_FLOAT: () => GL_FLOAT,
    GL_HALF_FLOAT: () => GL_HALF_FLOAT,
    GL_LINEAR: () => GL_LINEAR,
    GL_LINEAR_MIPMAP_LINEAR: () => GL_LINEAR_MIPMAP_LINEAR,
    GL_LINEAR_MIPMAP_NEAREST: () => GL_LINEAR_MIPMAP_NEAREST,
    GL_LINES: () => GL_LINES,
    GL_LINE_STRIP: () => GL_LINE_STRIP,
    GL_MIRRORED_REPEAT: () => GL_MIRRORED_REPEAT,
    GL_NEAREST: () => GL_NEAREST,
    GL_NEAREST_MIPMAP_LINEAR: () => GL_NEAREST_MIPMAP_LINEAR,
    GL_NEAREST_MIPMAP_NEAREST: () => GL_NEAREST_MIPMAP_NEAREST,
    GL_POINTS: () => GL_POINTS,
    GL_REPEAT: () => GL_REPEAT,
    GL_SHORT: () => GL_SHORT,
    GL_STATIC_DRAW: () => GL_STATIC_DRAW,
    GL_TRIANGLES: () => GL_TRIANGLES,
    GL_TRIANGLE_FAN: () => GL_TRIANGLE_FAN,
    GL_TRIANGLE_STRIP: () => GL_TRIANGLE_STRIP,
    GL_UNSIGNED_BYTE: () => GL_UNSIGNED_BYTE,
    GL_UNSIGNED_INT: () => GL_UNSIGNED_INT,
    GL_UNSIGNED_SHORT: () => GL_UNSIGNED_SHORT,
    SceneState: () => SceneState,
    convertTextureToRgba8: () => convertTextureToRgba8
  });
  var D3D9_RING_MAGIC = 960770884;
  var D3D9_RING_VERSION = 1;
  var D3D9_RING_HEADER_SIZE = 64;
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
    D3D9CmdType2[D3D9CmdType2["UPDATE_VERTEX_BUFFER"] = 25] = "UPDATE_VERTEX_BUFFER";
    D3D9CmdType2[D3D9CmdType2["DESTROY_VERTEX_BUFFER"] = 26] = "DESTROY_VERTEX_BUFFER";
    D3D9CmdType2[D3D9CmdType2["UPDATE_INDEX_BUFFER"] = 27] = "UPDATE_INDEX_BUFFER";
    D3D9CmdType2[D3D9CmdType2["DESTROY_INDEX_BUFFER"] = 28] = "DESTROY_INDEX_BUFFER";
    D3D9CmdType2[D3D9CmdType2["CREATE_VERTEX_DECLARATION"] = 29] = "CREATE_VERTEX_DECLARATION";
    D3D9CmdType2[D3D9CmdType2["COUNT"] = 30] = "COUNT";
    return D3D9CmdType2;
  })(D3D9CmdType || {});
  var D3DCLEAR_TARGET = 1;
  var D3DCLEAR_ZBUFFER = 2;
  var D3DCLEAR_STENCIL = 4;
  var D3DRS_ZENABLE = 7;
  var D3DRS_ZWRITEENABLE = 14;
  var D3DRS_SRCBLEND = 19;
  var D3DRS_DESTBLEND = 20;
  var D3DRS_CULLMODE = 22;
  var D3DRS_ZFUNC = 23;
  var D3DRS_ALPHABLENDENABLE = 27;
  var D3DRS_COLORWRITEENABLE = 168;
  var D3DZB_FALSE = 0;
  var D3DZB_TRUE = 1;
  var D3DZB_USEW = 2;
  var D3DCMP_NEVER = 1;
  var D3DCMP_LESS = 2;
  var D3DCMP_EQUAL = 3;
  var D3DCMP_LESSEQUAL = 4;
  var D3DCMP_GREATER = 5;
  var D3DCMP_NOTEQUAL = 6;
  var D3DCMP_GREATEREQUAL = 7;
  var D3DCMP_ALWAYS = 8;
  var D3DCULL_NONE = 1;
  var D3DCULL_CW = 2;
  var D3DCULL_CCW = 3;
  var D3DBLEND_ZERO = 1;
  var D3DBLEND_ONE = 2;
  var D3DBLEND_SRCCOLOR = 3;
  var D3DBLEND_INVSRCCOLOR = 4;
  var D3DBLEND_SRCALPHA = 5;
  var D3DBLEND_INVSRCALPHA = 6;
  var D3DBLEND_DESTALPHA = 7;
  var D3DBLEND_INVDESTALPHA = 8;
  var D3DBLEND_DESTCOLOR = 9;
  var D3DBLEND_INVDESTCOLOR = 10;
  var D3DBLEND_SRCALPHASAT = 11;
  var D3DBLEND_BOTHSRCALPHA = 12;
  var D3DBLEND_BOTHINVSRCALPHA = 13;
  var D3DBLEND_BLENDFACTOR = 14;
  var D3DBLEND_INVBLENDFACTOR = 15;
  var D3DCOLORWRITEENABLE_RED = 1;
  var D3DCOLORWRITEENABLE_GREEN = 2;
  var D3DCOLORWRITEENABLE_BLUE = 4;
  var D3DCOLORWRITEENABLE_ALPHA = 8;
  var D3DUSAGE_WRITEONLY = 8;
  var D3DUSAGE_DYNAMIC = 512;
  var D3DPOOL_DEFAULT = 0;
  var D3DPOOL_MANAGED = 1;
  var D3DPOOL_SYSTEMMEM = 2;
  var D3DPOOL_SCRATCH = 3;
  var D3DFMT_A8R8G8B8 = 21;
  var D3DFMT_X8R8G8B8 = 22;
  var D3DFMT_A8B8G8R8 = 32;
  var D3DFMT_L8 = 50;
  var D3DFMT_INDEX16 = 101;
  var D3DFMT_INDEX32 = 102;
  var D3DFMT_DXT1 = 827611204;
  var D3DFMT_DXT3 = 861165636;
  var D3DFMT_DXT5 = 894720068;
  var D3DPT_POINTLIST = 1;
  var D3DPT_LINELIST = 2;
  var D3DPT_LINESTRIP = 3;
  var D3DPT_TRIANGLELIST = 4;
  var D3DPT_TRIANGLESTRIP = 5;
  var D3DPT_TRIANGLEFAN = 6;
  var D3DDECLTYPE_FLOAT1 = 0;
  var D3DDECLTYPE_FLOAT2 = 1;
  var D3DDECLTYPE_FLOAT3 = 2;
  var D3DDECLTYPE_FLOAT4 = 3;
  var D3DDECLTYPE_D3DCOLOR = 4;
  var D3DDECLTYPE_UBYTE4 = 5;
  var D3DDECLTYPE_SHORT2 = 6;
  var D3DDECLTYPE_SHORT4 = 7;
  var D3DDECLTYPE_UBYTE4N = 8;
  var D3DDECLTYPE_SHORT2N = 9;
  var D3DDECLTYPE_SHORT4N = 10;
  var D3DDECLTYPE_USHORT2N = 11;
  var D3DDECLTYPE_USHORT4N = 12;
  var D3DDECLTYPE_FLOAT16_2 = 15;
  var D3DDECLTYPE_FLOAT16_4 = 16;
  var D3DDECLTYPE_UNUSED = 17;
  var D3DDECLUSAGE_POSITION = 0;
  var D3DDECLUSAGE_BLENDWEIGHT = 1;
  var D3DDECLUSAGE_BLENDINDICES = 2;
  var D3DDECLUSAGE_NORMAL = 3;
  var D3DDECLUSAGE_PSIZE = 4;
  var D3DDECLUSAGE_TEXCOORD = 5;
  var D3DDECLUSAGE_TANGENT = 6;
  var D3DDECLUSAGE_BINORMAL = 7;
  var D3DDECLUSAGE_TESSFACTOR = 8;
  var D3DDECLUSAGE_POSITIONT = 9;
  var D3DDECLUSAGE_COLOR = 10;
  var D3DDECLUSAGE_FOG = 11;
  var D3DDECLUSAGE_DEPTH = 12;
  var D3DDECLUSAGE_SAMPLE = 13;
  var D3DSAMP_ADDRESSU = 1;
  var D3DSAMP_ADDRESSV = 2;
  var D3DSAMP_ADDRESSW = 3;
  var D3DSAMP_BORDERCOLOR = 4;
  var D3DSAMP_MAGFILTER = 5;
  var D3DSAMP_MINFILTER = 6;
  var D3DSAMP_MIPFILTER = 7;
  var D3DSAMP_MAXANISOTROPY = 10;
  var D3DTADDRESS_WRAP = 1;
  var D3DTADDRESS_MIRROR = 2;
  var D3DTADDRESS_CLAMP = 3;
  var D3DTADDRESS_BORDER = 4;
  var D3DTEXF_NONE = 0;
  var D3DTEXF_POINT = 1;
  var D3DTEXF_LINEAR = 2;
  var D3DTEXF_ANISOTROPIC = 3;
  var D3D9_MAX_STREAMS = 16;
  var D3D9_MAX_SAMPLERS = 16;
  var GL_STATIC_DRAW = 35044;
  var GL_DYNAMIC_DRAW = 35048;
  var GL_BYTE = 5120;
  var GL_UNSIGNED_BYTE = 5121;
  var GL_SHORT = 5122;
  var GL_UNSIGNED_SHORT = 5123;
  var GL_UNSIGNED_INT = 5125;
  var GL_FLOAT = 5126;
  var GL_HALF_FLOAT = 5131;
  var GL_POINTS = 0;
  var GL_LINES = 1;
  var GL_LINE_STRIP = 3;
  var GL_TRIANGLES = 4;
  var GL_TRIANGLE_STRIP = 5;
  var GL_TRIANGLE_FAN = 6;
  var GL_NEAREST = 9728;
  var GL_LINEAR = 9729;
  var GL_NEAREST_MIPMAP_NEAREST = 9984;
  var GL_LINEAR_MIPMAP_NEAREST = 9985;
  var GL_NEAREST_MIPMAP_LINEAR = 9986;
  var GL_LINEAR_MIPMAP_LINEAR = 9987;
  var GL_REPEAT = 10497;
  var GL_CLAMP_TO_EDGE = 33071;
  var GL_MIRRORED_REPEAT = 33648;
  var SceneState = /* @__PURE__ */ ((SceneState2) => {
    SceneState2[SceneState2["IDLE"] = 0] = "IDLE";
    SceneState2[SceneState2["IN_SCENE"] = 1] = "IN_SCENE";
    return SceneState2;
  })(SceneState || {});
  function unpackRgb565(c) {
    const r5 = c >>> 11 & 31;
    const g6 = c >>> 5 & 63;
    const b5 = c & 31;
    return [
      r5 << 3 | r5 >>> 2,
      g6 << 2 | g6 >>> 4,
      b5 << 3 | b5 >>> 2
    ];
  }
  function decodeDxtColorBlock(src, srcOffset, isDxt1) {
    const c0 = src[srcOffset] | src[srcOffset + 1] << 8;
    const c1 = src[srcOffset + 2] | src[srcOffset + 3] << 8;
    const [r0, g0, b0] = unpackRgb565(c0);
    const [r1, g1, b1] = unpackRgb565(c1);
    const palette = [
      [r0, g0, b0, 255],
      [r1, g1, b1, 255],
      [0, 0, 0, 255],
      [0, 0, 0, 255]
    ];
    if (!isDxt1 || c0 > c1) {
      palette[2] = [
        Math.floor((2 * r0 + r1 + 1) / 3),
        Math.floor((2 * g0 + g1 + 1) / 3),
        Math.floor((2 * b0 + b1 + 1) / 3),
        255
      ];
      palette[3] = [
        Math.floor((r0 + 2 * r1 + 1) / 3),
        Math.floor((g0 + 2 * g1 + 1) / 3),
        Math.floor((b0 + 2 * b1 + 1) / 3),
        255
      ];
    } else {
      palette[2] = [
        Math.floor((r0 + r1) / 2),
        Math.floor((g0 + g1) / 2),
        Math.floor((b0 + b1) / 2),
        255
      ];
      palette[3] = [0, 0, 0, 0];
    }
    return palette;
  }
  function convertTextureToRgba8(format, width, height, src) {
    const dst = new Uint8Array(width * height * 4);
    if (format === D3DFMT_A8R8G8B8 || format === D3DFMT_X8R8G8B8) {
      const pixelCount = width * height;
      const forceOpaque = format === D3DFMT_X8R8G8B8;
      for (let i = 0; i < pixelCount; i++) {
        const si = i * 4;
        const b = src[si] ?? 0;
        const g = src[si + 1] ?? 0;
        const r = src[si + 2] ?? 0;
        const a = forceOpaque ? 255 : src[si + 3] ?? 255;
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
    if (format === D3DFMT_DXT1 || format === D3DFMT_DXT3 || format === D3DFMT_DXT5) {
      const blocksX = Math.max(1, Math.ceil(width / 4));
      const blocksY = Math.max(1, Math.ceil(height / 4));
      const blockBytes = format === D3DFMT_DXT1 ? 8 : 16;
      let blockOffset = 0;
      for (let by = 0; by < blocksY; by++) {
        for (let bx = 0; bx < blocksX; bx++) {
          if (blockOffset + blockBytes > src.byteLength) {
            break;
          }
          const colorOffset = format === D3DFMT_DXT1 ? blockOffset : blockOffset + 8;
          const palette = decodeDxtColorBlock(
            src,
            colorOffset,
            format === D3DFMT_DXT1
          );
          const indices = (src[colorOffset + 4] | src[colorOffset + 5] << 8 | src[colorOffset + 6] << 16 | src[colorOffset + 7] << 24) >>> 0;
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
              const colorIdx = indices >>> pixelIdx * 2 & 3;
              const [r, g, b, aDefault] = palette[colorIdx];
              let a = aDefault;
              if (format === D3DFMT_DXT3) {
                const alphaByte = src[blockOffset + (pixelIdx >> 1)];
                const a4 = (pixelIdx & 1) === 0 ? alphaByte & 15 : alphaByte >>> 4;
                a = a4 << 4 | a4;
              } else if (format === D3DFMT_DXT5) {
                const bitPos = pixelIdx * 3;
                const bytePos = blockOffset + 2 + (bitPos >> 3);
                const shift = bitPos & 7;
                const raw = src[bytePos] | (src[bytePos + 1] ?? 0) << 8;
                const aIdx = raw >>> shift & 7;
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
  var D3D9CommandConsumer = class {
    view;
    u8;
    ringBase;
    gl;
    onPresent;
    sceneState = 0 /* IDLE */;
    presentedFrames = 0;
    totalCommandsExecuted = 0;
    drawCallsExecuted = 0;
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
    // Active Resources & Pipeline Bindings (Phase 4.3)
    vertexBuffers = /* @__PURE__ */ new Map();
    indexBuffers = /* @__PURE__ */ new Map();
    streamSources = /* @__PURE__ */ new Map();
    boundIndexBufferId = 0;
    vertexDeclarations = /* @__PURE__ */ new Map();
    activeVertexDeclarationId = 0;
    textures = /* @__PURE__ */ new Map();
    textureStages = /* @__PURE__ */ new Map();
    samplerStates = /* @__PURE__ */ new Map();
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
    dispose() {
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
    getVertexBuffer(bufferId) {
      return this.vertexBuffers.get(bufferId);
    }
    getIndexBuffer(bufferId) {
      return this.indexBuffers.get(bufferId);
    }
    getStreamSource(streamNumber) {
      return this.streamSources.get(streamNumber);
    }
    getVertexDeclaration(declId) {
      return this.vertexDeclarations.get(declId);
    }
    getTexture(textureId) {
      return this.textures.get(textureId);
    }
    getSamplerState(sampler) {
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
          glMinFilter: GL_NEAREST
        };
        this.samplerStates.set(sampler, st);
      }
      return st;
    }
    destroyVertexBuffer(bufferId) {
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
      for (const [slot, binding] of this.streamSources.entries()) {
        if (binding.bufferId === bufferId) {
          this.streamSources.set(slot, {
            streamNumber: slot,
            bufferId: 0,
            offset: 0,
            stride: 0
          });
          if (this.gl && slot === 0) {
            this.gl.bindBuffer(this.gl.ARRAY_BUFFER, null);
          }
        }
      }
    }
    destroyIndexBuffer(bufferId) {
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
    destroyTexture(textureId) {
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
    destroyVertexDeclaration(declId) {
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
    mapDeclElementType(declType) {
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
    mapGlWrapMode(addrMode) {
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
    updateSamplerGlFilters(st) {
      if (st.magFilter === D3DTEXF_POINT || st.magFilter === D3DTEXF_NONE) {
        st.glMagFilter = GL_NEAREST;
      } else if (st.magFilter === D3DTEXF_LINEAR || st.magFilter === D3DTEXF_ANISOTROPIC) {
        st.glMagFilter = GL_LINEAR;
      } else {
        throw new Error(`Unsupported MAGFILTER value: ${st.magFilter}`);
      }
      const minLinear = st.minFilter === D3DTEXF_LINEAR || st.minFilter === D3DTEXF_ANISOTROPIC;
      const minPoint = st.minFilter === D3DTEXF_POINT || st.minFilter === D3DTEXF_NONE;
      if (!minLinear && !minPoint) {
        throw new Error(`Unsupported MINFILTER value: ${st.minFilter}`);
      }
      if (st.mipFilter === D3DTEXF_NONE) {
        st.glMinFilter = minLinear ? GL_LINEAR : GL_NEAREST;
      } else if (st.mipFilter === D3DTEXF_POINT) {
        st.glMinFilter = minLinear ? GL_LINEAR_MIPMAP_NEAREST : GL_NEAREST_MIPMAP_NEAREST;
      } else if (st.mipFilter === D3DTEXF_LINEAR || st.mipFilter === D3DTEXF_ANISOTROPIC) {
        st.glMinFilter = minLinear ? GL_LINEAR_MIPMAP_LINEAR : GL_NEAREST_MIPMAP_LINEAR;
      } else {
        throw new Error(`Unsupported MIPFILTER value: ${st.mipFilter}`);
      }
    }
    applySamplerStateToBoundTexture(stage) {
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
    mapPrimitiveTypeAndCount(primitiveType, primitiveCount) {
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
    bindVertexDeclarationForDraw(baseVertexIndex) {
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
        const attrByteOffset = stream.offset + baseVertexIndex * stream.stride + elem.offset;
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
    initRingHeader(capacity = 4 * 1024 * 1024) {
      const maxCap = Math.max(256, Math.min(capacity, this.u8.byteLength - this.ringBase - D3D9_RING_HEADER_SIZE));
      this.view.setUint32(this.ringBase + 0, D3D9_RING_MAGIC, true);
      this.view.setUint32(this.ringBase + 4, D3D9_RING_VERSION, true);
      this.view.setUint32(this.ringBase + 8, 0, true);
      this.view.setUint32(this.ringBase + 12, 0, true);
      this.view.setUint32(this.ringBase + 16, maxCap, true);
      this.view.setUint32(this.ringBase + 20, 0, true);
      this.view.setUint32(this.ringBase + 24, 0, true);
      this.view.setUint32(this.ringBase + 28, 0, true);
    }
    validateRingHeader() {
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
        if (cmdType >= 30 /* COUNT */) {
          throw new Error(
            `Invalid command opcode: ${cmdType} (maximum known opcode is ${30 /* COUNT */ - 1})`
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
          case 14 /* CREATE_VERTEX_BUFFER */: {
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
            const glUsage = isDynamic ? this.gl ? this.gl.DYNAMIC_DRAW : GL_DYNAMIC_DRAW : this.gl ? this.gl.STATIC_DRAW : GL_STATIC_DRAW;
            let glBuffer = null;
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
              shadowData: new Uint8Array(length)
            });
            cmd = {
              type: 14 /* CREATE_VERTEX_BUFFER */,
              bufferId,
              length,
              usage,
              fvf,
              pool
            };
            break;
          }
          case 25 /* UPDATE_VERTEX_BUFFER */: {
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
              type: 25 /* UPDATE_VERTEX_BUFFER */,
              bufferId,
              offset,
              size,
              data
            };
            break;
          }
          case 10 /* SET_STREAM_SOURCE */: {
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
                stride: 0
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
                stride
              });
              if (this.gl && entry.glBuffer && streamNumber === 0) {
                this.gl.bindBuffer(this.gl.ARRAY_BUFFER, entry.glBuffer);
              }
            }
            cmd = {
              type: 10 /* SET_STREAM_SOURCE */,
              streamNumber,
              bufferId,
              offset,
              stride
            };
            break;
          }
          case 26 /* DESTROY_VERTEX_BUFFER */: {
            if (!payloadView || payloadBytes < 4) {
              throw new Error(
                `Truncated DESTROY_VERTEX_BUFFER payload: expected 4 bytes, got ${payloadBytes}`
              );
            }
            const bufferId = payloadView.getUint32(0, true);
            this.destroyVertexBuffer(bufferId);
            cmd = {
              type: 26 /* DESTROY_VERTEX_BUFFER */,
              bufferId
            };
            break;
          }
          case 15 /* CREATE_INDEX_BUFFER */: {
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
            const glUsage = isDynamic ? this.gl ? this.gl.DYNAMIC_DRAW : GL_DYNAMIC_DRAW : this.gl ? this.gl.STATIC_DRAW : GL_STATIC_DRAW;
            const glIndexType = format === D3DFMT_INDEX32 ? GL_UNSIGNED_INT : GL_UNSIGNED_SHORT;
            const bytesPerIndex = format === D3DFMT_INDEX32 ? 4 : 2;
            let glBuffer = null;
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
              shadowData: new Uint8Array(length)
            });
            cmd = {
              type: 15 /* CREATE_INDEX_BUFFER */,
              bufferId,
              length,
              usage,
              format,
              pool
            };
            break;
          }
          case 27 /* UPDATE_INDEX_BUFFER */: {
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
              type: 27 /* UPDATE_INDEX_BUFFER */,
              bufferId,
              offset,
              size,
              data
            };
            break;
          }
          case 11 /* SET_INDICES */: {
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
              type: 11 /* SET_INDICES */,
              bufferId
            };
            break;
          }
          case 28 /* DESTROY_INDEX_BUFFER */: {
            if (!payloadView || payloadBytes < 4) {
              throw new Error(
                `Truncated DESTROY_INDEX_BUFFER payload: expected 4 bytes, got ${payloadBytes}`
              );
            }
            const bufferId = payloadView.getUint32(0, true);
            this.destroyIndexBuffer(bufferId);
            cmd = {
              type: 28 /* DESTROY_INDEX_BUFFER */,
              bufferId
            };
            break;
          }
          case 29 /* CREATE_VERTEX_DECLARATION */: {
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
            const parsedElements = [];
            const outElements = [];
            for (let i = 0; i < elementCount; i++) {
              const base = 8 + i * 8;
              const stream = payloadView.getUint16(base + 0, true);
              const offset = payloadView.getUint16(base + 2, true);
              const type = payloadView.getUint8(base + 4);
              const method = payloadView.getUint8(base + 5);
              const usage = payloadView.getUint8(base + 6);
              const usageIndex = payloadView.getUint8(base + 7);
              if (stream === 255 || type === D3DDECLTYPE_UNUSED) {
                break;
              }
              if (stream >= D3D9_MAX_STREAMS) {
                throw new Error(
                  `Invalid stream index ${stream} in vertex declaration ${declId}`
                );
              }
              const spec = this.mapDeclElementType(type);
              const elem = {
                stream,
                offset,
                type,
                method,
                usage,
                usageIndex
              };
              outElements.push(elem);
              parsedElements.push({ ...elem, spec });
            }
            this.vertexDeclarations.set(declId, {
              declId,
              elements: parsedElements
            });
            cmd = {
              type: 29 /* CREATE_VERTEX_DECLARATION */,
              declId,
              elements: outElements
            };
            break;
          }
          case 19 /* SET_VERTEX_DECLARATION */: {
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
              type: 19 /* SET_VERTEX_DECLARATION */,
              declId
            };
            break;
          }
          case 16 /* CREATE_TEXTURE */: {
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
            if (format !== D3DFMT_A8R8G8B8 && format !== D3DFMT_X8R8G8B8 && format !== D3DFMT_A8B8G8R8 && format !== D3DFMT_L8 && format !== D3DFMT_DXT1 && format !== D3DFMT_DXT3 && format !== D3DFMT_DXT5) {
              throw new Error(`Unsupported texture format: 0x${format.toString(16)}`);
            }
            let glTexture = null;
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
              levelData: /* @__PURE__ */ new Map()
            });
            cmd = {
              type: 16 /* CREATE_TEXTURE */,
              textureId,
              width,
              height,
              levels,
              usage,
              format,
              pool
            };
            break;
          }
          case 17 /* UPDATE_TEXTURE */: {
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
              type: 17 /* UPDATE_TEXTURE */,
              textureId,
              level,
              pitch,
              dataBytes,
              width,
              height,
              rgbaData
            };
            break;
          }
          case 7 /* SET_TEXTURE */: {
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
              type: 7 /* SET_TEXTURE */,
              stage,
              textureId
            };
            break;
          }
          case 6 /* SET_SAMPLER_STATE */: {
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
              type: 6 /* SET_SAMPLER_STATE */,
              sampler,
              stateType,
              value
            };
            break;
          }
          case 12 /* DRAW_PRIMITIVE */: {
            if (!payloadView || payloadBytes < 12) {
              throw new Error(
                `Truncated DRAW_PRIMITIVE payload: expected 12 bytes, got ${payloadBytes}`
              );
            }
            if (this.sceneState !== 1 /* IN_SCENE */) {
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
            const requiredBytes = stream0.offset + (startVertex + vertexCount) * stream0.stride;
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
              type: 12 /* DRAW_PRIMITIVE */,
              primitiveType,
              startVertex,
              primitiveCount,
              glMode,
              vertexCount
            };
            break;
          }
          case 13 /* DRAW_INDEXED_PRIMITIVE */: {
            if (!payloadView || payloadBytes < 24) {
              throw new Error(
                `Truncated DRAW_INDEXED_PRIMITIVE payload: expected 24 bytes, got ${payloadBytes}`
              );
            }
            if (this.sceneState !== 1 /* IN_SCENE */) {
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
            const requiredIndexBytes = indexByteOffset + vertexCount * ibEntry.bytesPerIndex;
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
              type: 13 /* DRAW_INDEXED_PRIMITIVE */,
              primitiveType,
              baseVertexIndex,
              minVertexIndex,
              numVertices,
              startIndex,
              primitiveCount,
              glMode,
              vertexCount,
              glIndexType: ibEntry.glIndexType,
              indexByteOffset
            };
            break;
          }
          case 18 /* DESTROY_RESOURCE */: {
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
              type: 18 /* DESTROY_RESOURCE */,
              resourceType,
              resourceId
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
        const newTail = (tail + packetSize) % capacity;
        this.view.setUint32(this.ringBase + 12, newTail, true);
      }
      return executed;
    }
  };
  var D3D9CommandProducer = class _D3D9CommandProducer {
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
      return new _D3D9CommandProducer(buffer, byteOffset);
    }
    writeBytesCircular(src, dstRingOffset, count, capacity) {
      const dataStart = this.ringBase + D3D9_RING_HEADER_SIZE;
      for (let i = 0; i < count; i++) {
        this.u8[dataStart + (dstRingOffset + i) % capacity] = src[i];
      }
    }
    emitRawPacket(cmdType, flags, payload, explicitPayloadBytes) {
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
      hdrView.setUint32(4, explicitPayloadBytes ?? alignedPayload, true);
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
    emitCreateVertexBuffer(bufferId, length, usage = 0, fvf = 0, pool = 0) {
      const payload = new Uint8Array(20);
      const v = new DataView(payload.buffer);
      v.setUint32(0, bufferId, true);
      v.setUint32(4, length, true);
      v.setUint32(8, usage, true);
      v.setUint32(12, fvf, true);
      v.setUint32(16, pool, true);
      this.emitRawPacket(14 /* CREATE_VERTEX_BUFFER */, 0, payload);
    }
    emitUpdateVertexBuffer(bufferId, offset, data) {
      const bytes = data instanceof Uint8Array ? data : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
      const payload = new Uint8Array(12 + bytes.byteLength);
      const v = new DataView(payload.buffer);
      v.setUint32(0, bufferId, true);
      v.setUint32(4, offset, true);
      v.setUint32(8, bytes.byteLength, true);
      payload.set(bytes, 12);
      this.emitRawPacket(25 /* UPDATE_VERTEX_BUFFER */, 0, payload);
    }
    emitSetStreamSource(streamNumber, bufferId, offset, stride) {
      const payload = new Uint8Array(16);
      const v = new DataView(payload.buffer);
      v.setUint32(0, streamNumber, true);
      v.setUint32(4, bufferId, true);
      v.setUint32(8, offset, true);
      v.setUint32(12, stride, true);
      this.emitRawPacket(10 /* SET_STREAM_SOURCE */, 0, payload);
    }
    emitDestroyVertexBuffer(bufferId) {
      const payload = new Uint8Array(4);
      const v = new DataView(payload.buffer);
      v.setUint32(0, bufferId, true);
      this.emitRawPacket(26 /* DESTROY_VERTEX_BUFFER */, 0, payload);
    }
    emitCreateIndexBuffer(bufferId, length, usage = 0, format = D3DFMT_INDEX16, pool = 0) {
      const payload = new Uint8Array(20);
      const v = new DataView(payload.buffer);
      v.setUint32(0, bufferId, true);
      v.setUint32(4, length, true);
      v.setUint32(8, usage, true);
      v.setUint32(12, format, true);
      v.setUint32(16, pool, true);
      this.emitRawPacket(15 /* CREATE_INDEX_BUFFER */, 0, payload);
    }
    emitUpdateIndexBuffer(bufferId, offset, data) {
      const bytes = data instanceof Uint8Array ? data : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
      const payload = new Uint8Array(12 + bytes.byteLength);
      const v = new DataView(payload.buffer);
      v.setUint32(0, bufferId, true);
      v.setUint32(4, offset, true);
      v.setUint32(8, bytes.byteLength, true);
      payload.set(bytes, 12);
      this.emitRawPacket(27 /* UPDATE_INDEX_BUFFER */, 0, payload);
    }
    emitSetIndices(bufferId) {
      const payload = new Uint8Array(4);
      const v = new DataView(payload.buffer);
      v.setUint32(0, bufferId, true);
      this.emitRawPacket(11 /* SET_INDICES */, 0, payload);
    }
    emitDestroyIndexBuffer(bufferId) {
      const payload = new Uint8Array(4);
      const v = new DataView(payload.buffer);
      v.setUint32(0, bufferId, true);
      this.emitRawPacket(28 /* DESTROY_INDEX_BUFFER */, 0, payload);
    }
    emitCreateVertexDeclaration(declId, elements) {
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
      this.emitRawPacket(29 /* CREATE_VERTEX_DECLARATION */, 0, payload);
    }
    emitSetVertexDeclaration(declId) {
      const payload = new Uint8Array(4);
      const v = new DataView(payload.buffer);
      v.setUint32(0, declId, true);
      this.emitRawPacket(19 /* SET_VERTEX_DECLARATION */, 0, payload);
    }
    emitCreateTexture(textureId, width, height, levels = 1, usage = 0, format = D3DFMT_A8R8G8B8, pool = 0) {
      const payload = new Uint8Array(28);
      const v = new DataView(payload.buffer);
      v.setUint32(0, textureId, true);
      v.setUint32(4, width, true);
      v.setUint32(8, height, true);
      v.setUint32(12, levels, true);
      v.setUint32(16, usage, true);
      v.setUint32(20, format, true);
      v.setUint32(24, pool, true);
      this.emitRawPacket(16 /* CREATE_TEXTURE */, 0, payload);
    }
    emitUpdateTexture(textureId, level, pitch, width, height, data) {
      const bytes = data instanceof Uint8Array ? data : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
      const payload = new Uint8Array(24 + bytes.byteLength);
      const v = new DataView(payload.buffer);
      v.setUint32(0, textureId, true);
      v.setUint32(4, level, true);
      v.setUint32(8, pitch, true);
      v.setUint32(12, bytes.byteLength, true);
      v.setUint32(16, width, true);
      v.setUint32(20, height, true);
      payload.set(bytes, 24);
      this.emitRawPacket(17 /* UPDATE_TEXTURE */, 0, payload);
    }
    emitSetTexture(stage, textureId) {
      const payload = new Uint8Array(8);
      const v = new DataView(payload.buffer);
      v.setUint32(0, stage, true);
      v.setUint32(4, textureId, true);
      this.emitRawPacket(7 /* SET_TEXTURE */, 0, payload);
    }
    emitSetSamplerState(sampler, stateType, value) {
      const payload = new Uint8Array(12);
      const v = new DataView(payload.buffer);
      v.setUint32(0, sampler, true);
      v.setUint32(4, stateType, true);
      v.setUint32(8, value, true);
      this.emitRawPacket(6 /* SET_SAMPLER_STATE */, 0, payload);
    }
    emitDrawPrimitive(primitiveType, startVertex, primitiveCount) {
      const payload = new Uint8Array(12);
      const v = new DataView(payload.buffer);
      v.setUint32(0, primitiveType, true);
      v.setUint32(4, startVertex, true);
      v.setUint32(8, primitiveCount, true);
      this.emitRawPacket(12 /* DRAW_PRIMITIVE */, 0, payload);
    }
    emitDrawIndexedPrimitive(primitiveType, baseVertexIndex, minVertexIndex, numVertices, startIndex, primitiveCount) {
      const payload = new Uint8Array(24);
      const v = new DataView(payload.buffer);
      v.setUint32(0, primitiveType, true);
      v.setInt32(4, baseVertexIndex, true);
      v.setUint32(8, minVertexIndex, true);
      v.setUint32(12, numVertices, true);
      v.setUint32(16, startIndex, true);
      v.setUint32(20, primitiveCount, true);
      this.emitRawPacket(13 /* DRAW_INDEXED_PRIMITIVE */, 0, payload);
    }
    emitDestroyResource(resourceType, resourceId) {
      const payload = new Uint8Array(8);
      const v = new DataView(payload.buffer);
      v.setUint32(0, resourceType, true);
      v.setUint32(4, resourceId, true);
      this.emitRawPacket(18 /* DESTROY_RESOURCE */, 0, payload);
    }
  };
  return __toCommonJS(d3d9_consumer_exports);
})();
