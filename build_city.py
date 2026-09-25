#!/usr/bin/env python3
"""Build the tiled city-wide map data for Layers: San Francisco (north-up, local metres)."""
import json, math, os, glob, re, collections
from shapely.geometry import shape, Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union
from shapely import affinity

LON0, LAT0 = -122.44, 37.76
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
TILE = 400
def xy(lon, lat): return ((lon - LON0) * KX, -(lat - LAT0) * KY)
def proj(g):
    from shapely.ops import transform
    return transform(lambda x, y, z=None: xy(x, y), g)
def rings(g, nd=1):
    if g.is_empty: return []
    gs = [g] if isinstance(g, Polygon) else list(getattr(g, 'geoms', []))
    return [[[round(x, nd), round(y, nd)] for x, y in p.exterior.coords] for p in gs if isinstance(p, Polygon) and p.area > 2]
os.makedirs('city/tiles', exist_ok=True)

def era_of(y):
    if not y or y == 1900: return 'unk'
    return 'vic' if y < 1906 else 'edw' if y < 1930 else 'deco' if y < 1950 else 'mod' if y < 1980 else 'now'

# ---- land = union of neighbourhoods ----
regions = [json.load(open(f)) for f in sorted(glob.glob('regions/*.json'))]
land = unary_union([proj(shape(r['geometry'])).buffer(0) for r in regions]).simplify(4)
minx, miny, maxx, maxy = land.bounds
hoods = []
for r in regions:
    g = proj(shape(r['geometry'])).buffer(0); c = g.representative_point()
    hoods.append(dict(n=r['name'], slug=r['slug'], c=[round(c.x), round(c.y)], a=round(g.area / 1e6, 2), p=rings(g.simplify(8), 0)))

# ---- parcels: year built + addresses, grouped into blocks ----
parcels = json.load(open('data_city/parcels.json'))
year_by_apn, blocks_raw = {}, collections.defaultdict(list)
for p in parcels:
    apn = p.get('apn') or ''
    yb = p.get('yearbuilt') or ''
    yr = int(yb) if yb.isdigit() and 1840 < int(yb) < 2030 else None
    year_by_apn[apn] = yr
    if not p.get('g'): continue
    try: g = proj(shape(p['g'])).buffer(0)
    except Exception: continue
    st = (p.get('stname') or '').title()
    st = re.sub(r"\bMc([a-z])", lambda m: 'Mc' + m.group(1).upper(), st).replace("O'farrell", "O'Farrell")
    blocks_raw[apn[:-3] if len(apn) > 3 else apn].append((g, yr, (st + ' ' + (p.get('sttype') or '').title()).strip()))
print('parcels', len(parcels), 'blocks', len(blocks_raw))

blocks = []
for bid, ps in blocks_raw.items():
    try: u = unary_union([g.buffer(0.8) for g, _, _ in ps]).buffer(-0.8).simplify(1.2)
    except Exception: continue
    if u.is_empty or u.area < 150: continue
    cnt = collections.Counter(era_of(y) for _, y, _ in ps)
    streets = [s for s, _ in collections.Counter(s for _, _, s in ps if s and s != 'Unknown').most_common(2)]
    dated = sorted(y for _, y, _ in ps if y and y != 1900)
    known = {k: v for k, v in cnt.items() if k != 'unk'}
    dom = max(known, key=known.get) if known else 'unk'
    minb = u.bounds
    blocks.append(dict(id=bid, p=rings(u), bb=[round(v) for v in minb], dom=dom, cnt=dict(cnt), st=streets, old=dated[0] if dated else None, n=len(ps)))
print('blocks built', len(blocks))

# ---- buildings into tiles ----
tiles = collections.defaultdict(lambda: {'b': [], 't': []})
for b in json.load(open('data_city/buildings.json')):
    if not b.get('g'): continue
    try: g = proj(shape(b['g']))
    except Exception: continue
    mb = (b.get('mblr') or '')[2:]
    yr = year_by_apn.get(mb)
    h = float(b.get('hgt_median_m') or 0)
    gs = [g] if isinstance(g, Polygon) else list(getattr(g, 'geoms', []))
    for poly in gs:
        if not isinstance(poly, Polygon) or poly.area < 4: continue
        c = poly.representative_point(); i, j = math.floor(c.x / TILE), math.floor(c.y / TILE)
        ox, oy = i * TILE, j * TILE
        pts = [(round((x - ox) * 2), round((y - oy) * 2)) for x, y in poly.exterior.coords[:-1]]
        flat = [yr or 0, round(h)]
        px, py = 0, 0
        for x, y in pts: flat += [x - px, y - py]; px, py = x, y
        tiles[(i, j)]['b'].append(flat)
