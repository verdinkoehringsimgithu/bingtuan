import os
import csv
from collections import defaultdict

data_dir = 'd:/123/unpacked/res/data'

def load_csv(name):
    path = os.path.join(data_dir, name)
    rows = []
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('gbk', errors='ignore')
    reader = csv.reader(text.splitlines())
    header_cn = next(reader, None)
    header_types = next(reader, None)
    header_en = next(reader, None)
    for r in reader:
        if r and len(r) > 0 and r[0].strip():
            row_dict = {}
            for i, col in enumerate(r):
                if i < len(header_en):
                    row_dict[header_en[i]] = col.strip()
            rows.append(row_dict)
    return header_en, header_cn, rows

_, _, mazes = load_csv('adventure_maze.csv')
_, _, monsters = load_csv('monster.csv')
_, _, income = load_csv('adventure_income.csv')

# Build monster map
monster_dict = {m['ID']: m for m in monsters}

# Group mazes by area_id
areas = defaultdict(list)
for m in mazes:
    aid = m.get('area_id', '')
    if aid:
        areas[int(aid)].append(m)

print(f"Total Areas: {len(areas)}")
print(f"{'Area':5} | {'Stages':6} | {'Min Req BP':12} | {'Max Req BP':12} | {'Monster BP':12} | {'Exp/Hour':10} | {'Gold/Hour':10}")
print("-" * 80)

for aid in sorted(areas.keys()):
    stage_list = areas[aid]
    req_bps = [int(s['battle_point']) for s in stage_list if s.get('battle_point', '').isdigit()]
    min_bp = min(req_bps) if req_bps else 0
    max_bp = max(req_bps) if req_bps else 0
    
    # get boss monster bp
    boss_stage = stage_list[-1]
    mon_id = boss_stage.get('monster_id', '')
    mon = monster_dict.get(mon_id, {})
    mon_bp = mon.get('battle_point', 'N/A')
    
    # drop speeds (in seconds per drop or per minute/hour)
    exp_spd = boss_stage.get('drop_exp_speed', '0')
    gold_spd = boss_stage.get('drop_gold_speed', '0')
    
    # Sample every 2-3 areas to keep output concise
    if aid <= 10 or aid % 5 == 0 or aid == len(areas):
        print(f"{aid:5} | {len(stage_list):6} | {min_bp:12,d} | {max_bp:12,d} | {int(mon_bp) if str(mon_bp).isdigit() else 0:12,d} | {int(exp_spd) if str(exp_spd).isdigit() else 0:10,d} | {int(gold_spd) if str(gold_spd).isdigit() else 0:10,d}")
