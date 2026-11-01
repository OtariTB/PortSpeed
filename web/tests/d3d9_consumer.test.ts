import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  D3D9CommandConsumer,
  D3D9CommandProducer,
  D3D9CmdType,
  D3DCLEAR_TARGET,
  D3DCLEAR_ZBUFFER,
  D3DCLEAR_STENCIL,
  SceneState,
  D3D9_RING_MAGIC,
  D3D9_RING_VERSION,
  D3D9_RING_HEADER_SIZE,
  D3DRS_ZENABLE,
  D3DRS_ZWRITEENABLE,
  D3DRS_SRCBLEND,
  D3DRS_DESTBLEND,
  D3DRS_CULLMODE,
  D3DRS_ZFUNC,
  D3DRS_ALPHABLENDENABLE,
  D3DRS_COLORWRITEENABLE,
  D3DZB_FALSE,
  D3DZB_TRUE,
  D3DZB_USEW,
  D3DCMP_NEVER,
  D3DCMP_LESS,
  D3DCMP_EQUAL,
  D3DCMP_LESSEQUAL,
  D3DCMP_GREATER,
  D3DCMP_NOTEQUAL,
  D3DCMP_GREATEREQUAL,
  D3DCMP_ALWAYS,
  D3DCULL_NONE,
  D3DCULL_CW,
  D3DCULL_CCW,
  D3DBLEND_ZERO,
  D3DBLEND_ONE,
  D3DBLEND_SRCCOLOR,
  D3DBLEND_INVSRCCOLOR,
  D3DBLEND_SRCALPHA,
  D3DBLEND_INVSRCALPHA,
  D3DBLEND_DESTALPHA,
  D3DBLEND_INVDESTALPHA,
  D3DBLEND_DESTCOLOR,
  D3DBLEND_INVDESTCOLOR,
  D3DBLEND_SRCALPHASAT,
  D3DBLEND_BLENDFACTOR,
  D3DBLEND_INVBLENDFACTOR,
  D3DCOLORWRITEENABLE_RED,
  D3DCOLORWRITEENABLE_GREEN,
  D3DCOLORWRITEENABLE_BLUE,
  D3DCOLORWRITEENABLE_ALPHA,
  D3DUSAGE_WRITEONLY,
  D3DUSAGE_DYNAMIC,
  D3DPOOL_DEFAULT,
  D3DPOOL_MANAGED,
  GL_STATIC_DRAW,
  GL_DYNAMIC_DRAW,
  D3DFMT_INDEX16,
  D3DFMT_INDEX32,
  D3DFMT_A8R8G8B8,
  D3DFMT_X8R8G8B8,
  D3DFMT_DXT1,
  D3DPT_TRIANGLELIST,
  D3DPT_TRIANGLESTRIP,
  D3DDECLTYPE_FLOAT3,
  D3DDECLTYPE_D3DCOLOR,
  D3DDECLTYPE_FLOAT2,
  D3DDECLTYPE_UNUSED,
  D3DDECLUSAGE_POSITION,
  D3DDECLUSAGE_COLOR,
  D3DDECLUSAGE_TEXCOORD,
  D3DSAMP_ADDRESSU,
  D3DSAMP_ADDRESSV,
  D3DSAMP_MAGFILTER,
  D3DSAMP_MINFILTER,
  D3DSAMP_MIPFILTER,
  D3DTADDRESS_CLAMP,
  D3DTADDRESS_MIRROR,
  D3DTEXF_LINEAR,
  D3DTEXF_POINT,
  GL_UNSIGNED_SHORT,
  GL_UNSIGNED_INT,
  GL_TRIANGLES,
  GL_TRIANGLE_STRIP,
  GL_CLAMP_TO_EDGE,
  GL_MIRRORED_REPEAT,
  GL_LINEAR,
  GL_LINEAR_MIPMAP_NEAREST,
} from '../src/d3d9_consumer.ts';

test('D3D9 consumer validates valid ring header', () => {
  const cap = 256;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  D3D9CommandProducer.initRing(buf, 0, cap);

  const consumer = new D3D9CommandConsumer(buf, 0);
  const hdr = consumer.validateRingHeader();
  assert.equal(hdr.magic, D3D9_RING_MAGIC);
  assert.equal(hdr.version, D3D9_RING_VERSION);
  assert.equal(hdr.head, 0);
  assert.equal(hdr.tail, 0);
  assert.equal(hdr.capacity, cap);
  assert.equal(consumer.getPendingBytes(), 0);
});

test('D3D9 consumer rejects invalid magic or unsupported version', () => {
  const cap = 256;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  D3D9CommandProducer.initRing(buf, 0, cap);
  const view = new DataView(buf);

  // Corrupt magic
  view.setUint32(0, 0xdeadbeef, true);
  const c1 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c1.validateRingHeader(), /Invalid ring buffer magic/);

  // Restore magic, corrupt version
  view.setUint32(0, D3D9_RING_MAGIC, true);
  view.setUint32(4, 2, true);
  const c2 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c2.validateRingHeader(), /Unsupported ring buffer version/);
});

