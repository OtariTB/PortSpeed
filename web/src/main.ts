import './style.css';
import {parseTpk,extractTexturePayload,type Texture} from './tpk';
import {decodeDxt,type DecoderExports} from './decoder';
import {TextureRenderer} from './renderer';
import {parseGeometryDirectory,decompressAndParseSolid,getStockVehicleSpaceParts,type GeometryPartRecord,type SolidMesh} from './geometry';
import {MeshRenderer,type DecodedTextureRgba} from './mesh_renderer';

const file=document.querySelector<HTMLInputElement>('#file')!;
const select=document.querySelector<HTMLSelectElement>('#texture')!;
const status=document.querySelector<HTMLElement>('#status')!;
const metadata=document.querySelector<HTMLElement>('#metadata')!;
const canvas=document.querySelector<HTMLCanvasElement>('#canvas')!;

const geomFile=document.querySelector<HTMLInputElement>('#geom-file');
const geomPart=document.querySelector<HTMLSelectElement>('#geom-part');
const geomWireframe=document.querySelector<HTMLInputElement>('#geom-wireframe');
const geomReset=document.querySelector<HTMLButtonElement>('#geom-reset');
const geomStatus=document.querySelector<HTMLElement>('#geom-status');
const geomMetadata=document.querySelector<HTMLElement>('#geom-metadata');
const geomCanvas=document.querySelector<HTMLCanvasElement>('#geom-canvas');

let bytes=new Uint8Array(),textures: Texture[]=[],generation=0;
let geomBytes=new Uint8Array(),geomParts: GeometryPartRecord[]=[],geomGeneration=0;
const solidCache=new Map<number,SolidMesh>();
const loadedTextureMap=new Map<number,DecodedTextureRgba>();

const EXTERNAL_TEXTURE_NAMES: Record<number,string>={
  0x77a20245:'240SX_SKIN1 (external CARSKIN)',
  0x90e719eb:'DAMAGE_N (external GLOBALB.LZC)',
  0xe5f6a5ed:'CHASSIS (external GLOBALB.LZC)',
  0x027ff2dc:'BLACK (external GLOBALB.LZC)',
  0xe4cea024:'TIRE_STYLE01 (external GLOBALB.LZC)',
};

const sha=async (b: Uint8Array)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new Uint8Array(b)))).map(v=>v.toString(16).padStart(2,'0')).join('');
const hex32=(v: number)=>`0x${(v>>>0).toString(16).padStart(8,'0')}`;

