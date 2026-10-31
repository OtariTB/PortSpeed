// Integration test against user-local files. Never copies them into the web root.
import {chromium} from 'playwright';
import {createServer} from 'vite';
import {readFile,writeFile,mkdir,realpath} from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const root=path.resolve('..');
const config=JSON.parse((await readFile(path.join(root,'config/local.json'),'utf8')).replace(/^\uFEFF/,''));
const evidence=JSON.parse(await readFile(path.join(root,'research/local/phase2/assets.json'),'utf8'));
const sourceRoot=await realpath(config.game_root);
const output=path.resolve(process.env.LOCALAPPDATA,'NFSProStreetResearch/phase2');
const outputPhase3=path.resolve(process.env.LOCALAPPDATA,'NFSProStreetResearch/phase3');
assert(!output.toLowerCase().startsWith(root.toLowerCase()+path.sep));
assert(!output.toLowerCase().startsWith(sourceRoot.toLowerCase()+path.sep));
assert(!outputPhase3.toLowerCase().startsWith(root.toLowerCase()+path.sep));
assert(!outputPhase3.toLowerCase().startsWith(sourceRoot.toLowerCase()+path.sep));
await mkdir(output,{recursive:true});
await mkdir(outputPhase3,{recursive:true});
assert.equal((await realpath(output)).toLowerCase(),output.toLowerCase());
const server=await createServer({server:{host:'127.0.0.1',port:5173,strictPort:false}});
let browser;
try {
  await server.listen();
  const baseUrl=server.resolvedUrls.local[0];
  browser=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1280,height:1100}});
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{
    const url=route.request().url();requests.push({url,method:route.request().method()});
    if(!url.startsWith(baseUrl)) return route.abort();
    return route.continue();
  });
  await page.goto(baseUrl);
  await page.waitForFunction(()=>!document.querySelector('#file').disabled);
  const checks=[];
  for(const entry of evidence.files.filter(f=>f.textures)) {
    const filename=await realpath(path.join(sourceRoot,'Need For Spped - Pro Street',entry.path));
    assert(filename.toLowerCase().startsWith(sourceRoot.toLowerCase()+path.sep));
    const bytes=await readFile(filename);
    assert.equal(createHash('sha256').update(bytes).digest('hex'),entry.sha256);
    await page.locator('#file').setInputFiles(filename);
    await page.waitForFunction(()=>!document.querySelector('#texture').disabled);
    const comparisons=entry.dxt_comparisons??entry.bc3_comparisons;
    for(const comparison of comparisons) {
      await page.locator('#texture').selectOption({label:comparison.name});
      await page.waitForFunction(expected=>document.querySelector('#canvas').dataset.rgbaSha256===expected,comparison.rgba_sha256);
      const framebuffer=await page.locator('#canvas').evaluate(canvas=>{
        const gl=canvas.getContext('webgl2'),w=canvas.width,h=canvas.height;
        const bytes=new Uint8Array(w*h*4);gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
        const rows=new Uint8Array(bytes.length);
        for(let y=0;y<h;y++)rows.set(bytes.subarray((h-1-y)*w*4,(h-y)*w*4),y*w*4);
        const ext=gl.getExtension('WEBGL_debug_renderer_info');
        return {pixels:Array.from(rows),width:w,height:h,renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),error:gl.getError()};
      });
      const hash=createHash('sha256').update(Buffer.from(framebuffer.pixels)).digest('hex');
      assert.equal(hash,comparison.rgba_sha256,`WebGL readback mismatch: ${comparison.name}`);
      assert.equal(framebuffer.error,0);
      checks.push({file:entry.path,name:comparison.name,fourcc:comparison.fourcc??'DXT5',compressed:Boolean(comparison.compressed),rgba_sha256:hash,renderer:framebuffer.renderer});
      if(comparison.name==='ICON_STAR')await page.screenshot({path:path.join(output,'browser-icon-star.png'),fullPage:true});
    }
  }
  const geomFilename=await realpath(path.join(sourceRoot,'Need For Spped - Pro Street','CARS/240SX/GEOMETRY.BIN'));
  assert(geomFilename.toLowerCase().startsWith(sourceRoot.toLowerCase()+path.sep));
  await page.locator('#geom-file').setInputFiles(geomFilename);
  await page.waitForFunction(()=>document.querySelector('#geom-canvas').dataset.renderedTris==='14612');
  const geomFramebuffer=await page.locator('#geom-canvas').evaluate(canvas=>{
    const gl=canvas.getContext('webgl2'),w=canvas.width,h=canvas.height;
    const bytes=new Uint8Array(w*h*4);gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
    const bgR=bytes[0],bgG=bytes[1],bgB=bytes[2];
    let nonBgPixels=0;
    for(let i=0;i<bytes.length;i+=4) {
      if(bytes[i]!==bgR||bytes[i+1]!==bgG||bytes[i+2]!==bgB) nonBgPixels++;
    }
    return {width:w,height:h,nonBgPixels,error:gl.getError(),tris:Number(canvas.dataset.renderedTris),verts:Number(canvas.dataset.renderedVerts),parts:Number(canvas.dataset.renderedParts)};
  });
  assert.equal(geomFramebuffer.error,0);
  assert.equal(geomFramebuffer.parts,27);
  assert.equal(geomFramebuffer.tris,14612);
  assert(geomFramebuffer.nonBgPixels>5000,'Expected 3D mesh pixels rendered on #geom-canvas');
  await page.screenshot({path:path.join(outputPhase3,'browser-240sx-geometry.png'),fullPage:true});

  await page.locator('#file').setInputFiles({name:'invalid.bun',mimeType:'application/octet-stream',buffer:Buffer.from('bad')});
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('File size outside'));
  assert.equal(await page.locator('#texture').isDisabled(),true);
  assert.equal(await page.locator('#canvas').getAttribute('data-rgba-sha256'),null);
  assert.deepEqual(errors,[]);
  assert(requests.every(r=>r.method==='GET'&&r.url.startsWith(baseUrl)));
  const report={browser:browser.version(),mode:'headless Chrome; forced SwiftShader software WebGL2',checks,geometry_check:geomFramebuffer,malformed_rejected:true,page_errors:errors,requests};
  await writeFile(path.join(root,'research/local/phase2/browser.json'),JSON.stringify(report,null,2));
  console.log(`${checks.length} original textures (including 11 compressed 240SX DXT1/DXT3/DXT5) + 240SX 3D geometry (${geomFramebuffer.parts} parts, ${geomFramebuffer.tris} triangles): Python/Pillow/WASM/WebGL readback hashes agree. Malformed input rejected. Browser ${report.browser}.`);
} finally {await browser?.close();await server.close();}
