#!/usr/bin/env python3
"""Project, rotate, clip and simplify the raw data into a compact map.json for the illustrated map."""
import json, math
from shapely.geometry import shape, Polygon, MultiPolygon, LineString, Point, mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely import affinity

A = json.load(open('data/aoi.json'))
AOI_LL = A['aoi']
LAT0, LON0 = 37.7768, -122.4349
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
def xy(lon, lat): return ((lon - LON0) * KX, -(lat - LAT0) * KY)
# rotate so O'Farrell Street runs horizontally
(x1, y1), (x2, y2) = xy(*AOI_LL[1]), xy(*AOI_LL[0])
ANG = math.degrees(math.atan2(y2 - y1, x2 - x1))
def proj_geom(g):
    g2 = shapely_transform(g)
    return affinity.rotate(g2, -ANG, origin=(0, 0))
def shapely_transform(g):
    from shapely.ops import transform
    return transform(lambda x, y, z=None: xy(x, y), g)

aoi = proj_geom(Polygon(AOI_LL))
view = aoi.buffer(70, join_style=2)           # a little context beyond the study area
minx, miny, maxx, maxy = view.bounds
def r(v): return round(v, 1)
def ring(coords): return [[r(x - minx), r(y - miny)] for x, y in coords]
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): g = [g]
    elif isinstance(g, MultiPolygon): g = list(g.geoms)
    else: g = [x for x in getattr(g, 'geoms', []) if isinstance(x, Polygon)]
    return [ring(p.exterior.coords) for p in g if p.area > 1]

# parcels with year built + address
parcels = []
for p in json.load(open('data/parcels_historic.json')):
    try: g = proj_geom(shape(p['the_geom']))
    except Exception: continue
    yb = p.get('yearbuilt', '')
    def fixname(s):
        s = s.title()
        s = __import__('re').sub(r"\bMc([a-z])", lambda m: 'Mc' + m.group(1).upper(), s)
        return s.replace("O'farrell", "O'Farrell").replace("Ofarrell", "O'Farrell")
    p['stname'] = fixname(p.get('stname') or '')
    parcels.append(dict(g=g, apn=p.get('apn', ''), yr=int(yb) if yb.isdigit() and 1840 < int(yb) < 2030 else None,
                        addr=' '.join(x for x in [p.get('lowstnum'), p.get('stname') or '', (p.get('sttype') or '').title()] if x),
                        name=p.get('name') or ''))
ptree = STRtree([p['g'] for p in parcels])

# buildings
bld = []
for b in json.load(open('data/buildings.json')):
    try: g = proj_geom(shape(b['shape'])).intersection(view)
    except Exception: continue
    if g.is_empty: continue
    g = g.simplify(0.35)
    c = g.representative_point()
    yr, addr = None, ''
    for i in ptree.query(c):
        if parcels[i]['g'].contains(c): yr, addr = parcels[i]['yr'], parcels[i]['addr']; break
    h = float(b.get('hgt_median_m') or 0)
    for pr in polys(g):
        bld.append(dict(p=pr, h=round(h, 1), y=yr, a=addr))

# blocks = union of parcels sharing an assessor block number
by_block = {}
for p in parcels: by_block.setdefault(p['apn'][:4], []).append(p)
blocks = []
for bn, ps in by_block.items():
    u = unary_union([p['g'].buffer(0.6) for p in ps]).buffer(-0.6)
    u = u.intersection(view)
    if u.is_empty or u.area < 200: continue
    c = u.representative_point()
    yrs = sorted(p['yr'] for p in ps if p['yr'] and p['yr'] != 1900)
    blocks.append(dict(id=bn, p=polys(u.simplify(0.8)), c=[r(c.x - minx), r(c.y - miny)], n=len(ps),
                       inAoi=aoi.contains(c), oldest=yrs[0] if yrs else None))

