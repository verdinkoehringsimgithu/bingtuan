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

_, _, mercenaries = load_csv('mercenary.csv')

genre_names = {
    '1': 'Critical / Burst (暴击流)',
    '2': 'Recovery / Defense (回复/防沉流)',
    '3': 'True Damage / Pure (纯粹流)',
    '4': 'Others / Special (其他/混合)'
}

quality_names = {
    '1': 'White',
    '2': 'Green',
    '3': 'Blue',
    '4': 'Purple',
    '5': 'Gold',
    '6': 'Flash Gold'
}

genre_stats = defaultdict(lambda: {'count': 0, 'by_quality': defaultdict(int), 'avg_bp_factor': [], 'avg_init_bp': []})

for m in mercenaries:
    g = m.get('genre', '4')
    q = m.get('quality', '1')
    st = genre_stats[g]
    st['count'] += 1
    st['by_quality'][q] += 1
    try:
        st['avg_bp_factor'].append(float(m.get('bp_factor', 0)))
        st['avg_init_bp'].append(float(m.get('init_bp', 0)))
    except:
        pass

print("=== MERCENARY GENRE DISTRIBUTION ===")
for g, st in sorted(genre_stats.items()):
    name = genre_names.get(g, f'Unknown ({g})')
    avg_bp = sum(st['avg_init_bp'])/len(st['avg_init_bp']) if st['avg_init_bp'] else 0
    avg_fac = sum(st['avg_bp_factor'])/len(st['avg_bp_factor']) if st['avg_bp_factor'] else 0
    qual_breakdown = ', '.join([f"{quality_names.get(k, k)}:{v}" for k, v in sorted(st['by_quality'].items())])
    print(f"Genre {g} - {name:32}: Total={st['count']:4}, AvgInitBP={avg_bp:6.1f}, AvgBPFactor={avg_fac:5.2f}")
    print(f"    Quality Breakdown: {qual_breakdown}")

print("\n=== MERCENARY QUALITY STATS ===")
qual_stats = defaultdict(lambda: {'count': 0, 'init_bp': [], 'bp_factor': [], 'max_wakeup': []})
for m in mercenaries:
    q = m.get('quality', '')
    if q in quality_names:
        st = qual_stats[q]
        st['count'] += 1
        try:
            st['init_bp'].append(float(m.get('init_bp', 0)))
            st['bp_factor'].append(float(m.get('bp_factor', 0)))
            st['max_wakeup'].append(float(m.get('max_wakeup', 0)))
        except:
            pass

for q in sorted(qual_stats.keys()):
    st = qual_stats[q]
    c = st['count']
    avg_bp = sum(st['init_bp'])/c
    avg_fac = sum(st['bp_factor'])/c
    avg_wkp = sum(st['max_wakeup'])/c
    print(f"Quality {q} - {quality_names[q]:12}: Count={c:4}, AvgInitBP={avg_bp:7.1f}, AvgBPFactor={avg_fac:6.2f}, AvgMaxWakeup={avg_wkp:4.1f}")