test('D3D9 consumer rejects out-of-bounds capacity or head/tail pointers', () => {
  const cap = 256;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  D3D9CommandProducer.initRing(buf, 0, cap);
  const view = new DataView(buf);

  // Capacity exceeds allocated buffer
  view.setUint32(16, cap + 1024, true);
  const c1 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c1.validateRingHeader(), /Invalid ring buffer capacity/);

  // Head out of bounds
  view.setUint32(16, cap, true);
  view.setUint32(8, cap + 1, true);
  const c2 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c2.validateRingHeader(), /Ring buffer pointer out of bounds/);

  // Tail out of bounds
  view.setUint32(8, 0, true);
  view.setUint32(12, cap + 1, true);
  const c3 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c3.validateRingHeader(), /Ring buffer pointer out of bounds/);
});

test('D3D9 consumer processes BeginScene, Clear, EndScene, Present sequence', () => {
  const cap = 1024;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);

  producer.emitBeginScene();
  // Clear: flags = TARGET|ZBUFFER|STENCIL (7), color = 0x80336699 (ARGB), z = 1.0, stencil = 0
  const argbColor = 0x80336699;
  producer.emitClear(D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL, argbColor, 1.0, 0);
  producer.emitEndScene();
  producer.emitPresent(0, 0, 1280, 720);

  let presentCalled = false;
  const consumer = new D3D9CommandConsumer(buf, 0, {
    onPresent: (frame, cmd) => {
      presentCalled = true;
      assert.equal(frame, 1);
      assert.equal(cmd.srcRect.w, 1280);
      assert.equal(cmd.srcRect.h, 720);
    },
  });

  assert.equal(consumer.sceneState, SceneState.IDLE);
  const cmds = consumer.processCommands();

  assert.equal(cmds.length, 4);
  assert.equal(cmds[0].type, D3D9CmdType.BEGIN_SCENE);
  assert.equal(cmds[1].type, D3D9CmdType.CLEAR);
  assert.equal(cmds[2].type, D3D9CmdType.END_SCENE);
  assert.equal(cmds[3].type, D3D9CmdType.PRESENT);

  const clr = cmds[1];
  if (clr.type === D3D9CmdType.CLEAR) {
    assert.equal(clr.flags, 7);
    assert.equal(clr.color, argbColor);
    assert.equal(clr.a, 0x80 / 255.0);
    assert.equal(clr.r, 0x33 / 255.0);
    assert.equal(clr.g, 0x66 / 255.0);
    assert.equal(clr.b, 0x99 / 255.0);
    assert.equal(clr.z, 1.0);
    assert.equal(clr.stencil, 0);
  }

  assert.equal(consumer.sceneState, SceneState.IDLE);
  assert.equal(consumer.presentedFrames, 1);
  assert.equal(consumer.totalCommandsExecuted, 4);
  assert.equal(consumer.getPendingBytes(), 0);
  assert.equal(presentCalled, true);
});

test('D3D9 consumer enforces strict scene state machine', () => {
  const cap = 512;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);

  // Double BeginScene
  producer.emitBeginScene();
  producer.emitBeginScene();
  const c1 = new D3D9CommandConsumer(buf, 0);
  assert.throws(
    () => c1.processCommands(),
    /Invalid state transition: BEGIN_SCENE called while already IN_SCENE/
  );

  // EndScene when IDLE
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitEndScene();
  const c2 = new D3D9CommandConsumer(buf, 0);
  assert.throws(
    () => c2.processCommands(),
    /Invalid state transition: END_SCENE called while IDLE/
  );

  // Present while IN_SCENE
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitBeginScene();
  producer.emitPresent(0, 0, 800, 600);
  const c3 = new D3D9CommandConsumer(buf, 0);
  assert.throws(
    () => c3.processCommands(),
    /Invalid state transition: PRESENT called while IN_SCENE/
  );
});

test('D3D9 consumer rejects malformed packets and invalid opcodes', () => {
  const cap = 512;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const view = new DataView(buf);

  // Invalid opcode 99
  const payload = new Uint8Array(4);
  producer.emitRawPacket(99, 0, payload);
  const c1 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c1.processCommands(), /Invalid command opcode: 99/);

  // Truncated packet header (pending < 8 bytes)
  D3D9CommandProducer.initRing(buf, 0, cap);
  view.setUint32(8, 4, true); // head = 4, tail = 0 => pending = 4
  const c2 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c2.processCommands(), /Truncated command packet header: 4 bytes pending/);

  // Truncated packet payload (packetSize > pending)
  D3D9CommandProducer.initRing(buf, 0, cap);
  // Write header requesting 32 bytes payload, but only advance head by 16 bytes
  const dataStart = D3D9_RING_HEADER_SIZE;
  view.setUint16(dataStart + 0, D3D9CmdType.CLEAR, true);
  view.setUint16(dataStart + 2, 0, true);
  view.setUint32(dataStart + 4, 32, true); // payload_bytes = 32 => packetSize = 40
  view.setUint32(8, 16, true); // head = 16
  const c3 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c3.processCommands(), /Truncated command packet for opcode 1: 40 bytes required, 16 available/);

  // Truncated CLEAR payload (< 20 bytes)
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitRawPacket(D3D9CmdType.CLEAR, 0, new Uint8Array(8));
  const c4 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c4.processCommands(), /Truncated CLEAR payload: expected at least 20 bytes/);
});

