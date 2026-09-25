#!/usr/bin/env python3
"""Route each walking tour along real streets (OpenStreetMap) and write city/tours.js.

Input: tours_src/*.tour.json (stops chosen from city/stories_all.json).
Each leg gets a street-following path, its length, and the main streets it follows.
"""
import json, glob, math, heapq, collections
from shapely.geometry import LineString

LON0, LAT0 = -122.44, 37.76
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
def xy(lon, lat): return ((lon - LON0) * KX, -(lat - LAT0) * KY)
WALK = {'footway', 'path', 'steps', 'pedestrian', 'residential', 'unclassified', 'living_street', 'tertiary', 'secondary', 'primary', 'trunk'}

# ---- walking graph: nodes are exact coordinates shared by touching ways ----
idx, pts, adj = {}, [], collections.defaultdict(list)
def node(lon, lat):
    k = (round(lon, 7), round(lat, 7))
    if k not in idx: idx[k] = len(pts); pts.append(xy(lon, lat))
    return idx[k]
for el in json.load(open('data_city/osm.json')):
    t = el.get('tags', {})
    if el['type'] != 'way' or t.get('highway') not in WALK or 'geometry' not in el: continue
    if t.get('access') in ('private', 'no'): continue
    side = t.get('footway') == 'sidewalk'  # usable, but prefer the named street it runs beside
    name = t.get('name') or ('stairs' if t['highway'] == 'steps' else '')
    g = el['geometry']
    for a, b in zip(g, g[1:]):
        u, v = node(a['lon'], a['lat']), node(b['lon'], b['lat'])
        d = math.dist(pts[u], pts[v]) * (1.15 if t['highway'] == 'steps' else 1.06 if side else 1)
        adj[u].append((v, d, name)); adj[v].append((u, d, name))
print('graph', len(pts), 'nodes')

# keep only the main connected network (stray paths and private courtyards are islands)
comp, main = {}, None
for s0 in range(len(pts)):
    if s0 in comp or not adj[s0]: continue
    st, members = [s0], [s0]; comp[s0] = s0
    while st:
        u = st.pop()
        for v, _, _ in adj[u]:
            if v not in comp: comp[v] = s0; st.append(v); members.append(v)
    if main is None or len(members) > main[1]: main = (s0, len(members))
print('main network', main[1], 'nodes')
# spatial grid for snapping stops to the nearest node on the main network
G = 60
grid = collections.defaultdict(list)
for i, (x, y) in enumerate(pts):
    if comp.get(i) == main[0]: grid[(int(x // G), int(y // G))].append(i)
def snap(x, y):
    best, bd = None, 1e18
    for r in range(1, 12):
        cx, cy = int(x // G), int(y // G)
        for i in range(cx - r, cx + r + 1):
            for j in range(cy - r, cy + r + 1):
                for n in grid.get((i, j), ()):
                    d = (pts[n][0] - x) ** 2 + (pts[n][1] - y) ** 2
                    if d < bd: bd, best = d, n
        if best is not None and math.sqrt(bd) < r * G: return best
    return best

def route(a, b):  # A* on the walking graph
    tx, ty = pts[b]; h = lambda n: math.hypot(pts[n][0] - tx, pts[n][1] - ty)
    dist, prev, pq = {a: 0}, {}, [(h(a), a)]
    while pq:
        _, u = heapq.heappop(pq)
        if u == b: break
        du = dist[u]
        for v, w, nm in adj[u]:
            nd = du + w
            if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = (u, nm, w); heapq.heappush(pq, (nd + h(v), v))
    if b not in dist: return None
    path, names, n = [b], [], b
    while n != a:
        u, nm, w = prev[n]; path.append(u); names.append((nm, w)); n = u
    path.reverse(); names.reverse()
    return dist[b], [pts[i] for i in path], names

def street_summary(names):
    runs = []
    for nm, w in names:
        if runs and runs[-1][0] == nm: runs[-1][1] += w
        else: runs.append([nm, w])
    main = [nm for nm, w in runs if nm and w >= 70]
    out = []
    for nm in main:
        if not out or out[-1] != nm: out.append(nm)
    return out[:3]

def bearing(p, q):
    a = math.degrees(math.atan2(q[0] - p[0], -(q[1] - p[1]))) % 360  # 0 = north
    return ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'][int((a + 22.5) // 45) % 8]

stories = {s['id']: s for s in json.load(open('city/stories_all.json'))}
tours = []
for f in sorted(glob.glob('tours_src/*.tour.json')):
    t = json.load(open(f))
    stops = [s for s in t['stops'] if s['id'] in stories]
    if len(stops) < len(t['stops']): print('  ! missing stop ids in', f)
    legs, total = [], 0
    for s0, s1 in zip(stops, stops[1:]):
        p, q = stories[s0['id']]['c'], stories[s1['id']]['c']
        a, b = snap(*p), snap(*q)
        r = route(a, b) if a is not None and b is not None and a != b else None
        if r:
            d, path, names = r
            path = [tuple(p)] + path + [tuple(q)]
            line = LineString(path).simplify(2.5)
            d = d + math.dist(p, pts[a]) + math.dist(q, pts[b])
            legs.append(dict(m=round(d), via=street_summary(names), dir=bearing(p, q), p=[[round(x), round(y)] for x, y in line.coords]))
        else:
            legs.append(dict(m=round(math.dist(p, q)), via=[], dir=bearing(p, q), p=[[round(p[0]), round(p[1])], [round(q[0]), round(q[1])]]))
        total += legs[-1]['m']
    tours.append(dict(id=t['id'], title=t['title'], tagline=t.get('tagline', ''), intro=t['intro'], stops=stops, legs=legs, m=round(total),
                      hood=collections.Counter(stories[s['id']]['hood'] for s in stops).most_common(1)[0][0]))
    detour = total / max(1, sum(math.dist(stories[a['id']]['c'], stories[b['id']]['c']) for a, b in zip(stops, stops[1:])))
    print(f"{t['id']}: {len(stops)} stops · {total / 1000:.1f} km walking (x{detour:.2f} of straight line) · longest leg {max(l['m'] for l in legs)} m")
open('city/tours.js', 'w').write('window.TOURS = ' + json.dumps(tours, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(len(tours), 'tours')
