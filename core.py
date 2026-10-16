import json
import os
import re
import sqlite3
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from catalog import seed_catalog

ROOT = Path(__file__).parent
DEFAULTS = dict(math_count=2, coding_count=1, timezone='America/Toronto',
    math_level=4, coding_level=2, csmc_year=None,
    completed_contests=['CSMC *', 'Cayley 2025', 'CIMC 2024', 'CCC Junior 2025'])


class Database(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect():
    path = Path(os.environ.get('DAILIES_DB', str(ROOT/'data'/'dailies.sqlite3')))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20, factory=Database)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS problems(id TEXT PRIMARY KEY, canonical_id TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS days(date TEXT PRIMARY KEY, timezone TEXT NOT NULL, shortage TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments(date TEXT REFERENCES days(date), position INTEGER, problem_id TEXT REFERENCES problems(id), canonical_id TEXT UNIQUE, reason TEXT, PRIMARY KEY(date,position));
        CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, problem_id TEXT REFERENCES problems(id), outcome TEXT NOT NULL, answer TEXT, assistance INTEGER, difficulty TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS drafts(problem_id TEXT PRIMARY KEY REFERENCES problems(id), code TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(problem_id TEXT PRIMARY KEY REFERENCES problems(id));
        ''')
        db.execute('INSERT OR IGNORE INTO settings VALUES(1,?)', (json.dumps(DEFAULTS),))
        for p in seed_catalog():
            validate_problem(p)
            db.execute('INSERT OR IGNORE INTO problems VALUES(?,?,?)', (p['id'],p['canonical_id'],json.dumps(p)))


def preferences(db):
    return json.loads(db.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0])


def validate_settings(s):
    if set(s) != set(DEFAULTS):
        raise ValueError('Settings fields do not match this version.')
    for k in ('math_count','coding_count'):
        if type(s[k]) is not int or not 0 <= s[k] <= 10:
            raise ValueError('Problem counts must be whole numbers from 0 to 10.')
    if s['math_count']+s['coding_count'] == 0:
        raise ValueError('Choose at least one daily problem.')
    for k in ('math_level','coding_level'):
        if type(s[k]) is not int or not 1 <= s[k] <= 5:
            raise ValueError('Levels must be from 1 to 5.')
    try:
        ZoneInfo(s['timezone'])
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise ValueError('Use a valid IANA timezone, such as America/Toronto.')
    if not isinstance(s['completed_contests'],list) or len(s['completed_contests'])>200 or any(not isinstance(x,str) or len(x)>100 for x in s['completed_contests']):
        raise ValueError('Completed contests must be a list of names.')
    y=s['csmc_year']
    if y is not None and (type(y) is not int or not 1960 <= y <= 2100):
        raise ValueError('Enter a valid CSMC year or leave it blank.')
    return s


def number(value):
    value=str(value).strip()
    if len(value)>100 or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:\s*/\s*[+-]?\d+)?',value):
        raise ValueError('Enter a number, decimal, or fraction such as 3/8.')
    try:
        if '/' in value:
            a,b=value.split('/')
            return Fraction(a.strip())/Fraction(b.strip())
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        raise ValueError('Enter a valid number with a nonzero denominator.')


def validate_problem(p):
    required={'id','canonical_id','title','track','source','source_id','source_url','contest','topic','difficulty','native_rating','minutes','reuse_status','attribution','statement','answer_type','answer','solution','answer_verified','choices','active'}
    if not isinstance(p,dict) or set(p)!=required:
        raise ValueError('Problem fields do not match the catalog format.')
    for k in required-{'difficulty','minutes','answer_verified','choices','active'}:
        if not isinstance(p[k],str) or len(p[k])>30000:
            raise ValueError(f'Invalid text field: {k}')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',p['id']) or not p['canonical_id'] or not p['title']:
        raise ValueError('A stable ID, canonical ID and title are required.')
    if p['track'] not in ('math','coding') or type(p['difficulty']) is not int or not 1<=p['difficulty']<=5:
        raise ValueError('Invalid track or difficulty.')
    if type(p['minutes']) is not int or not 1<=p['minutes']<=180:
        raise ValueError('Invalid time estimate.')
    if type(p['active']) is not bool or type(p['answer_verified']) is not bool:
        raise ValueError('Active and answer_verified must be boolean.')
    if not isinstance(p['choices'],list) or any(not isinstance(x,str) for x in p['choices']):
        raise ValueError('Choices must be text.')
    if p['reuse_status'] not in ('original','licensed','permission_granted','reference_only') or not p['attribution']:
        raise ValueError('Content provenance is required.')
    if p['source_url'] and (urlparse(p['source_url']).scheme!='https' or not urlparse(p['source_url']).netloc):
        raise ValueError('Source links must use HTTPS.')
    if p['reuse_status']=='reference_only' and (p['statement'] or p['solution'] or p['answer']):
        raise ValueError('Reference-only records cannot contain copied content or answer keys.')
    if p['answer_type'] not in ('numeric','choice','self_review','external'):
        raise ValueError('Invalid answer type.')
    if p['track']=='coding' and (p['answer_type']!='external' or not p['source_url']):
        raise ValueError('Coding problems require an external judge link.')
    if p['active'] and p['track']=='math':
        if not p['statement'] or not p['solution'] or not p['answer_verified'] or p['answer_type']=='external':
            raise ValueError('Active math requires approved content and a verified solution.')
    if p['answer_type']=='numeric':
        number(p['answer'])
    if p['answer_type']=='choice' and (not p['choices'] or p['answer'] not in [x.split(':')[0] for x in p['choices']]):
        raise ValueError('Choice answer must match a choice label.')
    return p


def catalog(db):
    return [json.loads(r[0]) for r in db.execute('SELECT payload FROM problems ORDER BY id')]


def public_problem(p):
    return {k:v for k,v in p.items() if k not in ('answer','solution','answer_verified')}


def blocked(p,s):
    for c in s['completed_contests']:
        if c.endswith('*') and p['contest'].startswith(c[:-1].strip()): return True
        if p['contest'] and p['contest']==c: return True
    if s['csmc_year'] is None and p['contest'].startswith('CSMC'): return True
    return False


def target_level(db,track,s):
    rows=db.execute('SELECT outcome,assistance,difficulty FROM attempts a JOIN problems p ON p.id=a.problem_id WHERE json_extract(p.payload,\'$.track\')=? ORDER BY a.id DESC LIMIT 8',(track,)).fetchall()
    base=s[track+'_level']
    if len(rows)<5: return base
    success=sum(r['outcome']=='solved' and not r['assistance'] and r['difficulty']!='hard' for r in rows)/len(rows)
    return max(1,min(5,base+(1 if success>=.75 else -1 if success<=.25 else 0)))


def daily(now=None):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        s=preferences(db)
        day=(now or datetime.now(ZoneInfo(s['timezone']))).astimezone(ZoneInfo(s['timezone'])).date().isoformat()
        existing=db.execute('SELECT * FROM days WHERE date=?',(day,)).fetchone()
        if not existing:
            used={r[0] for r in db.execute('SELECT canonical_id FROM assignments')}
            used.update(r[0] for r in db.execute('SELECT p.canonical_id FROM attempts a JOIN problems p ON a.problem_id=p.id'))
            selected=[]; shortages=[]
            topics={}
            for r in db.execute('SELECT json_extract(p.payload,\'$.topic\') AS topic,COUNT(*) AS n FROM attempts a JOIN problems p ON p.id=a.problem_id GROUP BY topic'):
                topics[r['topic']]=r['n']
            for track in ('math','coding'):
                level=target_level(db,track,s)
                floor=max(1,level-1) if track=='math' else 1
                candidates=[p for p in catalog(db) if p['active'] and p['track']==track and p['canonical_id'] not in used and not blocked(p,s) and floor<=p['difficulty']<=level+1 and not (track=='math' and level>=3 and p['source']=='Dailies Originals')]
                candidates.sort(key=lambda p:(abs(p['difficulty']-level),topics.get(p['topic'],0),p['id']))
                count=s[track+'_count']; chosen=[]
                while candidates and len(chosen)<count:
                    desired=min(5,level+(len(chosen)%2)) if track=='math' else level
                    candidates.sort(key=lambda x:(abs(x['difficulty']-desired),x['topic'] in [v['topic'] for v in chosen],topics.get(x['topic'],0),x['id']))
                    p=candidates.pop(0)
                    if p['canonical_id'] in used: continue
                    used.add(p['canonical_id']); chosen.append(p)
                    candidates.sort(key=lambda x:(x['topic'] in [v['topic'] for v in chosen],abs(x['difficulty']-level),topics.get(x['topic'],0),x['id']))
                for p in chosen:
                    reason=f'{p["topic"].capitalize()} practice at level {p["difficulty"]}; your current {track} target is {level}.'
                    if track=='math' and level>=4:
                        role='Stretch reasoning' if p['difficulty']>level else 'Core problem solving'
                        reason=f'{role} for your Euclid 75/100 goal. Write a full solution before checking the final answer. Difficulty is estimated.'
                    selected.append((p,reason))
                if len(chosen)<count: shortages.append(f'{track.capitalize()}: only {len(chosen)} of {count} suitable unseen problems available. Import reviewed problems to expand your catalog.')
            db.execute('INSERT INTO days VALUES(?,?,?)',(day,s['timezone'],json.dumps(shortages)))
            for pos,(p,reason) in enumerate(selected):
                db.execute('INSERT INTO assignments VALUES(?,?,?,?,?)',(day,pos,p['id'],p['canonical_id'],reason))
        stored=db.execute('SELECT * FROM days WHERE date=?',(day,)).fetchone()
        items=[]
        for r in db.execute("SELECT a.reason,p.payload FROM assignments a JOIN problems p ON p.id=a.problem_id WHERE a.date=? AND a.reason NOT LIKE 'Superseded:%' ORDER BY json_extract(p.payload,'$.track') DESC,a.position",(day,)):
            p=public_problem(json.loads(r['payload'])); p['reason']=r['reason']; p['latest_attempt']=latest(db,p['id']); items.append(p)
        return dict(date=day,timezone=stored['timezone'],problems=items,shortages=json.loads(stored['shortage']),minutes=sum(p['minutes'] for p in items))


def latest(db,pid):
    r=db.execute('SELECT * FROM attempts WHERE problem_id=? ORDER BY id DESC LIMIT 1',(pid,)).fetchone()
    return dict(r) if r else None


def get_problem(db,pid):
    r=db.execute('SELECT payload FROM problems WHERE id=?',(pid,)).fetchone()
    if not r: raise ValueError('Problem not found.')
    return json.loads(r[0])


def submit(pid,data):
    with connect() as db:
        p=get_problem(db,pid)
        if not p['active']: raise ValueError('This problem is not active.')
        assistance=data.get('assistance',False); difficulty=data.get('difficulty','okay')
        if type(assistance) is not bool or difficulty not in ('easy','okay','hard'): raise ValueError('Invalid attempt feedback.')
        answer=str(data.get('answer','')).strip()
        if len(answer)>10000: raise ValueError('Answer is too long.')
        kind=p['answer_type']
        if kind=='numeric': outcome='solved' if number(answer)==number(p['answer']) else 'incorrect'
        elif kind=='choice':
            if answer.upper() not in [x.split(':')[0].upper() for x in p['choices']]: raise ValueError('Choose one of the listed options.')
            outcome='solved' if answer.upper()==p['answer'].upper() else 'incorrect'
        else:
            outcome=data.get('outcome')
            if outcome not in ('solved','with_help','attempted'): raise ValueError('Select a result.')
        if assistance and outcome=='solved': outcome='with_help'
        db.execute('INSERT INTO attempts(problem_id,outcome,answer,assistance,difficulty,created_at) VALUES(?,?,?,?,?,?)',
                   (pid,outcome,answer,int(assistance),difficulty,datetime.now().astimezone().isoformat()))
        return dict(outcome=outcome,latest_attempt=latest(db,pid))


def export_data():
    with connect() as db:
        return dict(version=1,settings=preferences(db),problems=catalog(db),
                    **{t:[dict(r) for r in db.execute(f'SELECT * FROM {t}')] for t in ('days','assignments','attempts','drafts','reviews')})


def restore(data):
    if not isinstance(data,dict) or set(data)!={'version','settings','problems','days','assignments','attempts','drafts','reviews'} or data['version']!=1:
        raise ValueError('Unsupported backup format.')
    validate_settings(data['settings'])
    if not isinstance(data['problems'],list) or len(data['problems'])>10000:
        raise ValueError('Invalid backup catalog.')
    for p in data['problems']: validate_problem(p)
    # Validate all rows in an isolated database before touching the live database.
    tables={'days':('date','timezone','shortage'),'assignments':('date','position','problem_id','canonical_id','reason'),
            'attempts':('id','problem_id','outcome','answer','assistance','difficulty','created_at'),
            'drafts':('problem_id','code'),'reviews':('problem_id',)}
    for t,keys in tables.items():
        if not isinstance(data[t],list): raise ValueError(f'Invalid {t}.')
        for row in data[t]:
            if not isinstance(row,dict) or set(row)!=set(keys): raise ValueError(f'Invalid {t} row.')
    pmap={p['id']:p for p in data['problems']}
    if len(pmap)!=len(data['problems']): raise ValueError('Duplicate problem IDs.')
    for r in data['days']:
        datetime.strptime(r['date'],'%Y-%m-%d')
        try: ZoneInfo(r['timezone'])
        except (ZoneInfoNotFoundError,TypeError,ValueError): raise ValueError('Invalid backup timezone.')
        if not isinstance(json.loads(r['shortage']),list): raise ValueError('Invalid shortage list.')
    for r in data['assignments']:
        if r['problem_id'] not in pmap or r['canonical_id']!=pmap[r['problem_id']]['canonical_id'] or type(r['position']) is not int or r['position']<0:
            raise ValueError('Assignment identity mismatch.')
    for r in data['attempts']:
        if r['outcome'] not in ('solved','with_help','attempted','incorrect') or r['assistance'] not in (0,1) or r['difficulty'] not in ('easy','okay','hard'):
            raise ValueError('Invalid attempt.')
        datetime.fromisoformat(r['created_at'])
    for r in data['drafts']:
        if not isinstance(r['code'],str) or len(r['code'])>200000: raise ValueError('Invalid draft.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for t in ('reviews','drafts','attempts','assignments','days','problems'): db.execute(f'DELETE FROM {t}')
        for p in data['problems']: db.execute('INSERT INTO problems VALUES(?,?,?)',(p['id'],p['canonical_id'],json.dumps(p)))
        db.execute('UPDATE settings SET payload=? WHERE id=1',(json.dumps(data['settings']),))
        for t,keys in tables.items():
            for r in data[t]: db.execute(f'INSERT INTO {t} ({",".join(keys)}) VALUES({",".join("?" for _ in keys)})',tuple(r[k] for k in keys))


def import_catalog(rows,approve=False):
    if not isinstance(rows,list) or not 1<=len(rows)<=10000: raise ValueError('Provide an array of 1–10000 problems.')
    seen=set()
    for p in rows:
        validate_problem(p)
        if p['id'] in seen: raise ValueError('Duplicate ID in import.')
        seen.add(p['id'])
    with connect() as db:
        for p in rows:
            old=db.execute('SELECT canonical_id FROM problems WHERE id=?',(p['id'],)).fetchone()
            if old: raise ValueError(f'ID already exists: {p["id"]}. Imports only add new records.')
        if approve:
            for p in rows: db.execute('INSERT INTO problems VALUES(?,?,?)',(p['id'],p['canonical_id'],json.dumps(p)))
    return dict(validated=len(rows),committed=approve,problems=[dict(id=p['id'],title=p['title'],reuse_status=p['reuse_status'],active=p['active']) for p in rows])
