import json
import mmap
from recon import WORKSPACE
from paths import safe_path
from archive_headers import big4_index,jdlz_header


def main():
    config=json.loads((WORKSPACE/'config/local.json').read_text(encoding='utf-8-sig'))
    root=safe_path(config['game_root'])
    inventory=json.loads((WORKSPACE/'research/local/inventory/inventory.json').read_text())
    results=[]
    for row in inventory['files']:
        if row['extension'] not in ('.big','.lzc'):continue
        source=safe_path(root/row['path'])
        if not source.is_relative_to(root):raise ValueError('source escaped root')
        item={'path':row['path']}
        try:
            with source.open('rb') as f:
                if row['extension']=='.big':
                    with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:item.update(big4_index(data))
                else:item.update(jdlz_header(f.read(16),source.stat().st_size))
        except ValueError as exc:item['validation_error']=str(exc)
        results.append(item)
    target=safe_path(WORKSPACE/'research/local/phase2/archives.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k!='entries'} for r in results],indent=2))


if __name__=='__main__':main()