async function start(): Promise<void> {
  const response=await fetch(`${import.meta.env.BASE_URL}bc3.wasm`);
  if(!response.ok) throw new Error('WASM module unavailable; run npm run wasm');
  const {instance}=await WebAssembly.instantiate(await response.arrayBuffer(),{env:{abort:()=>{throw new Error('WASM decoder trapped');}}});
  const decoder=instance.exports as DecoderExports;
  const renderer=new TextureRenderer(canvas);
  const meshRenderer=geomCanvas?new MeshRenderer(geomCanvas):null;
  let sourceHash='';
  let geomSourceHash='';

  async function show(): Promise<void> {
    const epoch=++generation;
    try {
      const t=textures[Number(select.value)];
      if(!t) throw new Error('No texture selected');
      const payload=extractTexturePayload(bytes,t);
      const pixels=decodeDxt(decoder,t.fourcc,payload,t.width,t.height);
      const pixelHash=await sha(pixels);
      if(epoch!==generation) return;
      renderer.draw(pixels,t.width,t.height);
      const isCompressed=Boolean(t.compressedSize&&t.compressedSize>0);
      const compInfo=isCompressed?`\nCompression: CIP+JDLZ/HUFF (${t.compressedSize} B -> ${t.size+148} B)`:'\nCompression: Uncompressed';
      metadata.textContent=`${t.name}\nHash: ${hex32(t.hash)}\n\n${t.width} × ${t.height} · ${t.fourcc}\nMip levels: ${t.mips}\nRecord: 0x${t.recordOffset.toString(16)}\nPixels: 0x${t.dataOffset.toString(16)}\nBase bytes: ${t.baseSize}${compInfo}\n\nRGBA SHA-256\n${pixelHash}\n\nSource SHA-256\n${sourceHash}`;
      canvas.dataset.rgbaSha256=pixelHash;
      status.textContent=`Decoded ${t.name} (${t.fourcc}${isCompressed?' + CIP':''}) in WebAssembly and rendered with WebGL2.`;
    } catch(error) {if(epoch===generation){renderer.clear();delete canvas.dataset.rgbaSha256;metadata.textContent='No texture displayed.';status.textContent=String(error);}}
  }

  function showGeometry(): void {
    if(!meshRenderer||!geomPart||!geomMetadata||!geomStatus||!geomCanvas) return;
    const epoch=++geomGeneration;
    try {
      const val=geomPart.value;
      if(!val) throw new Error('No part selected');
      let selectedEntries: GeometryPartRecord[]=[];
      let label='';
      if(val==='__STOCK_KIT00__') {
        selectedEntries=getStockVehicleSpaceParts(geomParts);
        label=`Composite Stock Vehicle (${selectedEntries.length} KIT00_*_A vehicle-space parts)`;
      } else {
        const idx=Number(val);
        const entry=geomParts[idx];
        if(!entry) throw new Error('Invalid part selection');
        selectedEntries=[entry];
        label=`${entry.name} (${hex32(entry.partHash)})`;
      }
      const solids: SolidMesh[]=selectedEntries.map(entry=>{
        let cached=solidCache.get(entry.partHash);
        if(!cached) {
          cached=decompressAndParseSolid(geomBytes,entry);
          solidCache.set(entry.partHash,cached);
        }
        return cached;
      });
      if(epoch!==geomGeneration) return;
      meshRenderer.loadSolids(solids);
      const totalSubmeshes=solids.reduce((acc,s)=>acc+s.submeshes.length,0);
      const totalVerts=solids.reduce((acc,s)=>acc+s.numVerts,0);
      const totalTris=solids.reduce((acc,s)=>acc+s.numTris,0);
      const allTexHashes=new Set<number>();
      for(const s of solids) for(const h of s.textureHashes) allTexHashes.add(h>>>0);
      const resolvedTex: string[]=[];
      const unresolvedTex: string[]=[];
      for(const h of allTexHashes) {
        const loaded=loadedTextureMap.get(h);
        if(loaded) resolvedTex.push(`${loaded.name} (${hex32(h)})`);
        else unresolvedTex.push(EXTERNAL_TEXTURE_NAMES[h]||hex32(h));
      }
      const first=solids[0];
      const bboxStr=solids.length===1
        ?`BBox min: [${first.bboxMin.map((v: number)=>v.toFixed(3)).join(', ')}]\nBBox max: [${first.bboxMax.map((v: number)=>v.toFixed(3)).join(', ')}]`
        :`Parts combined: ${solids.length} vehicle-space eSolid chunks`;
      const localOriginNote=(solids.length===1&&(/WHEEL|BRAKE_|SEAT/.test(first.name)))
        ?`\nNote: Local-origin part centered at [0, 0, 0]; vehicle wheel/seat world transforms reside in VLT/marker attributes.`
        :'';
      geomMetadata.textContent=`${label}\n\nSubmeshes: ${totalSubmeshes}\nVertices: ${totalVerts.toLocaleString()}\nTriangles: ${totalTris.toLocaleString()}\n${bboxStr}${localOriginNote}\n\nBound 240SX Textures (${resolvedTex.length}/${allTexHashes.size})\n${resolvedTex.length?resolvedTex.join('\n'):'None (load CARS/240SX/TEXTURES.BIN above to bind diffuse maps)'}\n\nUnresolved External Texture Hashes (${unresolvedTex.length})\n${unresolvedTex.length?unresolvedTex.join('\n'):'None'}\n\nSource SHA-256\n${geomSourceHash}`;
      geomCanvas.dataset.renderedTris=String(totalTris);
      geomCanvas.dataset.renderedVerts=String(totalVerts);
      geomCanvas.dataset.renderedParts=String(solids.length);
      geomStatus.textContent=`Decoded ${solids.length} eSolid part(s) (${totalTris.toLocaleString()} triangles, ${totalVerts.toLocaleString()} vertices) via CIP+JDLZ+HUFF and rendered in WebGL2.`;
    } catch(error) {
      if(epoch===geomGeneration) {
        meshRenderer.clear();
        delete geomCanvas.dataset.renderedTris;
        geomMetadata.textContent='No geometry displayed.';
        geomStatus.textContent=String(error);
      }
    }
  }

  file.addEventListener('change',async()=>{
    const epoch=++generation;
    renderer.clear();delete canvas.dataset.rgbaSha256;select.disabled=true;select.replaceChildren();textures=[];bytes=new Uint8Array();metadata.textContent='No asset loaded.';
    try {
      const chosen=file.files?.[0]; if(!chosen) return;
      if(chosen.size>64*1024*1024) throw new Error('File exceeds the 64 MiB research limit');
      status.textContent='Validating container…';
      const incoming=new Uint8Array(await chosen.arrayBuffer());
      const parsed=parseTpk(incoming), hash=await sha(incoming);
      if(epoch!==generation) return;
      bytes=incoming;textures=parsed;sourceHash=hash;
      loadedTextureMap.clear();
      for(const t of textures) {
        try {
          const payload=extractTexturePayload(bytes,t);
          const rgba=decodeDxt(decoder,t.fourcc,payload,t.width,t.height);
          loadedTextureMap.set(t.hash>>>0,{name:t.name,hash:t.hash>>>0,width:t.width,height:t.height,rgba});
        } catch {
          // Ignore individual background material decode failure
        }
      }
      if(meshRenderer) {
        meshRenderer.setTextures([...loadedTextureMap.values()]);
        if(geomParts.length>0) showGeometry();
      }
      textures.forEach((t,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=t.name;select.append(option);});
      const star=textures.findIndex(t=>t.name==='ICON_STAR');select.value=String(star>=0?star:0);select.disabled=false;
      await show();
    }catch(error){if(epoch===generation)status.textContent=String(error);}
  });

  select.addEventListener('change',()=>void show());
  file.disabled=false;

  if(geomFile&&geomPart&&geomWireframe&&geomReset&&geomStatus&&geomMetadata&&geomCanvas&&meshRenderer) {
    geomFile.addEventListener('change',async()=>{
      const epoch=++geomGeneration;
      meshRenderer.clear();delete geomCanvas.dataset.renderedTris;geomPart.disabled=true;geomPart.replaceChildren();geomParts=[];geomBytes=new Uint8Array();solidCache.clear();geomMetadata.textContent='No geometry loaded.';
      try {
        const chosen=geomFile.files?.[0]; if(!chosen) return;
        if(chosen.size>64*1024*1024) throw new Error('File exceeds the 64 MiB research limit');
        geomStatus.textContent='Validating geometry container…';
        const incoming=new Uint8Array(await chosen.arrayBuffer());
        const parsed=parseGeometryDirectory(incoming), hash=await sha(incoming);
        if(epoch!==geomGeneration) return;
        geomBytes=incoming;geomParts=parsed;geomSourceHash=hash;
        const stockKit00=getStockVehicleSpaceParts(geomParts);
        if(stockKit00.length>0) {
          const presetOpt=document.createElement('option');
          presetOpt.value='__STOCK_KIT00__';
          presetOpt.textContent=`[Composite] Stock 240SX KIT00 (${stockKit00.length} vehicle-space parts)`;
          geomPart.append(presetOpt);
        }
        geomParts.forEach((p,i)=>{
          const option=document.createElement('option');
          option.value=String(i);
          option.textContent=p.name?`${p.name} (${hex32(p.partHash)})`:hex32(p.partHash);
          geomPart.append(option);
        });
        geomPart.value=stockKit00.length>0?'__STOCK_KIT00__':'0';
        geomPart.disabled=false;
        geomWireframe.disabled=false;
        geomReset.disabled=false;
        showGeometry();
      } catch(error) {
        if(epoch===geomGeneration) geomStatus.textContent=String(error);
      }
    });
    geomPart.addEventListener('change',()=>showGeometry());
    geomWireframe.addEventListener('change',()=>meshRenderer.setWireframe(geomWireframe.checked));
    geomReset.addEventListener('click',()=>meshRenderer.resetCamera());
    geomFile.disabled=false;
    geomCanvas.addEventListener('webglcontextlost',event=>{event.preventDefault();geomStatus.textContent='WebGL2 context lost. Reload to continue.';});
    window.addEventListener('pagehide',()=>meshRenderer.dispose(),{once:true});
  }

  canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();status.textContent='WebGL2 context lost. Reload to continue.';});
  window.addEventListener('pagehide',()=>renderer.dispose(),{once:true});
}
start().catch(error=>{file.disabled=true;status.textContent=String(error);});