test('D3D9 consumer handles circular ring buffer wraparound across boundaries', () => {
  // Use a compact capacity (128 bytes) so each 68-byte frame wraps around the boundary
  const cap = 128;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  // 1. Write and consume a frame: BeginScene (8) + Clear (28) = 36 bytes.
  // Head becomes 36.
  producer.emitBeginScene();
  producer.emitClear(D3DCLEAR_TARGET, 0xff00ff00, 1.0, 0);
  let cmds = consumer.processCommands();
  assert.equal(cmds.length, 2);
  assert.equal(consumer.getPendingBytes(), 0);
  assert.equal(consumer.sceneState, SceneState.IN_SCENE);

  // 2. Next: EndScene (8) + Present (24) = 32 bytes.
  // Head becomes 68.
  producer.emitEndScene();
  producer.emitPresent(0, 0, 1920, 1080);
  assert.equal(consumer.getPendingBytes(), 32);

  cmds = consumer.processCommands();
  assert.equal(cmds.length, 2);
  assert.equal(cmds[0].type, D3D9CmdType.END_SCENE);
  assert.equal(cmds[1].type, D3D9CmdType.PRESENT);
  assert.equal(consumer.sceneState, SceneState.IDLE);
  assert.equal(consumer.getPendingBytes(), 0);

  // 3. Perform 20 successive frames to verify sustained wraparound cycling:
  // Each frame is 68 bytes. In a 128-byte ring, every frame wraps around the boundary!
  for (let frame = 1; frame <= 20; frame++) {
    producer.emitBeginScene();
    producer.emitClear(D3DCLEAR_TARGET, (0xff000000 | frame) >>> 0, 1.0, 0);
    producer.emitEndScene();
    producer.emitPresent(0, 0, 1920, 1080);

    const fCmds = consumer.processCommands();
    assert.equal(fCmds.length, 4);
    assert.equal(fCmds[0].type, D3D9CmdType.BEGIN_SCENE);
    assert.equal(fCmds[1].type, D3D9CmdType.CLEAR);
    assert.equal(fCmds[2].type, D3D9CmdType.END_SCENE);
    assert.equal(fCmds[3].type, D3D9CmdType.PRESENT);
    assert.equal(consumer.sceneState, SceneState.IDLE);
    assert.equal(consumer.getPendingBytes(), 0);

    const clrCmd = fCmds[1];
    if (clrCmd.type === D3D9CmdType.CLEAR) {
      assert.equal(clrCmd.color, (0xff000000 | frame) >>> 0);
    }
  }
  assert.equal(consumer.presentedFrames, 21);
});

test('D3D9 consumer processes SET_VIEWPORT and calculates WebGL2 coordinates', () => {
  const cap = 512;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  // Emit standard viewport: x=0, y=0, w=1280, h=720, minZ=0.0, maxZ=1.0
  producer.emitSetViewport(0, 0, 1280, 720, 0.0, 1.0);
  let cmds = consumer.processCommands();
  assert.equal(cmds.length, 1);
  assert.equal(cmds[0].type, D3D9CmdType.SET_VIEWPORT);
  assert.equal(consumer.viewport.x, 0);
  assert.equal(consumer.viewport.y, 0);
  assert.equal(consumer.viewport.width, 1280);
  assert.equal(consumer.viewport.height, 720);
  assert.equal(consumer.viewport.minZ, 0.0);
  assert.equal(consumer.viewport.maxZ, 1.0);
  assert.equal(consumer.viewport.glX, 0);
  assert.equal(consumer.viewport.glY, 0);

  // Emit nontrivial sub-viewport: x=50, y=30, w=400, h=300 on virtual target 720
  // D3D9 (top-left) to GL (bottom-left): glY = 720 - (30 + 300) = 390
  producer.emitSetViewport(50, 30, 400, 300, 0.1, 0.9);
  cmds = consumer.processCommands();
  assert.equal(cmds.length, 1);
  assert.equal(consumer.viewport.x, 50);
  assert.equal(consumer.viewport.y, 30);
  assert.equal(consumer.viewport.width, 400);
  assert.equal(consumer.viewport.height, 300);
  assert.equal(consumer.viewport.glX, 50);
  assert.equal(consumer.viewport.glY, 390);
  assert.equal(consumer.viewport.glWidth, 400);
  assert.equal(consumer.viewport.glHeight, 300);
  assert.equal(Math.round(consumer.viewport.minZ * 10), 1);
  assert.equal(Math.round(consumer.viewport.maxZ * 10), 9);
});

