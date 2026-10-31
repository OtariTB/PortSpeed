"""Local-only format validation and one BC3 texture extraction.

Run with the optional Pillow validation environment; no source writes.
"""
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
from PIL import Image, __version__ as pillow_version
from recon import WORKSPACE
from paths import safe_path
from tpk import parse_tpk, texture_payload, decode_dxt, dds, png, FormatError


def main():
    config=json.loads((WORKSPACE/'config/local.json').read_text(encoding='utf-8-sig'))
    root=safe_path(config['game_root'])
    out=safe_path(Path(os.environ['LOCALAPPDATA'])/'NFSProStreetResearch/phase2')
    if out.is_relative_to(root) or root.is_relative_to(out) or out.is_relative_to(WORKSPACE):
        raise ValueError('unsafe extraction directory')
    out.mkdir(parents=True,exist_ok=True)
    paths=['GLOBAL/LOADINGTEXTURES.BUN','GLOBAL/UniqueBootTextures.bin','GLOBAL/NISOverlayTextures.bin',
           'FRONTEND/FRONTDLC.BUN','GLOBAL/GLOBALA.BUN','CARS/240SX/TEXTURES.BIN']
    report={'pillow_version':pillow_version,'files':[],'output_directory':str(out)}
    for rel in paths:
        source=safe_path(root/'Need For Spped - Pro Street'/rel)
        if not source.is_relative_to(root): raise ValueError('source escapes root')
        data=source.read_bytes()
        row={'path':rel,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}
        try:
            textures=parse_tpk(data)
            row['textures']=[asdict(t) for t in textures]
            comparisons=[]
            for t in textures:
                if t.fourcc not in ('DXT1','DXT3','DXT5'): continue
                payload=texture_payload(data,t)
                rgba=decode_dxt(t.fourcc,payload[:t.base_size],t.width,t.height)
                image=Image.open(io.BytesIO(dds(t,payload))).convert('RGBA')
                reference=image.tobytes()
                diffs=[abs(a-b) for a,b in zip(rgba,reference)]
                if len(rgba)!=len(reference) or max(diffs,default=0)!=0:
                    raise ValueError(f'independent DDS decoder mismatch: {t.name}, max={max(diffs)}')
                comparisons.append({'name':t.name,'fourcc':t.fourcc,'rgba_sha256':hashlib.sha256(rgba).hexdigest(),'pillow_equal':True})
                if rel==paths[0] and t.name=='ICON_STAR':
                    # Fixed output names; never use untrusted asset names as paths.
                    for name,content in [('icon-star.png',png(t.width,t.height,rgba)),('icon-star.dds',dds(t,payload))]:
                        target=safe_path(out/name)
                        if target.parent!=out: raise ValueError('unsafe output')
                        target.write_bytes(content)
                    reread=Image.open(out/'icon-star.png').convert('RGBA').tobytes()
                    if reread!=rgba: raise ValueError('PNG round trip mismatch')
                    report['selected']={**asdict(t),'source':rel,'source_sha256':row['sha256'],
                                        'rgba_sha256':hashlib.sha256(rgba).hexdigest(),'png_round_trip_equal':True}
            row['bc3_comparisons']=comparisons
        except FormatError as exc:
            row['unsupported']=str(exc)
        report['files'].append(row)
    report_path=safe_path(WORKSPACE/'research/local/phase2/assets.json')
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'selected':report.get('selected'),'files':[{k:v for k,v in r.items() if k not in ('textures','bc3_comparisons')} for r in report['files']]},indent=2))


if __name__=='__main__': main()
