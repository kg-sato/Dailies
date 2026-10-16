import json
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

import core


@asynccontextmanager
async def lifespan(app):
    core.initialize()
    yield


app=FastAPI(title='Dailies',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])


@app.middleware('http')
async def local_requests(request: Request, call_next):
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'Cross-origin writes are not allowed.'},403)
        if 'application/json' not in request.headers.get('content-type',''):
            return JSONResponse({'detail':'Use application/json.'},415)
    length=request.headers.get('content-length','0')
    if not length.isdigit() or int(length)>10_000_000:
        return JSONResponse({'detail':'Request exceeds the 10 MB limit.'},413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    response.headers['Cache-Control']='no-store'
    return response


@app.exception_handler(ValueError)
async def invalid(request,exc): return JSONResponse({'detail':str(exc)},400)


@app.exception_handler(sqlite3.IntegrityError)
async def integrity(request,exc): return JSONResponse({'detail':'Conflicting or invalid database references. No changes saved.'},400)


@app.get('/')
def index(): return FileResponse(core.ROOT/'static'/'index.html')


@app.get('/api/today')
def today(): return core.daily()


@app.get('/api/settings')
def settings():
    with core.connect() as db: return core.preferences(db)


@app.put('/api/settings')
def save_settings(data:dict):
    core.validate_settings(data)
    if data['csmc_year'] is not None:
        data['completed_contests']=[x for x in data['completed_contests'] if not x.startswith('CSMC')]+[f'CSMC {data["csmc_year"]}']
    with core.connect() as db: db.execute('UPDATE settings SET payload=? WHERE id=1',(json.dumps(data),))
    return data


@app.get('/api/problems')
def problems():
    with core.connect() as db:
        assigned={r[0] for r in db.execute('SELECT canonical_id FROM assignments')}
        review={r[0] for r in db.execute('SELECT problem_id FROM reviews')}
        s=core.preferences(db)
        return [{**core.public_problem(p),'latest_attempt':core.latest(db,p['id']),'assigned':p['canonical_id'] in assigned,'review':p['id'] in review,'excluded':core.blocked(p,s)} for p in core.catalog(db) if p['active']]


@app.get('/api/problems/{pid}')
def problem(pid:str):
    with core.connect() as db:
        p=core.get_problem(db,pid)
        draft=db.execute('SELECT code FROM drafts WHERE problem_id=?',(pid,)).fetchone()
        return {**core.public_problem(p),'latest_attempt':core.latest(db,pid),'draft':draft[0] if draft else '',
                'review':bool(db.execute('SELECT 1 FROM reviews WHERE problem_id=?',(pid,)).fetchone())}


@app.get('/api/problems/{pid}/solution')
def solution(pid:str):
    with core.connect() as db:
        p=core.get_problem(db,pid)
        return {'solution':p['solution'],'answer':p['answer']}


@app.post('/api/problems/{pid}/attempts')
def attempt(pid:str,data:dict): return core.submit(pid,data)


@app.put('/api/problems/{pid}/draft')
def draft(pid:str,data:dict):
    code=data.get('code')
    if not isinstance(code,str) or len(code)>200000: raise ValueError('Draft must be text under 200,000 characters.')
    with core.connect() as db:
        if core.get_problem(db,pid)['track']!='coding': raise ValueError('Only coding problems have drafts.')
        db.execute('INSERT INTO drafts VALUES(?,?) ON CONFLICT(problem_id) DO UPDATE SET code=excluded.code',(pid,code))
    return {'saved':True}


@app.put('/api/problems/{pid}/review')
def review(pid:str,data:dict):
    if type(data.get('enabled')) is not bool: raise ValueError('Specify enabled as a boolean.')
    with core.connect() as db:
        core.get_problem(db,pid)
        if data['enabled']: db.execute('INSERT OR IGNORE INTO reviews VALUES(?)',(pid,))
        else: db.execute('DELETE FROM reviews WHERE problem_id=?',(pid,))
    return {'enabled':data['enabled']}


@app.get('/api/progress')
def progress():
    with core.connect() as db:
        history=[dict(r) for r in db.execute('SELECT a.*,json_extract(p.payload,\'$.title\') AS title,json_extract(p.payload,\'$.track\') AS track,json_extract(p.payload,\'$.topic\') AS topic FROM attempts a JOIN problems p ON p.id=a.problem_id ORDER BY a.id DESC')]
        s=core.preferences(db)
        return dict(history=history,levels={t:core.target_level(db,t,s) for t in ('math','coding')},
            assigned=db.execute('SELECT COUNT(*) FROM assignments').fetchone()[0],
            practiced_days=db.execute('SELECT COUNT(DISTINCT substr(created_at,1,10)) FROM attempts').fetchone()[0])


@app.get('/api/export')
def export(): return JSONResponse(core.export_data(),headers={'Content-Disposition':'attachment; filename="dailies-backup.json"'})


@app.post('/api/import')
def restore(data:dict):
    try:
        core.restore(data)
    except (TypeError,KeyError,OverflowError) as exc:
        raise ValueError('Invalid backup field values.') from exc
    return {'restored':True}


app.mount('/static',StaticFiles(directory=core.ROOT/'static'),name='static')