test('D3D9 consumer rejects invalid SET_VIEWPORT depth ranges and truncated packets', () => {
  const cap = 512;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);

  // Invalid minZ > maxZ
  producer.emitSetViewport(0, 0, 640, 480, 0.8, 0.2);
  const c1 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c1.processCommands(), /Invalid viewport depth range/);

  // Invalid minZ < 0
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitSetViewport(0, 0, 640, 480, -0.1, 1.0);
  const c2 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c2.processCommands(), /Invalid viewport depth range/);

  // Truncated payload (< 24 bytes)
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitRawPacket(D3D9CmdType.SET_VIEWPORT, 0, new Uint8Array(16));
  const c3 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c3.processCommands(), /Truncated SET_VIEWPORT payload: expected 24 bytes/);
});

test('D3D9 consumer processes all 8 supported render states and maintains defaults', () => {
  const cap = 1024;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  // Verify authentic Direct3D 9 initial defaults
  assert.equal(consumer.renderStates.zEnable, true);
  assert.equal(consumer.renderStates.zWriteEnable, true);
  assert.equal(consumer.renderStates.zFunc, D3DCMP_LESSEQUAL);
  assert.equal(consumer.renderStates.cullMode, D3DCULL_CCW);
  assert.equal(consumer.renderStates.alphaBlendEnable, false);
  assert.equal(consumer.renderStates.srcBlend, D3DBLEND_ONE);
  assert.equal(consumer.renderStates.destBlend, D3DBLEND_ZERO);
  assert.equal(consumer.renderStates.colorWriteEnable, 0x0f);

  // 1. ZENABLE
  producer.emitSetRenderState(D3DRS_ZENABLE, D3DZB_FALSE);
  // 2. ZWRITEENABLE
  producer.emitSetRenderState(D3DRS_ZWRITEENABLE, 0);
  // 3. ZFUNC
  producer.emitSetRenderState(D3DRS_ZFUNC, D3DCMP_GREATER);
  // 4. CULLMODE
  producer.emitSetRenderState(D3DRS_CULLMODE, D3DCULL_CW);
  // 5. ALPHABLENDENABLE
  producer.emitSetRenderState(D3DRS_ALPHABLENDENABLE, 1);
  // 6. SRCBLEND
  producer.emitSetRenderState(D3DRS_SRCBLEND, D3DBLEND_SRCALPHA);
  // 7. DESTBLEND
  producer.emitSetRenderState(D3DRS_DESTBLEND, D3DBLEND_INVSRCALPHA);
  // 8. COLORWRITEENABLE (R | B = 1 | 4 = 5)
  producer.emitSetRenderState(D3DRS_COLORWRITEENABLE, D3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_BLUE);

  const cmds = consumer.processCommands();
  assert.equal(cmds.length, 8);

  assert.equal(consumer.renderStates.zEnable, false);
  assert.equal(consumer.renderStates.zWriteEnable, false);
  assert.equal(consumer.renderStates.zFunc, D3DCMP_GREATER);
  assert.equal(consumer.renderStates.cullMode, D3DCULL_CW);
  assert.equal(consumer.renderStates.alphaBlendEnable, true);
  assert.equal(consumer.renderStates.srcBlend, D3DBLEND_SRCALPHA);
  assert.equal(consumer.renderStates.destBlend, D3DBLEND_INVSRCALPHA);
  assert.equal(consumer.renderStates.colorWriteEnable, 5);
});

test('D3D9 consumer rejects unsupported render states and values explicitly', () => {
  const cap = 512;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);

  // 1. Unsupported render state: FOGENABLE (28)
  producer.emitSetRenderState(28, 1);
  const c1 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c1.processCommands(), /Unsupported render state: 28/);

  // 2. Unsupported ZENABLE value: D3DZB_USEW (2)
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitSetRenderState(D3DRS_ZENABLE, D3DZB_USEW);
  const c2 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c2.processCommands(), /Unsupported ZENABLE value: 2/);

  // 3. Unsupported ZFUNC value: 0 or 9
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitSetRenderState(D3DRS_ZFUNC, 9);
  const c3 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c3.processCommands(), /Unsupported ZFUNC value: 9/);

  // 4. Unsupported CULLMODE value: 4
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitSetRenderState(D3DRS_CULLMODE, 4);
  const c4 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c4.processCommands(), /Unsupported CULLMODE value: 4/);

  // 5. Unsupported blend factor: 12 (D3DBLEND_BOTHSRCALPHA)
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitSetRenderState(D3DRS_SRCBLEND, 12);
  const c5 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c5.processCommands(), /Unsupported SRCBLEND value: 12/);

  // 6. Unsupported COLORWRITEENABLE value (> 15)
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitSetRenderState(D3DRS_COLORWRITEENABLE, 16);
  const c6 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c6.processCommands(), /Unsupported COLORWRITEENABLE value: 16/);

  // 7. Truncated SET_RENDER_STATE payload (< 8 bytes)
  D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitRawPacket(D3D9CmdType.SET_RENDER_STATE, 0, new Uint8Array(4));
  const c7 = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => c7.processCommands(), /Truncated SET_RENDER_STATE payload: expected 8 bytes/);
});