# OpenStreetMap: streets, parks, notable buildings
streets, parks, labels = [], [], []
MAJOR = {'primary': 3, 'secondary': 3, 'tertiary': 2, 'residential': 1, 'unclassified': 1, 'living_street': 1}
for el in json.load(open('data/osm.json')):
    t = el.get('tags', {})
    if el['type'] == 'way' and 'highway' in t and 'geometry' in el:
        hw = t['highway']
        if hw in MAJOR or hw in ('footway', 'path', 'pedestrian', 'steps'):
            ln = proj_geom(LineString([(g['lon'], g['lat']) for g in el['geometry']])).intersection(view.buffer(40))
            if ln.is_empty: continue
            for part in (getattr(ln, 'geoms', None) or [ln]):
                if isinstance(part, LineString) and len(part.coords) > 1:
                    streets.append(dict(k=MAJOR.get(hw, 0), n=t.get('name', ''), p=ring(part.coords)))
    elif t.get('leisure') in ('park', 'garden', 'playground') and el['type'] == 'way' and 'geometry' in el:
        try: g = proj_geom(Polygon([(g['lon'], g['lat']) for g in el['geometry']])).intersection(view)
        except Exception: continue
        if not g.is_empty and g.area > 150:
            parks.append(dict(n=t.get('name', ''), k=t['leisure'], p=polys(g)))
    elif el['type'] == 'relation' and t.get('leisure') == 'park':
        outers = [m for m in el.get('members', []) if m.get('role') == 'outer' and m.get('geometry')]
        for m in outers:
            try: g = proj_geom(Polygon([(q['lon'], q['lat']) for q in m['geometry']])).intersection(view)
            except Exception: continue
            if not g.is_empty and g.area > 150: parks.append(dict(n=t.get('name', ''), k='park', p=polys(g)))

# trees
trees = []
for t in json.load(open('data/trees.json')):
    try: pt = proj_geom(Point(float(t['longitude']), float(t['latitude'])))
    except Exception: continue
    if view.contains(pt): trees.append([r(pt.x - minx), r(pt.y - miny)])

# landmarks and historic districts
lms = []
for l in json.load(open('data/landmarks.json')):
    g = proj_geom(shape(l['the_geom'])); c = g.representative_point()
    lms.append(dict(no=int(float(l.get('landmarkno') or 0)), name=(l.get('name') or '').replace('\n', ' '), addr=l.get('address') or '',
                    year=int(float(l.get('yeardesignated') or 0)), doc=(l.get('designationdocument') or {}).get('url', '') if isinstance(l.get('designationdocument'), dict) else l.get('designationdocument', ''),
                    c=[r(c.x - minx), r(c.y - miny)]))
hds = []
for d in json.load(open('data/historic_districts.json')):
    g = proj_geom(shape(d['the_geom'])).intersection(view)
    if g.is_empty or g.area < 2000: continue
    hds.append(dict(name=d.get('name_1', ''), desc=d.get('description', ''), link=(d.get('link') or {}).get('url', '') if isinstance(d.get('link'), dict) else d.get('link', ''), p=polys(g.simplify(1.5))))

PLACES = [("Alamo Square", -122.4347, 37.7763, 'park'), ("Hayes Valley", -122.4262, 37.7757, 'hood'), ("The Fillmore", -122.4318, 37.7823, 'hood'),
          ("Western Addition", -122.4388, 37.7806, 'hood'), ("NoPa", -122.4418, 37.7768, 'hood'), ("Lower Haight", -122.4312, 37.7718, 'hood'),
          ("The Panhandle", -122.4452, 37.7722, 'park'), ("Duboce Park", -122.4335, 37.7697, 'park')]
places = []
for name, lon, lat, kind in PLACES:
    pt = proj_geom(Point(lon, lat))
    if view.contains(pt): places.append(dict(n=name, k=kind, c=[r(pt.x - minx), r(pt.y - miny)]))
out = dict(w=r(maxx - minx), h=r(maxy - miny), angle=round(ANG, 3), origin=[LON0, LAT0], offset=[r(minx), r(miny)],
           aoi=polys(aoi), buildings=bld, blocks=blocks, streets=streets, parks=parks, trees=trees, landmarks=lms, districts=hds, places=places)
json.dump(out, open('map.json', 'w'), separators=(',', ':'))
print(f"map {out['w']:.0f}×{out['h']:.0f} m, rotated {ANG:.2f}°: {len(bld)} buildings, {len(blocks)} blocks ({sum(b['inAoi'] for b in blocks)} in area), "
      f"{len(streets)} street segments, {len(parks)} parks, {len(trees)} trees, {len(lms)} landmarks, {len(hds)} districts")
import os; print('map.json', round(os.path.getsize('map.json') / 1e6, 2), 'MB')
