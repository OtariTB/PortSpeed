"""Print validated metadata for a source-relative standalone TPK; no extraction."""
import argparse
from dataclasses import asdict
import hashlib
import json
from recon import WORKSPACE
from paths import safe_path
from tpk import parse_tpk,LIMIT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_relative_path')
    args=parser.parse_args()
    config=json.loads((WORKSPACE/'config/local.json').read_text(encoding='utf-8-sig'))
    root=safe_path(config['game_root'])
    source=safe_path(root/args.source_relative_path)
    if not source.is_relative_to(root):raise ValueError('path outside source root')
    if source.stat().st_size>LIMIT:raise ValueError('file exceeds 64 MiB limit')
    data=source.read_bytes()
    print(json.dumps({'source':source.relative_to(root).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),
                      'textures':[asdict(t) for t in parse_tpk(data)]},indent=2))


if __name__=='__main__':main()
