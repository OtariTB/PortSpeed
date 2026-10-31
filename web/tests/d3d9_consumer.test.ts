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
