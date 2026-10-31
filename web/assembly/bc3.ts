// Authored BC1/BC2/BC3 (DXT1/DXT3/DXT5) base-level decoder. No game code or WASI dependencies.
// ABI: prepare(w,h,n) -> input pointer; decode/decodeBc1/decodeBc2(w,h,n) -> RGBA pointer; 0 = invalid.
const INPUT: i32 = 65536;
function valid(w: i32, h: i32, n: i32): bool {
  return w > 0 && h > 0 && w <= 4096 && h <= 4096 && n == ((w+3)/4)*((h+3)/4)*16;
}
function validBc1(w: i32, h: i32, n: i32): bool {
  return w > 0 && h > 0 && w <= 4096 && h <= 4096 && n == ((w+3)/4)*((h+3)/4)*8;
}
export function prepare(w: i32, h: i32, n: i32): i32 {
  if (!valid(w,h,n) && !validBc1(w,h,n)) return 0;
  const pages = (INPUT+n+w*h*4+65535)/65536;
  if (pages > memory.size() && memory.grow(pages-memory.size()) == -1) return 0;
  return INPUT;
}
function channel(c: u32, k: i32): u32 {
  if (k == 0) { const v=(c>>11)&31; return (v<<3)|(v>>2); }
  if (k == 1) { const v=(c>>5)&63; return (v<<2)|(v>>4); }
  const v=c&31; return (v<<3)|(v>>2);
}
export function decodeBc1(w: i32, h: i32, n: i32): i32 {
  if (!validBc1(w,h,n) || INPUT+n+w*h*4 > memory.size()*65536) return 0;
  const output=INPUT+n;
  let p=INPUT;
  for (let y=0;y<h;y+=4) for (let x=0;x<w;x+=4) {
    const c0=<u32>load<u16>(p), c1=<u32>load<u16>(p+2), ci=load<u32>(p+4);
    for (let j=0;j<16;j++) {
      const px=x+j%4, py=y+j/4;
      if (px>=w || py>=h) continue;
      const q=output+(py*w+px)*4;
      const index=(ci>>(j*2))&3;
      if (c0<=c1 && index==3) {
        store<u32>(q,0);
        continue;
      }
      for (let k=0;k<3;k++) {
        const v0=channel(c0,k), v1=channel(c1,k);
        let v: u32;
        if (index==0) v=v0;
        else if (index==1) v=v1;
        else if (c0>c1) v=index==2 ? (2*v0+v1)/3 : (v0+2*v1)/3;
        else v=(v0+v1)/2;
        store<u8>(q+k,<u8>v);
      }
      store<u8>(q+3,255);
    }
    p+=8;
  }
  return output;
}
export function decodeBc2(w: i32, h: i32, n: i32): i32 {
  if (!valid(w,h,n) || INPUT+n+w*h*4 > memory.size()*65536) return 0;
  const output=INPUT+n;
  let p=INPUT;
  for (let y=0;y<h;y+=4) for (let x=0;x<w;x+=4) {
    const ai=load<u64>(p);
    const c0=<u32>load<u16>(p+8), c1=<u32>load<u16>(p+10), ci=load<u32>(p+12);
    for (let j=0;j<16;j++) {
      const px=x+j%4, py=y+j/4;
      if (px>=w || py>=h) continue;
      const q=output+(py*w+px)*4;
      const index=(ci>>(j*2))&3;
      for (let k=0;k<3;k++) {
        const v0=channel(c0,k), v1=channel(c1,k);
        let v: u32;
        if (index==0) v=v0;
        else if (index==1) v=v1;
        else if (index==2) v=(2*v0+v1)/3;
        else v=(v0+2*v1)/3;
        store<u8>(q+k,<u8>v);
      }
      const a4=<u32>((ai>>(j*4))&15);
      store<u8>(q+3,<u8>(a4*17));
    }
    p+=16;
  }
  return output;
}
export function decode(w: i32, h: i32, n: i32): i32 {
  if (!valid(w,h,n) || INPUT+n+w*h*4 > memory.size()*65536) return 0;
  const output=INPUT+n;
  let p=INPUT;
  for (let y=0;y<h;y+=4) for (let x=0;x<w;x+=4) {
    const a0=<u32>load<u8>(p), a1=<u32>load<u8>(p+1);
    const ai=load<u64>(p)>>16;
    const c0=<u32>load<u16>(p+8), c1=<u32>load<u16>(p+10), ci=load<u32>(p+12);
    for (let j=0;j<16;j++) {
      const px=x+j%4, py=y+j/4;
      if (px>=w || py>=h) continue;
      const q=output+(py*w+px)*4;
      const index=(ci>>(j*2))&3;
      for (let k=0;k<3;k++) {
        const v0=channel(c0,k), v1=channel(c1,k);
        let v: u32;
        if (index==0) v=v0;
        else if (index==1) v=v1;
        else if (index==2) v=(2*v0+v1)/3;
        else v=(v0+2*v1)/3;
        store<u8>(q+k,<u8>v);
      }
      const idx=<u32>((ai>>(j*3))&7);
      let a: u32;
      if (idx==0) a=a0;
      else if (idx==1) a=a1;
      else if (a0>a1) a=((8-idx)*a0+(idx-1)*a1)/7;
      else if (idx<6) a=((6-idx)*a0+(idx-1)*a1)/5;
      else a=idx==6 ? 0 : 255;
      store<u8>(q+3,<u8>a);
    }
    p+=16;
  }
  return output;
}
