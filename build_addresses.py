#!/usr/bin/env python3
"""Pack every San Francisco street address (city EAS) into a compact typeahead index: city/addr.json."""
import json, math, re, collections
LON0, LAT0 = -122.44, 37.76
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
def xy(lon, lat): return round((lon - LON0) * KX), round(-(lat - LAT0) * KY)
def nice(st):  # "01ST ST" -> "1st St", "O'FARRELL ST" -> "O'Farrell St"
    w = []
    for t in st.split():
        t = re.sub(r'^0(\d)', r'\1', t)
        t = t.lower() if re.match(r'^\d', t) else t.title()
        w.append(re.sub(r"\bMc([a-z])", lambda m: 'Mc' + m.group(1).upper(), t))
    return ' '.join(w).replace("O'farrell", "O'Farrell")
streets, seen, marks = collections.defaultdict(dict), set(), []
for r in json.load(open('data_city/addresses.json')):
    try: num = int(r['address_number']); lon, lat = float(r['longitude']), float(r['latitude'])
    except Exception: continue
    st = ' '.join(filter(None, [r.get('street_name'), r.get('street_type')])).strip()
    if not st: continue
    x, y = xy(lon, lat)
    streets[st].setdefault(num, (x, y))
    lm = (r.get('complete_landmark_name') or '').strip()
    if lm and lm.lower() not in seen: seen.add(lm.lower()); marks.append([lm, f'{num} {nice(st)}', x, y])
out = []
for st in sorted(streets):
    flat, p = [], (0, 0, 0)  # delta-coded: number, x, y
    for n in sorted(streets[st]): x, y = streets[st][n]; flat += [n - p[0], x - p[1], y - p[2]]; p = (n, x, y)
    out.append([nice(st), flat])
json.dump({'streets': out, 'marks': marks}, open('city/addr.json', 'w'), separators=(',', ':'))
import os
print(len(out), 'streets', sum(len(f) // 3 for _, f in out), 'addresses', len(marks), 'named places', f"{os.path.getsize('city/addr.json')/1e6:.1f} MB")
