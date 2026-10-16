"""Original, independently checkable exercises plus source-only contest references."""
from fractions import Fraction
from euclid_catalog import euclid_catalog


def original(n, title, topic, statement, answer, solution, difficulty=2, kind='numeric', choices=None):
    return dict(id=f'math-{n:02}', canonical_id=f'dailies:math:{n}', title=title,
                track='math', source='Dailies Originals', source_id=f'math-{n:02}',
                source_url='', contest='', topic=topic, difficulty=difficulty,
                native_rating='Cayley preparation' if difficulty < 4 else 'CSMC preparation',
                minutes=7, reuse_status='original', attribution='Dailies original exercise',
                statement=statement, answer_type=kind, answer=str(answer), solution=solution,
                answer_verified=True, choices=choices or [], active=True)


def seed_catalog():
    rows = []
    # Each parameter choice creates a different exercise; solutions supply reproducible checks.
    for i, (a, b, c) in enumerate([(3, 5, 26), (4, 7, 39), (5, 9, 54), (6, 11, 71)], 1):
        x = (c-b)//a
        rows.append(original(i, f'The hidden number {i}', 'algebra',
            f'A number x satisfies {a}x + {b} = {c}. What is x?', x,
            f'Subtract {b} from both sides, then divide by {a}: x = ({c} − {b})/{a} = {x}.', 1))
    for i, (w, h) in enumerate([(8, 6), (12, 5), (9, 12), (15, 8)], 5):
        diagonal = int((w*w+h*h)**0.5)
        rows.append(original(i, f'Across the rectangle {i-4}', 'geometry',
            f'A rectangle has side lengths {w} and {h}. What is its diagonal length?', diagonal,
            f'By Pythagoras, d² = {w*w} + {h*h} = {diagonal**2}, so d = {diagonal}.', 2))
    for i, (r, b) in enumerate([(3, 5), (4, 7), (5, 8), (6, 9)], 9):
        ans=Fraction(r*(r-1), (r+b)*(r+b-1))
        rows.append(original(i, f'Two red tokens {i-8}', 'probability',
            f'A bag contains {r} red tokens and {b} blue tokens. Two tokens are drawn without replacement. What is the probability both are red? Give an exact fraction.', ans,
            f'Multiply the successive probabilities: {r}/{r+b} × {r-1}/{r+b-1} = {ans}.', 3))
    for i, (n, modulus) in enumerate([(23, 7), (31, 9), (43, 11), (51, 13)], 13):
        ans=(n*n)%modulus
        rows.append(original(i, f'Square remainder {i-12}', 'number theory',
            f'What is the remainder when {n}² is divided by {modulus}?', ans,
            f'{n}² = {n*n} = {modulus} × {(n*n)//modulus} + {ans}.', 2))
    for i, (n, k) in enumerate([(8, 3), (9, 4), (10, 3), (11, 4)], 17):
        import math
        ans=math.comb(n,k)
        rows.append(original(i, f'Choose a team {i-16}', 'counting',
            f'A club has {n} members. How many different teams of {k} members can it form? Order does not matter.', ans,
            f'Choose {k} of {n}: C({n},{k}) = {n}! / ({k}! × {n-k}!) = {ans}.', 3))
    for i, (a, d, count) in enumerate([(4, 3, 12), (7, 4, 10), (5, 6, 11), (9, 5, 14)], 21):
        end=a+d*(count-1); ans=count*(a+end)//2
        rows.append(original(i, f'Arithmetic trail {i-20}', 'sequences',
            f'An arithmetic sequence starts at {a} and increases by {d} each step. What is the sum of its first {count} terms?', ans,
            f'The last term is {a} + {count-1} × {d} = {end}. The sum is {count}({a}+{end})/2 = {ans}.', 2))
    for i, (s, p) in enumerate([(11, 24), (13, 35), (14, 40), (17, 60)], 25):
        ans=s*s-2*p
        rows.append(original(i, f'Squares without solving {i-24}', 'algebra',
            f'Two real numbers x and y satisfy x + y = {s} and xy = {p}. Find x² + y².', ans,
            f'x² + y² = (x+y)² − 2xy = {s*s} − {2*p} = {ans}.', 3))
    rows.append(original(29, 'Last digit cycle', 'number theory',
        'What is the last digit of 7²⁰²⁶?', 'B',
        'Powers of 7 end in 7, 9, 3, 1. Since 2026 has remainder 2 on division by 4, the last digit is 9.',
        3, 'choice', ['A: 7', 'B: 9', 'C: 3', 'D: 1']))
    rows.append(original(30, 'An even product', 'proof',
        'Prove that n(n+1) is even for every integer n.', '',
        'Consecutive integers have opposite parity, so one of n and n+1 is even. Their product is therefore divisible by 2.',
        3, 'self_review'))
    coding=[('24j2','Dusa And The Yobis','simulation',1),('24j3','Bronze Count','sorting',2),
            ('23j2','Chili Peppers','simulation',1),('23j3','Special Event','counting',2),
            ('22j2','Fergusonball Ratings','simulation',1),('22j3','Harp Tuning','strings',2),
            ('21j2','Silent Auction','simulation',1),('21j3','Secret Instructions','strings',2),
            ('20j2','Epidemiology','simulation',1),('20j3','Art','geometry',2),
            ('19j2','Time to Decompress','strings',1),('19j3','Cold Compress','strings',2),
            ('18j2','Occupy parking','strings',1),('18j3','Are we there yet?','sequences',2),
            ('24j4','Troublesome Keys','strings',3),('23j4','Wooden Fence','geometry',3),
            ('22j4','Good Groups','sets',3),('21j4','Arranging Books','counting',3)]
    for code,title,topic,level in coding:
        year=2000+int(code[:2]); slot=code[2:].upper()
        rows.append(dict(id=f'ccc{code}',canonical_id=f'waterloo:ccc:{year}:{slot}',title=title,
            track='coding',source='Waterloo CCC',source_id=f'ccc{code}',
            source_url=f'https://dmoj.ca/problem/ccc{code}',contest=f'CCC Junior {year}',
            topic=topic,difficulty=level,native_rating=slot,minutes=16,
            reuse_status='reference_only',attribution='University of Waterloo CEMC; judge: DMOJ',
            statement='',answer_type='external',answer='',solution='',answer_verified=False,
            choices=[],active=True))
    return rows + euclid_catalog()