test('D3D9 consumer handles vertex buffer creation, sub-data updates, and destruction', () => {
  const cap = 2048;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  // 1. Create static vertex buffer (id=1, length=64, usage=WRITEONLY, fvf=0x142, pool=MANAGED)
  producer.emitCreateVertexBuffer(1, 64, D3DUSAGE_WRITEONLY, 0x142, D3DPOOL_MANAGED);
  // 2. Create dynamic vertex buffer (id=2, length=128, usage=DYNAMIC|WRITEONLY, fvf=0, pool=DEFAULT)
  producer.emitCreateVertexBuffer(2, 128, D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY, 0, D3DPOOL_DEFAULT);

  let cmds = consumer.processCommands();
  assert.equal(cmds.length, 2);
  assert.equal(cmds[0].type, D3D9CmdType.CREATE_VERTEX_BUFFER);
  assert.equal(cmds[1].type, D3D9CmdType.CREATE_VERTEX_BUFFER);

  const vb1 = consumer.getVertexBuffer(1);
  assert.ok(vb1);
  assert.equal(vb1.length, 64);
  assert.equal(vb1.usage, D3DUSAGE_WRITEONLY);
  assert.equal(vb1.fvf, 0x142);
  assert.equal(vb1.pool, D3DPOOL_MANAGED);
  assert.equal(vb1.glUsage, GL_STATIC_DRAW);

  const vb2 = consumer.getVertexBuffer(2);
  assert.ok(vb2);
  assert.equal(vb2.length, 128);
  assert.equal(vb2.glUsage, GL_DYNAMIC_DRAW);

  // 3. Upload initial 24 bytes (6 floats) to vb1 at offset 0
  const vertsA = new Float32Array([1.0, 2.0, 3.0, -4.0, 5.5, 6.25]);
  producer.emitUpdateVertexBuffer(1, 0, vertsA);

  // 4. Upload sub-range 12 bytes (3 floats) to vb1 at byte offset 24
  const vertsB = new Float32Array([10.0, 20.0, 30.0]);
  producer.emitUpdateVertexBuffer(1, 24, vertsB);

  cmds = consumer.processCommands();
  assert.equal(cmds.length, 2);
  assert.equal(cmds[0].type, D3D9CmdType.UPDATE_VERTEX_BUFFER);
  assert.equal(cmds[1].type, D3D9CmdType.UPDATE_VERTEX_BUFFER);

  const shadowFloats = new Float32Array(
    vb1.shadowData.buffer,
    vb1.shadowData.byteOffset,
    9
  );
  assert.deepEqual(Array.from(shadowFloats), [
    1.0, 2.0, 3.0, -4.0, 5.5, 6.25, 10.0, 20.0, 30.0,
  ]);

  // 5. Destroy vb1 via DESTROY_VERTEX_BUFFER and vb2 via DESTROY_RESOURCE (type=1)
  producer.emitDestroyVertexBuffer(1);
  producer.emitDestroyResource(1, 2);
  cmds = consumer.processCommands();
  assert.equal(cmds.length, 2);
  assert.equal(cmds[0].type, D3D9CmdType.DESTROY_VERTEX_BUFFER);
  assert.equal(cmds[1].type, D3D9CmdType.DESTROY_RESOURCE);
  assert.equal(consumer.getVertexBuffer(1), undefined);
  assert.equal(consumer.getVertexBuffer(2), undefined);
});

test('D3D9 consumer tracks SET_STREAM_SOURCE bindings and unbinds on destruction', () => {
  const cap = 1024;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  producer.emitCreateVertexBuffer(10, 256, D3DUSAGE_WRITEONLY, 0, D3DPOOL_DEFAULT);
  producer.emitCreateVertexBuffer(20, 512, D3DUSAGE_DYNAMIC, 0, D3DPOOL_DEFAULT);

  // Bind stream 0 -> buffer 10 (offset 32, stride 24) and stream 1 -> buffer 20 (offset 0, stride 16)
  producer.emitSetStreamSource(0, 10, 32, 24);
  producer.emitSetStreamSource(1, 20, 0, 16);

  let cmds = consumer.processCommands();
  assert.equal(cmds.length, 4);

  const s0 = consumer.getStreamSource(0);
  assert.ok(s0);
  assert.equal(s0.bufferId, 10);
  assert.equal(s0.offset, 32);
  assert.equal(s0.stride, 24);

  const s1 = consumer.getStreamSource(1);
  assert.ok(s1);
  assert.equal(s1.bufferId, 20);
  assert.equal(s1.offset, 0);
  assert.equal(s1.stride, 16);

  // Explicit unbind of stream 1 with bufferId = 0
  producer.emitSetStreamSource(1, 0, 0, 0);
  consumer.processCommands();
  assert.equal(consumer.getStreamSource(1)?.bufferId, 0);
  assert.equal(consumer.getStreamSource(1)?.stride, 0);

  // Destroying buffer 10 automatically unbinds stream 0
  producer.emitDestroyVertexBuffer(10);
  consumer.processCommands();
  assert.equal(consumer.getStreamSource(0)?.bufferId, 0);
  assert.equal(consumer.getStreamSource(0)?.offset, 0);
  assert.equal(consumer.getStreamSource(0)?.stride, 0);
});

