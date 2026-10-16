import itertools
import math
import unittest
from datetime import datetime,timedelta,timezone

import core
from euclid_catalog import euclid_catalog
import test_dailies as fixtures


class EuclidSelectionTests(unittest.TestCase):
    setUp=fixtures.DailiesTests.setUp
    tearDown=fixtures.DailiesTests.tearDown
    def test_euclid_daily_mix(self):
        now=datetime(2026,10,16,17,tzinfo=timezone.utc)
        for i in range(14):
            d=core.daily(now+timedelta(days=i))
            math_problems=[p for p in d['problems'] if p['track']=='math']
            self.assertEqual([p['difficulty'] for p in math_problems],[4,5])
            self.assertTrue(all(p['source']=='Dailies Euclid Originals' for p in math_problems))
            self.assertTrue(all('Euclid' in p['reason'] for p in math_problems))
        d=core.daily(now+timedelta(days=14))
        self.assertFalse(any(p['track']=='math' for p in d['problems']))
        self.assertTrue(d['shortages'])

    def test_upgrade_retains_history_and_coding(self):
        import upgrade_euclid
        self.client.get('/api/today')
        with core.connect() as db:
            rows=list(db.execute('SELECT * FROM assignments'))
            for row,pid in zip([r for r in rows if r['problem_id'].startswith('euclid-')],['math-05','math-13']):
                p=core.get_problem(db,pid)
                db.execute('UPDATE assignments SET problem_id=?,canonical_id=? WHERE date=? AND position=?',(pid,p['canonical_id'],row['date'],row['position']))
            coding=[dict(r) for r in db.execute("SELECT * FROM assignments WHERE problem_id LIKE 'ccc%'")]
        self.assertEqual(upgrade_euclid.upgrade()['replaced'],2)
        self.assertEqual(upgrade_euclid.upgrade()['replaced'],0)
        self.assertEqual(len(self.client.get('/api/today').json()['problems']),3)
        with core.connect() as db:
            self.assertEqual([dict(r) for r in db.execute("SELECT * FROM assignments WHERE problem_id LIKE 'ccc%'")],coding)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM assignments WHERE reason LIKE 'Superseded:%'").fetchone()[0],2)
        before=core.export_data();core.restore(before);self.assertEqual(core.export_data(),before)

    def test_no_basic_drills_after_downgrade(self):
        for _ in range(5):core.submit('euclid-01',{'answer':'0','difficulty':'hard'})
        d=core.daily(datetime(2026,10,16,17,tzinfo=timezone.utc))
        self.assertTrue(all(p['difficulty']>=4 for p in d['problems'] if p['track']=='math'))


class EuclidAnswerTests(unittest.TestCase):
    def test_independent_enumerations(self):
        answers={p['id']:core.number(p['answer']) for p in euclid_catalog()}
        checks={
            5:sum(1 for a in range(1,100) for b in range(a,100) if a*b==6*(a+b)),
            6:sum(1 for ups in itertools.combinations(range(9),4) if self.avoids(ups)),
            10:sum(len(set(str(n)))==2 for n in range(100,1000)),
            12:pow(3,100,13),
            17:sum(1 for x in range(1,20) for y in range(x+1,20) if y<20-x-y),
            19:sum(3*k//7 for k in range(1,101)),
            20:sum(max(b-a,c-b,12+a-c)<6 for a,b,c in itertools.combinations(range(12),3)),
            21:sum(x*x-y*y==2025 for x in range(1,1014) for y in range(1,x)),
            24:sum(n for n in range(1,1000) if any(a*(n-a)==n+15 for a in range(-20, n//2+1))),
            25:sum(self.below(ups) for ups in itertools.combinations(range(12),6)),
            26:sum(k*(k-1)*math.comb(10,k) for k in range(11)),
            28:next(n for n in range(2,1000) if (n*(n-1)//2)%100==0),
        }
        for i,value in checks.items():self.assertEqual(answers[f'euclid-{i:02}'],value,f'Exercise {i}')

    @staticmethod
    def avoids(ups):
        x=y=0
        for step in range(9):
            if step in ups:y+=1
            else:x+=1
            if (x,y)==(2,2):return False
        return True

    @staticmethod
    def below(ups):
        x=y=0
        for step in range(12):
            if step in ups:y+=1
            else:x+=1
            if y>x:return False
        return True


if __name__=='__main__':unittest.main()
