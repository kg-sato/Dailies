import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path

from fastapi.testclient import TestClient
import core
from app import app
from manage import codeforces_records


class DailiesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();os.environ['DAILIES_DB']=str(Path(self.temp.name)/'test.db')
        self.client_context=TestClient(app);self.client=self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None,None,None);self.temp.cleanup();os.environ.pop('DAILIES_DB',None)

    def test_concurrent_stable_sets_and_restart(self):
        now=datetime(2026,10,16,17,tzinfo=timezone.utc)
        with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(lambda _:core.daily(now),range(12)))
        self.assertTrue(all(x==results[0] for x in results));self.assertEqual(len(results[0]['problems']),3)
        core.initialize();self.assertEqual(core.daily(now),results[0])

    def test_two_weeks_no_repeats_and_shortage(self):
        seen=set();now=datetime(2026,10,16,17,tzinfo=timezone.utc)
        for i in range(14):
            d=core.daily(now+timedelta(days=i));self.assertEqual(len(d['problems']),3)
            for p in d['problems']:self.assertNotIn(p['canonical_id'],seen);seen.add(p['canonical_id'])
        d=core.daily(now+timedelta(days=30));self.assertEqual(len(d['problems']),1)
        d=core.daily(now+timedelta(days=31));self.assertTrue(d['shortages'])

    def test_exact_numeric_checks_and_invalid_input(self):
        p=core.seed_catalog()[8];answer=p['answer']
        equivalent=str(float(core.number(answer))) if core.number(answer).denominator in (2,4,5,8,10) else str(core.number(answer)*2/2)
        self.assertEqual(core.submit(p['id'],{'answer':answer})['outcome'],'solved')
        self.assertEqual(core.number('0.375'),core.number('3/8'));self.assertEqual(core.number('-2/-4'),core.number('0.5'))
        self.assertEqual(core.submit(p['id'],{'answer':'0'})['outcome'],'incorrect')
        for bad in ['1/0','__import__("os")','2**8','nan','1e999999','9'*101]:
            with self.assertRaises(ValueError):core.submit(p['id'],{'answer':bad})
        self.assertEqual(core.submit('math-29',{'answer':'b'})['outcome'],'solved')

    def test_drafts_review_and_backup_roundtrip(self):
        self.client.get('/api/today')
        self.assertEqual(self.client.put('/api/problems/ccc24j2/draft',json={'code':'print("hi")'}).status_code,200)
        self.client.put('/api/problems/math-01/review',json={'enabled':True})
        core.submit('math-01',{'answer':'7'})
        backup=self.client.get('/api/export').json()
        self.client.put('/api/problems/ccc24j2/draft',json={'code':'changed'})
        self.assertEqual(self.client.post('/api/import',json=backup).status_code,200)
        self.assertEqual(self.client.get('/api/export').json(),backup)
        self.assertEqual(self.client.get('/api/problems/ccc24j2').json()['draft'],'print("hi")')
        broken=copy.deepcopy(backup);broken['assignments'][0]['canonical_id']='wrong'
        self.assertEqual(self.client.post('/api/import',json=broken).status_code,400)
        self.assertEqual(self.client.get('/api/export').json(),backup)
        broken=copy.deepcopy(backup);broken['reviews'].append({'problem_id':'missing'})
        self.assertEqual(self.client.post('/api/import',json=broken).status_code,400)
        self.assertEqual(self.client.get('/api/export').json(),backup)

    def test_exclusions_mirrors_attempted_and_timezone(self):
        with core.connect() as db:
            s=core.preferences(db);s['completed_contests'].append('CCC Junior 2024');s['timezone']='Asia/Tokyo'
            db.execute('UPDATE settings SET payload=?',(json.dumps(s),))
            p=copy.deepcopy(core.seed_catalog()[0]);p['id']='mirror';p['contest']='CSMC 2020'
            db.execute('INSERT INTO problems VALUES(?,?,?)',(p['id'],p['canonical_id'],json.dumps(p)))
        core.submit('math-01',{'answer':'7'})
        d=core.daily(datetime(2026,10,16,18,tzinfo=timezone.utc));self.assertEqual(d['date'],'2026-10-17')
        self.assertTrue(all(p['contest']!='CCC Junior 2024' and p['canonical_id']!='dailies:math:1' for p in d['problems']))
        with core.connect() as db:self.assertTrue(core.blocked(p,s))

    def test_review_does_not_assign_and_solution_is_hidden(self):
        self.client.put('/api/problems/math-30/review',json={'enabled':True})
        self.client.get('/api/problems/math-30')
        with core.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM assignments').fetchone()[0],0)
        p=self.client.get('/api/problems/math-29').json();self.assertNotIn('answer',p);self.assertNotIn('solution',p)
        self.assertEqual(self.client.get('/api/problems/math-29/solution').json()['answer'],'B')

    def test_import_validation_and_approval(self):
        p=copy.deepcopy(core.seed_catalog()[0]);p['id']='new-problem';p['canonical_id']='new'
        core.import_catalog([p]);self.assertEqual(len(core.export_data()['problems']),len(core.seed_catalog()))
        bad=copy.deepcopy(p);bad['answer_verified']=False
        with self.assertRaises(ValueError):core.import_catalog([bad],True)
        bad=copy.deepcopy(p);bad['reuse_status']='reference_only'
        with self.assertRaises(ValueError):core.import_catalog([bad],True)
        core.import_catalog([p],True);self.assertEqual(len(core.export_data()['problems']),len(core.seed_catalog())+1)
        with self.assertRaises(ValueError):core.import_catalog([p],True)

    def test_settings_adaptation_and_api_guards(self):
        s=self.client.get('/api/settings').json();s['timezone']='Not/AZone'
        self.assertEqual(self.client.put('/api/settings',json=s).status_code,400)
        self.assertEqual(self.client.put('/api/settings',json={},headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/problems/math-01/attempts',json={'answer':'7','difficulty':'invalid'}).status_code,400)
        for _ in range(5):core.submit('math-01',{'answer':'7','difficulty':'easy'})
        with core.connect() as db:self.assertEqual(core.target_level(db,'math',core.preferences(db)),5)
        self.assertEqual(self.client.get('/').status_code,200)
        s=self.client.get('/api/settings').json();s['csmc_year']=2024
        out=self.client.put('/api/settings',json=s).json();self.assertIn('CSMC 2024',out['completed_contests']);self.assertNotIn('CSMC *',out['completed_contests'])

    def test_codeforces_staging(self):
        rows=codeforces_records({'status':'OK','result':{'problems':[{'contestId':1,'index':'A','name':'Example','rating':800,'tags':['math']}]}})
        self.assertFalse(rows[0]['active']);core.validate_problem(rows[0])


if __name__=='__main__':unittest.main()
