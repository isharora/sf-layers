#!/usr/bin/env python3
"""Collect verified 'on this day' dates (dates_src/*.out.json) into city/days.js."""
import json, glob
ids = {s['id'] for s in json.load(open('city/stories_all.json'))}
rows, seen = [], set()
for f in sorted(glob.glob('dates_src/*.out.json')):
    for r in json.load(open(f)):
        y, m, d = map(int, r['date'].split('-'))
        k = (r['id'], r['date'])
        if r['id'] not in ids or k in seen or not (1 <= m <= 12 and 1 <= d <= 31): continue
        seen.add(k); rows.append([m * 100 + d, y, r['id'], r['what'].strip()])
rows.sort()
open('city/days.js', 'w').write('window.DAYS = ' + json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(len(rows), 'dated events ·', len({r[0] for r in rows}), 'distinct days')
