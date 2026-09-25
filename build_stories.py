#!/usr/bin/env python3
"""Merge stories/*.json, project each story onto the map, attach it to a block, and write stories.js."""
import json, math, glob, os, re

M = json.load(open('map.json'))
LON0, LAT0 = M['origin']
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
A = math.radians(-M['angle'])
OX, OY = M['offset']

def to_map(lon, lat):
    x, y = (lon - LON0) * KX, -(lat - LAT0) * KY
    xr, yr = x * math.cos(A) - y * math.sin(A), x * math.sin(A) + y * math.cos(A)
    return [round(xr - OX, 1), round(yr - OY, 1)]

def inside(pt, poly):
    c = False; j = len(poly) - 1
    for i in range(len(poly)):
        (xi, yi), (xj, yj) = poly[i], poly[j]
        if (yi > pt[1]) != (yj > pt[1]) and pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi: c = not c
        j = i
    return c

THEMES = {
    'origins': ('Before the grid', '#9b7b4f'), 'victorian': ('Victorian San Francisco', '#b4556b'), 'quake1906': ('1906 & rebuilding', '#c0602f'),
    'communities': ('Many communities', '#5f7f4f'), 'harlem': ('Harlem of the West', '#3f5f9c'), 'redevelopment': ('Redevelopment', '#6c6f76'),
    'institutions': ('Landmarks & institutions', '#8a6d3b'), 'modern': ('Counterculture to today', '#7a4f9c'),
}
# duplicates found across researchers: keep one telling of each story
DROP = {'communities-emanu-el-residence', 'modern-zen-center-page-street', 'victorian-mish-house', 'victorian-mcmorry-lagan',
        'modern-rainbow-house', 'victorian-full-house-postcard-row', 'harlem-sacred-heart-panthers', 'harlem-ame-zion', 'victorian-nightingale-house'}
stories, problems = [], []
for f in sorted(glob.glob('stories/*.json')):
    theme = os.path.basename(f)[:-5]
    try: items = json.load(open(f))
    except Exception as e: problems.append(f'{f}: {e}'); continue
    for s in items:
        if s.get('id') in DROP: continue
        pl = s.get('place', {})
        try: c = to_map(float(pl['lon']), float(pl['lat']))
        except Exception: problems.append(f"{s.get('id')}: bad coordinates"); continue
        if not (0 <= c[0] <= M['w'] and 0 <= c[1] <= M['h']): problems.append(f"{s.get('id')}: outside map ({pl.get('label')})"); continue
        block = next((b['id'] for b in M['blocks'] if b['inAoi'] and any(inside(c, p) for p in b['p'])), None)
        if block is None:  # street / intersection: snap to the nearest block centre
            b = min((b for b in M['blocks'] if b['inAoi']), key=lambda b: (b['c'][0] - c[0]) ** 2 + (b['c'][1] - c[1]) ** 2)
            block = b['id']
        stories.append(dict(id=s['id'], theme=theme, title=s['title'], year=int(s['year']), yearEnd=s.get('yearEnd'), place=pl.get('label', ''),
                            precision=pl.get('precision', 'block'), c=c, block=block, hook=s['hook'], story=s['story'],
                            people=s.get('people') or [], sources=s.get('sources') or [], photo=s.get('photo')))
stories.sort(key=lambda s: (s['year'], s['title']))
# fan out pins that share (almost) the same spot
groups = {}
for s in stories: groups.setdefault((round(s['c'][0] / 14), round(s['c'][1] / 14)), []).append(s)
for g in groups.values():
    if len(g) > 1:
        for k, s in enumerate(g):
            ang = -math.pi / 2 + (k - (len(g) - 1) / 2) * 0.9
            s['c'] = [round(s['c'][0] + math.cos(ang) * 16, 1), round(s['c'][1] + math.sin(ang) * 16 + 8, 1)]
seen = set(); uniq = []
for s in stories:
    key = re.sub(r'\W', '', s['title'].lower())
    if key in seen: problems.append(f"duplicate title: {s['title']}"); continue
    seen.add(key); uniq.append(s)
out = dict(themes={k: dict(label=v[0], color=v[1]) for k, v in THEMES.items()}, stories=uniq)
open('stories.js', 'w').write('window.STORIES = ' + json.dumps(out, ensure_ascii=False) + ';\n')
print(f"{len(uniq)} stories on {len({s['block'] for s in uniq})} blocks")
for k in THEMES: print(f"  {k:14} {sum(s['theme'] == k for s in uniq)}")
for p in problems: print('  !', p)
