"""Explicitly reviewed catalog imports; no remote content is activated automatically."""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen, Request

import core


def codeforces_records(data):
    if data.get('status')!='OK': raise ValueError('Codeforces returned an unsuccessful response.')
    records=[]
    for p in data['result']['problems']:
        if 'contestId' not in p: continue
        code=f'{p["contestId"]}-{p["index"]}'
        rating=p.get('rating')
        level=max(1,min(5,(rating-600)//400+1)) if rating else 2
        records.append(dict(id='cf-'+code,canonical_id='codeforces:'+code,title=p['name'],
            track='coding',source='Codeforces',source_id=code,
            source_url=f'https://codeforces.com/problemset/problem/{p["contestId"]}/{p["index"]}',
            contest=f'Codeforces {p["contestId"]}',topic=', '.join(p.get('tags',[])) or 'general',
            difficulty=level,native_rating=str(rating or 'unrated'),minutes=20,reuse_status='reference_only',
            attribution='Codeforces metadata API',statement='',answer_type='external',answer='',solution='',
            answer_verified=False,choices=[],active=False))
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    p=sub.add_parser('import-catalog');p.add_argument('file',type=Path);p.add_argument('--approve',action='store_true')
    p=sub.add_parser('fetch-codeforces');p.add_argument('output',type=Path)
    p=sub.add_parser('export');p.add_argument('output',type=Path)
    args=parser.parse_args();core.initialize()
    try:
        if args.command=='import-catalog':
            print(json.dumps(core.import_catalog(json.loads(args.file.read_text(encoding='utf-8')),args.approve),indent=2))
        elif args.command=='fetch-codeforces':
            req=Request('https://codeforces.com/api/problemset.problems',headers={'User-Agent':'Dailies personal practice pilot'})
            with urlopen(req,timeout=45) as r: rows=codeforces_records(json.load(r))
            args.output.write_text(json.dumps(rows,indent=2),encoding='utf-8')
            print(f'Saved {len(rows)} inactive records for review. Set active=true only after reviewing metadata and difficulty, then validate and approve the import.')
        elif args.command=='export': args.output.write_text(json.dumps(core.export_data(),indent=2),encoding='utf-8')
        else: print('Database initialized.')
    except (ValueError,OSError,KeyError) as e: parser.exit(1,f'Error: {e}\n')


if __name__=='__main__': main()
