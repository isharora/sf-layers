#!/usr/bin/env python3
"""Merge the Alamo Square stories and the city-wide stories into city/stories.js (north-up city coordinates)."""
import json, math, glob, os, re
from shapely.geometry import shape, Point, Polygon
from shapely.strtree import STRtree
LON0, LAT0 = -122.44, 37.76
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
xy = lambda lon, lat: (round((lon - LON0) * KX, 1), round(-(lat - LAT0) * KY, 1))
THEMES = {
 'indigenous-early': ('Yelamu to Mexican era', '#9b7b4f'), 'gold-rush-victorian': ('Gold Rush & Victorian city', '#b4556b'),
 'quake1906': ('1906 & rebuilding', '#c0602f'), 'communities': ('Communities', '#5f7f4f'), 'labor-industry': ('Work & industry', '#8a6d3b'),
 'war-military': ('War & the military', '#5d6b52'), 'civil-rights': ('Civil rights & displacement', '#6c6f76'),
 'arts-counterculture': ('Arts & counterculture', '#7a4f9c'), 'lgbtq': ('LGBTQ history', '#c2508a'),
 'architecture-landmarks': ('Architecture & landmarks', '#a0773f'), 'parks-nature': ('Parks & nature', '#4f8a5b'), 'modern-city': ('The modern city', '#3f5f9c'),
}
ALAMO = {'origins': 'gold-rush-victorian', 'victorian': 'gold-rush-victorian', 'quake1906': 'quake1906', 'communities': 'communities',
         'harlem': 'communities', 'redevelopment': 'civil-rights', 'institutions': 'architecture-landmarks', 'modern': 'modern-city'}
ALAMO_DROP = {'communities-emanu-el-residence', 'modern-zen-center-page-street', 'victorian-mish-house', 'victorian-mcmorry-lagan',
              'modern-rainbow-house', 'victorian-full-house-postcard-row', 'harlem-sacred-heart-panthers', 'harlem-ame-zion', 'victorian-nightingale-house'}
# cross-neighbourhood duplicates found after the city research run (same event told twice)
CITY_DROP = {'inner-richmond-anza-mountain-lake', 'oceanview-merced-ingleside-wolfes-hall', 'tenderloin-hammett-891-post', 'haight-ashbury-panhandle-freeway-revolt',
             'golden-gate-park-diggers-free-food', 'inner-richmond-mountain-lake-alligator', 'tenderloin-twitter-tax-break', 'nob-hill-betty-ann-ong-rec-center'}
regions = [json.load(open(f)) for f in glob.glob('regions/*.json')]
rgeoms = [shape(r['geometry']).buffer(0) for r in regions]
rtree = STRtree(rgeoms)
base = json.loads(open('city/base.js').read()[len('window.BASE = '):-2])
bpolys, bids = [], []
for b in base['blocks']:
    for r in b['p']:
        if len(r) >= 4: bpolys.append(Polygon(r)); bids.append(b['id'])
btree = STRtree(bpolys)
def hood_of(lon, lat):
    p = Point(lon, lat)
    for i in rtree.query(p):
        if rgeoms[i].contains(p): return regions[i]['name']
    i = rtree.nearest(p); return regions[i]['name']
def block_of(x, y):
    p = Point(x, y)
    for i in btree.query(p):
        if bpolys[i].contains(p): return bids[i]
    i = btree.nearest(p); return bids[i] if bpolys[i].distance(p) < 60 else None
stories, problems = [], []
def add(s, theme):
    pl = s.get('place', {})
    try: lon, lat = float(pl['lon']), float(pl['lat'])
    except Exception: problems.append(f"{s.get('id')}: bad coordinates"); return
    if not (-122.53 < lon < -122.35 and 37.70 < lat < 37.84): problems.append(f"{s.get('id')}: outside SF"); return
    if theme not in THEMES: theme = 'modern-city'
    x, y = xy(lon, lat)
    stories.append(dict(id=s['id'], theme=theme, title=s['title'], year=int(s['year']), yearEnd=s.get('yearEnd'), place=pl.get('label', ''), c=[x, y],
                        block=block_of(x, y), hood=hood_of(lon, lat), hook=s['hook'], story=s['story'], people=s.get('people') or [], sources=s.get('sources') or [], photo=s.get('photo')))
for f in sorted(glob.glob('stories/*.json')):
    t = os.path.basename(f)[:-5]
    for s in json.load(open(f)):
        if s['id'] in ALAMO_DROP: continue
        add(s, 'indigenous-early' if int(s['year']) < 1848 else ALAMO.get(t, 'modern-city'))
for f in sorted(glob.glob('stories_city/*.json')):
    try: items = json.load(open(f))
    except Exception as e: problems.append(f'{f}: {e}'); continue
    for s in items:
        if s.get('id') in CITY_DROP: continue
        if all(k in s for k in ('id', 'title', 'year', 'place', 'hook', 'story')): add(s, s.get('theme', 'modern-city'))
# de-duplicate: same normalised title, or same building with near-identical title
seen, out = {}, []
for s in sorted(stories, key=lambda s: (s['year'], s['title'])):
    key = re.sub(r'[^a-z0-9]', '', s['title'].lower())
    if key in seen: problems.append(f"duplicate: {s['title']}"); continue
    seen[key] = 1; out.append(s)
# fan out pins sharing a spot (~12 m)
groups = {}
for s in out: groups.setdefault((round(s['c'][0] / 12), round(s['c'][1] / 12)), []).append(s)
for g in groups.values():
    if len(g) > 1:
        for k, s in enumerate(g):
            a = -math.pi / 2 + (k - (len(g) - 1) / 2) * .8
            s['c'] = [round(s['c'][0] + math.cos(a) * 14, 1), round(s['c'][1] + math.sin(a) * 14 + 6, 1)]
json.dump(out, open('city/stories_all.json', 'w'))
open('city/stories.js', 'w').write('window.STORIES = ' + json.dumps({'themes': {k: dict(label=v[0], color=v[1]) for k, v in THEMES.items()}, 'stories': out}, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(f"{len(out)} stories · {len({s['hood'] for s in out})} neighbourhoods · {os.path.getsize('city/stories.js') / 1e6:.1f} MB")
for p in problems[:30]: print('  !', p)
if len(problems) > 30: print(f'  … {len(problems) - 30} more')
