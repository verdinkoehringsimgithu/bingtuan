import hashlib
import json
from pathlib import Path
import pandas as pd

here=Path(__file__).parent
new=json.loads((here/'integration_reproduction.json').read_text(encoding='utf-8'))
old=pd.read_csv(here/'results/recommended_confirmation.csv')
for result in new['results']:
    row=old[(old.stage==result['stage'])&(old.genre==result['genre'])&(old.difficulty=='hard')&(old.point=='center')&(old.preparation=='standard')].iloc[0]
    for field in ('wr','turns','censor'):
        if field in result and field in row:
            assert abs(result[field]-row[field])<1e-12,(result['genre'],field)
core=here.parents[1]/'test_30man_combat_simulator.py'
assert hashlib.sha256(core.read_bytes()).hexdigest()=='d82477b368cea5994053bcee99a618d560135e6a5195926afe26f78aa91ba75e'
print('Six flow results exactly reproduce the 768-battle confirmed reference; canonical physics hash preserved.')