for t in json.load(open('data_city/trees.json')):
    try: x, y = xy(float(t['longitude']), float(t['latitude']))
    except Exception: continue
    i, j = math.floor(x / TILE), math.floor(y / TILE)
    tiles[(i, j)]['t'] += [round((x - i * TILE) * 2), round((y - j * TILE) * 2)]
for (i, j), v in tiles.items():
    json.dump(v, open(f'city/tiles/{i}_{j}.json', 'w'), separators=(',', ':'))
print('tiles', len(tiles), 'buildings', sum(len(v['b']) for v in tiles.values()))

# ---- streets, parks, water ----
streets, parks, labels_src = [], [], collections.defaultdict(list)
CLS = {'motorway': 4, 'trunk': 4, 'primary': 3, 'secondary': 3, 'tertiary': 2, 'residential': 1, 'unclassified': 1, 'living_street': 1, 'pedestrian': 1}
for el in json.load(open('data_city/osm.json')):
    t = el.get('tags', {})
    try:
        if el['type'] == 'way' and 'highway' in t and 'geometry' in el:
            hw = t['highway']; k = CLS.get(hw, 0)
            if hw in ('footway', 'path', 'steps') and t.get('footway') in ('sidewalk', 'crossing'): continue
            ln = proj(LineString([(g['lon'], g['lat']) for g in el['geometry']])).simplify(1.5)
            if ln.is_empty or len(ln.coords) < 2: continue
            if k in (0, 3, 4): streets.append(dict(k=k, p=[[round(x), round(y)] for x, y in ln.coords]))
            if k >= 1 and t.get('name') and hw != 'motorway': labels_src[t['name']].append((ln, k))
        elif ('leisure' in t or 'natural' in t) and el['type'] == 'way' and 'geometry' in el and len(el['geometry']) > 3:
            g = proj(Polygon([(q['lon'], q['lat']) for q in el['geometry']])).buffer(0).simplify(2)
            kind = 'water' if t.get('natural') == 'water' else 'sand' if t.get('natural') in ('beach', 'sand') else 'golf' if t.get('leisure') == 'golf_course' else 'park'
            if g.area > 400: parks.append(dict(k=kind, n=t.get('name', ''), p=rings(g)))
        elif el['type'] == 'relation':
            kind = 'water' if t.get('natural') == 'water' else 'golf' if t.get('leisure') == 'golf_course' else 'park'
            for m in el.get('members', []):
                if m.get('role') == 'outer' and m.get('geometry') and len(m['geometry']) > 3:
                    g = proj(Polygon([(q['lon'], q['lat']) for q in m['geometry']])).buffer(0).simplify(2)
                    if g.area > 400: parks.append(dict(k=kind, n=t.get('name', ''), p=rings(g)))
    except Exception:
        continue
# street labels: one anchor per ~700 m of each named street, on its longest pieces
labels = []
for name, lns in labels_src.items():
    rank = max(k for _, k in lns)  # 3 = primary/secondary/trunk: labelled from mid zoom
    lns = sorted((l for l, _ in lns), key=lambda l: -l.length); taken = []
    for l in lns:
        if l.is_empty or l.length < 110: break
        mid = l.interpolate(0.5, normalized=True)
        if any(mid.distance(q) < 700 for q in taken): continue
        a, b = l.interpolate(0.4, normalized=True), l.interpolate(0.6, normalized=True)
        ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
        if ang > 90: ang -= 180
        if ang < -90: ang += 180
        short = name.replace(' Street', ' St').replace(' Avenue', ' Ave').replace(' Boulevard', ' Blvd').replace(' Drive', ' Dr')
        labels.append([short, round(mid.x), round(mid.y), round(ang, 1), min(rank, 3)]); taken.append(mid)

# ---- landmarks ----
lms = []
for l in json.load(open('data_city/landmarks.json')):
    try:
        c = proj(shape(l['the_geom'])).representative_point(); c.x
    except Exception: continue
    doc = l.get('designationdocument'); doc = doc.get('url', '') if isinstance(doc, dict) else (doc or '')
    lms.append(dict(no=int(float(l.get('landmarkno') or 0)), name=(l.get('name') or '').replace('\n', ' '), addr=l.get('address') or '', year=int(float(l.get('yeardesignated') or 0)), doc=doc, c=[round(c.x), round(c.y)]))

base = dict(origin=[LON0, LAT0], tile=TILE, bounds=[round(minx), round(miny), round(maxx), round(maxy)], land=rings(land, 0),
            hoods=hoods, blocks=blocks, parks=parks, streets=streets, labels=labels, landmarks=lms,
            tiles=sorted(f'{i}_{j}' for i, j in tiles))
open('city/base.js', 'w').write('window.BASE = ' + json.dumps(base, separators=(',', ':')) + ';\n')
print(f"base.js {os.path.getsize('city/base.js') / 1e6:.1f} MB · {len(blocks)} blocks · {len(streets)} streets · {len(parks)} parks · {len(labels)} labels · {len(lms)} landmarks")