test('D3D9 consumer handles UPDATE_VERTEX_BUFFER across circular ring wraparound', () => {
  const cap = 128;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  // Create VB (8 + 20 = 28 bytes) + SetStreamSource (8 + 16 = 24 bytes) = 52 bytes
  producer.emitCreateVertexBuffer(5, 64, D3DUSAGE_DYNAMIC, 0, D3DPOOL_DEFAULT);
  producer.emitSetStreamSource(0, 5, 0, 16);
  consumer.processCommands();

  // Repeatedly upload 48-byte payloads (8 hdr + 12 update hdr + 48 data = 68 bytes per packet)
  // In a 128-byte ring, every update wraps across the end of the ring buffer!
  for (let iter = 1; iter <= 10; iter++) {
    const payload = new Uint8Array(48);
    for (let i = 0; i < 48; i++) {
      payload[i] = (iter * 13 + i) & 0xff;
    }
    producer.emitUpdateVertexBuffer(5, 8, payload);
    const cmds = consumer.processCommands();
    assert.equal(cmds.length, 1);
    assert.equal(cmds[0].type, D3D9CmdType.UPDATE_VERTEX_BUFFER);

    const vb = consumer.getVertexBuffer(5)!;
    assert.deepEqual(Array.from(vb.shadowData.slice(8, 56)), Array.from(payload));
  }
});

test('D3D9 consumer rejects invalid vertex buffer and stream source commands', () => {
  const cap = 512;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);

  // 1. CREATE_VERTEX_BUFFER with bufferId = 0
  let producer = D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitCreateVertexBuffer(0, 64);
  let consumer = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => consumer.processCommands(), /Invalid vertex buffer ID: 0/);

  // 2. CREATE_VERTEX_BUFFER with length = 0
  producer = D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitCreateVertexBuffer(1, 0);
  consumer = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => consumer.processCommands(), /Invalid vertex buffer length: 0/);

  // 3. Duplicate bufferId
  producer = D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitCreateVertexBuffer(1, 64);
  producer.emitCreateVertexBuffer(1, 64);
  consumer = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => consumer.processCommands(), /Duplicate vertex buffer ID: 1/);

  // 4. UPDATE_VERTEX_BUFFER on unknown bufferId
  producer = D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitUpdateVertexBuffer(99, 0, new Uint8Array([1, 2, 3, 4]));
  consumer = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => consumer.processCommands(), /Unknown vertex buffer ID in UPDATE_VERTEX_BUFFER: 99/);

  // 5. UPDATE_VERTEX_BUFFER out of bounds (offset + size > length)
  producer = D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitCreateVertexBuffer(1, 16);
  producer.emitUpdateVertexBuffer(1, 12, new Uint8Array(8)); // 12 + 8 = 20 > 16
  consumer = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => consumer.processCommands(), /Vertex buffer update out of bounds/);

  // 6. SET_STREAM_SOURCE with invalid stream slot (>= 16)
  producer = D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitSetStreamSource(16, 0, 0, 0);
  consumer = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => consumer.processCommands(), /Invalid stream number: 16/);

  // 7. SET_STREAM_SOURCE with unknown bufferId
  producer = D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitSetStreamSource(0, 42, 0, 16);
  consumer = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => consumer.processCommands(), /Unknown vertex buffer ID in SET_STREAM_SOURCE: 42/);

  // 8. DESTROY_VERTEX_BUFFER with unknown bufferId
  producer = D3D9CommandProducer.initRing(buf, 0, cap);
  producer.emitDestroyVertexBuffer(77);
  consumer = new D3D9CommandConsumer(buf, 0);
  assert.throws(() => consumer.processCommands(), /Unknown vertex buffer ID in DESTROY_VERTEX_BUFFER: 77/);
});

