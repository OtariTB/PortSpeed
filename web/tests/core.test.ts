import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {parseTpk,jdlzDecompress} from '../src/tpk.ts';
import {decodeBc1,decodeBc2,decodeBc3,decodeDxt,type DecoderExports} from '../src/decoder.ts';

const fixture=Buffer.from(JSON.parse(execFileSync('python', ['../tests/fixture_tpk.py'], {encoding:'utf8'})).base64,'base64');
const wasm=await WebAssembly.instantiate(readFileSync('public/bc3.wasm'),{env:{abort:()=>{throw Error('abort');}}});
const decoder=wasm.instance.exports as DecoderExports;

test('synthetic container to WASM RGBA',()=>{
  const [t]=parseTpk(fixture);
  assert.equal(t.name,'RED');
  const rgba=decodeBc3(decoder,fixture.subarray(t.dataOffset,t.dataOffset+t.baseSize),4,4);
  assert.deepEqual([...rgba],Array.from({length:16},()=>[255,0,0,255]).flat());
});
test('reject every truncated container',()=>{
  for(let i=0;i<fixture.length;i++) assert.throws(()=>parseTpk(fixture.subarray(0,i)));
});
test('reject corrupt record and bounds',()=>{
  const [t]=parseTpk(fixture);
  for(const [offset,size,value] of [[12,4,7],[20,4,0xffffffff],[28,4,17],[36,4,8],[40,2,0],[42,2,5000],[46,1,0],[50,1,0],[88,1,255]]) {
    const b=Buffer.from(fixture);
    b.writeUIntLE(value,t.recordOffset+offset,size);
    assert.throws(()=>parseTpk(b));
  }
});
test('WASM rejects bad sizes and dimensions before memory writes',()=>{
  assert.equal(decoder.prepare(-1,4,16),0);
  assert.equal(decoder.prepare(4097,4,16),0);
  assert.equal(decoder.prepare(4,4,15),0);
  assert.equal(decoder.decode(4,4,17),0);
  assert.equal(decoder.decodeBc1(4,4,7),0);
  assert.equal(decoder.decodeBc2(4,4,15),0);
  assert.throws(()=>decodeBc3(decoder,new Uint8Array(15),4,4));
  assert.throws(()=>decodeBc3(decoder,new Uint8Array(16),4.1,4));
  assert.throws(()=>decodeBc1(decoder,new Uint8Array(7),4,4));
  assert.throws(()=>decodeBc2(decoder,new Uint8Array(15),4,4));
});
test('both BC3 alpha modes, interpolation and partial block cropping',()=>{
  for(const [a0,a1,expected] of [[255,0,[255,0,218,182,145,109,72,36]],[0,255,[0,255,51,102,153,204,0,255]]] as const) {
    const block=Buffer.alloc(16);block[0]=a0;block[1]=a1;
    let bits=0n;for(let j=0;j<16;j++)bits|=BigInt(j%8)<<BigInt(3*j);
    for(let j=0;j<6;j++)block[2+j]=Number((bits>>BigInt(8*j))&255n);
    block.writeUInt16LE(0xf800,8);block.writeUInt16LE(0x07e0,10);block.writeUInt32LE(0xaaaaaaaa,12);
    const rgba=decodeBc3(decoder,block,4,4);
    assert.deepEqual([...rgba.filter((_,i)=>i%4===3)],[...expected,...expected]);
    assert.deepEqual([...rgba.subarray(0,3)],[170,85,0]);
    assert.deepEqual([...decodeBc3(decoder,block,1,1)],[170,85,0,a0]);
  }
});
test('WASM BC1 (DXT1) 4-color and 3-color+transparent modes',()=>{
  const block4=Buffer.alloc(8);
  block4.writeUInt16LE(0xf800,0);
  block4.writeUInt16LE(0x07e0,2);
  block4.writeUInt32LE(0x00000000,4);
  const rgba4=decodeBc1(decoder,block4,4,4);
  assert.deepEqual([...rgba4.subarray(0,4)],[255,0,0,255]);

  const block3=Buffer.alloc(8);
  block3.writeUInt16LE(0x07e0,0);
  block3.writeUInt16LE(0xf800,2);
  block3.writeUInt32LE(0xffffffff,4);
  const rgba3=decodeDxt(decoder,'DXT1',block3,4,4);
  assert.deepEqual([...rgba3.subarray(0,4)],[0,0,0,0]);
});
test('WASM BC2 (DXT3) explicit 4-bit alpha expansion',()=>{
  const block=Buffer.alloc(16);
  block.writeBigUInt64LE(0xfedcba9876543210n,0);
  block.writeUInt16LE(0xf800,8);
  block.writeUInt16LE(0x0000,10);
  block.writeUInt32LE(0x00000000,12);
  const rgba=decodeBc2(decoder,block,4,4);
  const alphas=[...rgba.filter((_,i)=>i%4===3)];
  assert.deepEqual(alphas,Array.from({length:16},(_,i)=>i*17));
});
test('JDLZ decompressor decodes literal stream',()=>{
  const payload=Buffer.from('240SX_A\0','ascii');
  const hdr=Buffer.alloc(16);
  hdr.write('JDLZ',0,'ascii');
  hdr[4]=0x02;hdr[5]=0x10;hdr[6]=0x00;hdr[7]=0x00;
  hdr.writeUInt32LE(payload.length,8);
  hdr.writeUInt32LE(16+2+payload.length,12);
  const stream=Buffer.concat([hdr,Buffer.from([0x00,0x00]),payload]);
  const out=jdlzDecompress(stream);
  assert.deepEqual(Buffer.from(out),payload);
});
