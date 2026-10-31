export interface DecoderExports extends WebAssembly.Exports {
  memory: WebAssembly.Memory;
  prepare(w: number,h: number,n: number): number;
  decode(w: number,h: number,n: number): number;
  decodeBc1(w: number,h: number,n: number): number;
  decodeBc2(w: number,h: number,n: number): number;
}
function checkDims(width: number,height: number): void {
  if(!Number.isInteger(width)||!Number.isInteger(height)||width<1||height<1||width>4096||height>4096) throw new Error('Invalid dimensions');
}
export function decodeBc1(module: DecoderExports, payload: Uint8Array, width: number,height: number): Uint8Array {
  checkDims(width,height);
  if(payload.length!==Math.ceil(width/4)*Math.ceil(height/4)*8) throw new Error('Invalid BC1 payload size');
  const input=module.prepare(width,height,payload.length);
  if(!input) throw new Error('Decoder allocation failed');
  new Uint8Array(module.memory.buffer,input,payload.length).set(payload);
  const output=module.decodeBc1(width,height,payload.length);
  if(!output) throw new Error('Decoder rejected input');
  return new Uint8Array(module.memory.buffer,output,width*height*4).slice();
}
export function decodeBc2(module: DecoderExports, payload: Uint8Array, width: number,height: number): Uint8Array {
  checkDims(width,height);
  if(payload.length!==Math.ceil(width/4)*Math.ceil(height/4)*16) throw new Error('Invalid BC2 payload size');
  const input=module.prepare(width,height,payload.length);
  if(!input) throw new Error('Decoder allocation failed');
  new Uint8Array(module.memory.buffer,input,payload.length).set(payload);
  const output=module.decodeBc2(width,height,payload.length);
  if(!output) throw new Error('Decoder rejected input');
  return new Uint8Array(module.memory.buffer,output,width*height*4).slice();
}
export function decodeBc3(module: DecoderExports, payload: Uint8Array, width: number,height: number): Uint8Array {
  checkDims(width,height);
  if(payload.length!==Math.ceil(width/4)*Math.ceil(height/4)*16) throw new Error('Invalid BC3 payload size');
  const input=module.prepare(width,height,payload.length);
  if(!input) throw new Error('Decoder allocation failed');
  new Uint8Array(module.memory.buffer,input,payload.length).set(payload);
  const output=module.decode(width,height,payload.length);
  if(!output) throw new Error('Decoder rejected input');
  return new Uint8Array(module.memory.buffer,output,width*height*4).slice();
}
export function decodeDxt(module: DecoderExports, fourcc: string, payload: Uint8Array, width: number, height: number): Uint8Array {
  if(fourcc==='DXT1') return decodeBc1(module,payload,width,height);
  if(fourcc==='DXT3') return decodeBc2(module,payload,width,height);
  if(fourcc==='DXT5') return decodeBc3(module,payload,width,height);
  throw new Error(`Unsupported DXT format: ${fourcc}`);
}