test('D3D9 consumer handles index buffer lifecycle and SET_INDICES binding', () => {
  const cap = 2048;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  // Create 16-bit IB (id=1, 64 bytes) and 32-bit IB (id=2, 128 bytes)
  producer.emitCreateIndexBuffer(1, 64, D3DUSAGE_WRITEONLY, D3DFMT_INDEX16, D3DPOOL_MANAGED);
  producer.emitCreateIndexBuffer(2, 128, D3DUSAGE_DYNAMIC, D3DFMT_INDEX32, D3DPOOL_DEFAULT);

  // Upload 6 uint16 indices to IB 1
  const indices16 = new Uint16Array([0, 1, 2, 2, 1, 3]);
  producer.emitUpdateIndexBuffer(1, 0, indices16);

  // Bind IB 1
  producer.emitSetIndices(1);

  let cmds = consumer.processCommands();
  assert.equal(cmds.length, 4);

  const ib1 = consumer.getIndexBuffer(1)!;
  assert.ok(ib1);
  assert.equal(ib1.format, D3DFMT_INDEX16);
  assert.equal(ib1.glIndexType, GL_UNSIGNED_SHORT);
  assert.equal(ib1.bytesPerIndex, 2);
  assert.equal(consumer.boundIndexBufferId, 1);

  const shadow16 = new Uint16Array(ib1.shadowData.buffer, ib1.shadowData.byteOffset, 6);
  assert.deepEqual(Array.from(shadow16), [0, 1, 2, 2, 1, 3]);

  const ib2 = consumer.getIndexBuffer(2)!;
  assert.ok(ib2);
  assert.equal(ib2.format, D3DFMT_INDEX32);
  assert.equal(ib2.glIndexType, GL_UNSIGNED_INT);
  assert.equal(ib2.bytesPerIndex, 4);

  // Destroying bound IB 1 automatically unbinds boundIndexBufferId
  producer.emitDestroyIndexBuffer(1);
  producer.emitDestroyResource(2, 2);
  consumer.processCommands();
  assert.equal(consumer.boundIndexBufferId, 0);
  assert.equal(consumer.getIndexBuffer(1), undefined);
  assert.equal(consumer.getIndexBuffer(2), undefined);
});

test('D3D9 consumer handles vertex declarations and element attribute specs', () => {
  const cap = 1024;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  producer.emitCreateVertexDeclaration(1, [
    { stream: 0, offset: 0, type: D3DDECLTYPE_FLOAT3, method: 0, usage: D3DDECLUSAGE_POSITION, usageIndex: 0 },
    { stream: 0, offset: 12, type: D3DDECLTYPE_D3DCOLOR, method: 0, usage: D3DDECLUSAGE_COLOR, usageIndex: 0 },
    { stream: 0, offset: 16, type: D3DDECLTYPE_FLOAT2, method: 0, usage: D3DDECLUSAGE_TEXCOORD, usageIndex: 0 },
    { stream: 0xff, offset: 0, type: D3DDECLTYPE_UNUSED, method: 0, usage: 0, usageIndex: 0 }, // D3DDECL_END
  ]);
  producer.emitSetVertexDeclaration(1);

  const cmds = consumer.processCommands();
  assert.equal(cmds.length, 2);
  assert.equal(consumer.activeVertexDeclarationId, 1);

  const decl = consumer.getVertexDeclaration(1)!;
  assert.ok(decl);
  // Sentinel D3DDECL_END is stripped automatically
  assert.equal(decl.elements.length, 3);
  assert.equal(decl.elements[0].spec.size, 3);
  assert.equal(decl.elements[0].spec.normalized, false);
  assert.equal(decl.elements[1].spec.size, 4);
  assert.equal(decl.elements[1].spec.normalized, true);
  assert.equal(decl.elements[2].spec.size, 2);

  // Destroy via DESTROY_RESOURCE (type=4)
  producer.emitDestroyResource(4, 1);
  consumer.processCommands();
  assert.equal(consumer.activeVertexDeclarationId, 0);
  assert.equal(consumer.getVertexDeclaration(1), undefined);
});

