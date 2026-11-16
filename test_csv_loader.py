import os
import csv
import glob

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

print("Testing CSV Loader...")
en, cn, rows = load_csv('mercenary.csv')
print(f'mercenary.csv: {len(rows)} mercenaries loaded.')
print('First mercenary:', rows[0]['ID'], rows[0].get('name'), rows[0].get('quality'))

en, cn, rows = load_csv('active_skill.csv')
print(f'active_skill.csv: {len(rows)} active skills loaded.')

en, cn, rows = load_csv('adventure_maze.csv')
print(f'adventure_maze.csv: {len(rows)} adventure mazes loaded.')

en, cn, rows = load_csv('monster.csv')
print(f'monster.csv: {len(rows)} monsters loaded.')

en, cn, rows = load_csv('mercenary_exp.csv')
print(f'mercenary_exp.csv: {len(rows)} exp rows loaded.')

en, cn, rows = load_csv('mining_dig_info.csv')
print(f'mining_dig_info.csv: {len(rows)} mining rows loaded.')
