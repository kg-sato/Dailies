"""Explicit one-time profile upgrade; retains superseded assignment identities."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import core


def upgrade():
    core.initialize()
    backup=core.export_data()
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    with core.connect() as db:
        directory=Path(db.execute('PRAGMA database_list').fetchone()[2]).parent
    path=directory/f'before-euclid-{stamp}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(backup,indent=2),encoding='utf-8')
    with core.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        s=core.preferences(db);s['math_level']=4
        db.execute('UPDATE settings SET payload=? WHERE id=1',(json.dumps(s),))
        day=datetime.now(ZoneInfo(s['timezone'])).date().isoformat()
        old=db.execute("SELECT a.* FROM assignments a JOIN problems p ON p.id=a.problem_id WHERE a.date=? AND a.reason NOT LIKE 'Superseded:%' AND json_extract(p.payload,'$.source')='Dailies Originals' AND NOT EXISTS (SELECT 1 FROM attempts t WHERE t.problem_id=a.problem_id)",(day,)).fetchall()
        used={r[0] for r in db.execute('SELECT canonical_id FROM assignments')}
        used.update(r[0] for r in db.execute('SELECT p.canonical_id FROM attempts a JOIN problems p ON p.id=a.problem_id'))
        candidates=[p for p in core.catalog(db) if p['source']=='Dailies Euclid Originals' and p['canonical_id'] not in used]
        position=db.execute('SELECT COALESCE(MAX(position),-1)+1 FROM assignments WHERE date=?',(day,)).fetchone()[0]
        replaced=0
        for row in old:
            desired=4+(replaced%2)
            candidates.sort(key=lambda p:(abs(p['difficulty']-desired),p['id']))
            if not candidates:break
            p=candidates.pop(0)
            db.execute('UPDATE assignments SET reason=? WHERE date=? AND position=?',('Superseded: Euclid goal upgrade; original identity retained to prevent repeats.',day,row['position']))
            reason='Core problem solving' if p['difficulty']==4 else 'Stretch reasoning'
            db.execute('INSERT INTO assignments VALUES(?,?,?,?,?)',(day,position,p['id'],p['canonical_id'],f'{reason} for your Euclid 75/100 goal. Write a full solution before checking the answer. Difficulty is estimated.'))
            position+=1;replaced+=1
    return {'replaced':replaced,'backup':str(path)}


if __name__=='__main__':print(json.dumps(upgrade(),indent=2))