test('D3D9 consumer handles texture creation, format conversion (ARGB/DXT1), and sampler states', () => {
  const cap = 4096;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  // 1. Create 2x1 A8R8G8B8 texture (id=1) and 4x4 DXT1 texture (id=2)
  producer.emitCreateTexture(1, 2, 1, 1, 0, D3DFMT_A8R8G8B8, D3DPOOL_MANAGED);
  producer.emitCreateTexture(2, 4, 4, 1, 0, D3DFMT_DXT1, D3DPOOL_MANAGED);

  // 2. Upload 2 pixels of A8R8G8B8 (little-endian BGRA bytes: [B, G, R, A])
  // Pixel 0: R=255, G=128, B=64, A=200 => BGRA = [64, 128, 255, 200]
  // Pixel 1: R=10, G=20, B=30, A=255 => BGRA = [30, 20, 10, 255]
  const bgraPixels = new Uint8Array([64, 128, 255, 200, 30, 20, 10, 255]);
  producer.emitUpdateTexture(1, 0, 8, 2, 1, bgraPixels);

  // 3. Upload 1 DXT1 4x4 block (8 bytes): c0 = 0xF800 (pure Red), c1 = 0x001F (pure Blue), all indices = 0 (c0)
  const dxt1Block = new Uint8Array([0x00, 0xf8, 0x1f, 0x00, 0x00, 0x00, 0x00, 0x00]);
  producer.emitUpdateTexture(2, 0, 8, 4, 4, dxt1Block);

  // 4. Configure sampler 0 and bind texture 1 to stage 0
  producer.emitSetSamplerState(0, D3DSAMP_ADDRESSU, D3DTADDRESS_CLAMP);
  producer.emitSetSamplerState(0, D3DSAMP_ADDRESSV, D3DTADDRESS_MIRROR);
  producer.emitSetSamplerState(0, D3DSAMP_MAGFILTER, D3DTEXF_LINEAR);
  producer.emitSetSamplerState(0, D3DSAMP_MINFILTER, D3DTEXF_LINEAR);
  producer.emitSetSamplerState(0, D3DSAMP_MIPFILTER, D3DTEXF_POINT);
  producer.emitSetTexture(0, 1);

  consumer.processCommands();

  const tex1 = consumer.getTexture(1)!;
  assert.deepEqual(
    Array.from(tex1.levelData.get(0)!),
    [255, 128, 64, 200, 10, 20, 30, 255]
  );

  const tex2 = consumer.getTexture(2)!;
  const dxtRgba = tex2.levelData.get(0)!;
  assert.equal(dxtRgba.byteLength, 4 * 4 * 4);
  assert.deepEqual(Array.from(dxtRgba.slice(0, 4)), [255, 0, 0, 255]);

  const samp0 = consumer.getSamplerState(0);
  assert.equal(samp0.glWrapS, GL_CLAMP_TO_EDGE);
  assert.equal(samp0.glWrapT, GL_MIRRORED_REPEAT);
  assert.equal(samp0.glMagFilter, GL_LINEAR);
  assert.equal(samp0.glMinFilter, GL_LINEAR_MIPMAP_NEAREST);
  assert.equal(consumer.textureStages.get(0), 1);

  // Destroy texture 1 -> automatically unbinds stage 0
  producer.emitDestroyResource(3, 1);
  consumer.processCommands();
  assert.equal(consumer.textureStages.get(0), 0);
  assert.equal(consumer.getTexture(1), undefined);
});

test('D3D9 consumer executes DRAW_PRIMITIVE and DRAW_INDEXED_PRIMITIVE and enforces draw constraints', () => {
  const cap = 4096;
  const buf = new ArrayBuffer(D3D9_RING_HEADER_SIZE + cap);
  const producer = D3D9CommandProducer.initRing(buf, 0, cap);
  const consumer = new D3D9CommandConsumer(buf, 0);

  // Setup VB (4 vertices * 12 bytes = 48 bytes), IB (6 uint16 = 12 bytes), and VertexDecl
  producer.emitCreateVertexDeclaration(1, [
    { stream: 0, offset: 0, type: D3DDECLTYPE_FLOAT3, method: 0, usage: D3DDECLUSAGE_POSITION, usageIndex: 0 },
  ]);
  producer.emitSetVertexDeclaration(1);
  producer.emitCreateVertexBuffer(1, 48, D3DUSAGE_WRITEONLY);
  producer.emitSetStreamSource(0, 1, 0, 12);
  producer.emitCreateIndexBuffer(1, 12, D3DUSAGE_WRITEONLY, D3DFMT_INDEX16);
  producer.emitSetIndices(1);

  producer.emitBeginScene();
  producer.emitDrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2); // 2 tris = 4 verts
  producer.emitDrawIndexedPrimitive(D3DPT_TRIANGLELIST, 0, 0, 4, 0, 2); // 2 tris = 6 indices
  producer.emitEndScene();

  const cmds = consumer.processCommands();
  assert.equal(consumer.drawCallsExecuted, 2);

  const dpCmd = cmds[7];
  assert.equal(dpCmd.type, D3D9CmdType.DRAW_PRIMITIVE);
  if (dpCmd.type === D3D9CmdType.DRAW_PRIMITIVE) {
    assert.equal(dpCmd.glMode, GL_TRIANGLE_STRIP);
    assert.equal(dpCmd.vertexCount, 4);
  }

  const dipCmd = cmds[8];
  assert.equal(dipCmd.type, D3D9CmdType.DRAW_INDEXED_PRIMITIVE);
  if (dipCmd.type === D3D9CmdType.DRAW_INDEXED_PRIMITIVE) {
    assert.equal(dipCmd.glMode, GL_TRIANGLES);
    assert.equal(dipCmd.vertexCount, 6);
    assert.equal(dipCmd.glIndexType, GL_UNSIGNED_SHORT);
  }

  // Draw outside BEGIN_SCENE..END_SCENE must throw
  producer.emitDrawPrimitive(D3DPT_TRIANGLELIST, 0, 1);
  assert.throws(
    () => consumer.processCommands(),
    /DRAW_PRIMITIVE called outside BEGIN_SCENE/
  );
});
