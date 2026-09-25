#!/usr/bin/env python3
"""Fetch base geometry and historic records for the study area (six blocks around Alamo Square)."""
import json, urllib.request, urllib.parse, time

# study area: Gough–Masonic × O'Farrell–Waller (street-grid corners from OpenStreetMap)
AOI = [(-122.4245, 37.7843489), (-122.4475058, 37.7810734), (-122.4451431, 37.7692913), (-122.4222415, 37.7729297)]
pad = lambda pts, d=0.0012: pts  # corners already sit on street centrelines; clip later in the renderer
WKT = 'MULTIPOLYGON (((' + ', '.join(f'{x} {y}' for x, y in AOI + [AOI[0]]) + ')))'
BOX = dict(n=max(y for _, y in AOI) + .001, s=min(y for _, y in AOI) - .001, e=max(x for x, _ in AOI) + .001, w=min(x for x, _ in AOI) - .001)

def soda(dsid, where, select=None, limit=50000):
    q = {'$where': where, '$limit': limit}
    if select: q['$select'] = select
    url = f"https://data.sf.gov/resource/{dsid}.json?" + urllib.parse.urlencode(q)
    for a in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sf-layers'}), timeout=120))
        except Exception as e:
            err = e; time.sleep(3)
    raise err

def save(name, rows):
    json.dump(rows, open(f'data/{name}.json', 'w'))
    print(f'{name:22} {len(rows):>6} rows')

save('buildings', soda('ynuv-fyni', f"intersects(shape, '{WKT}')", 'sf16_bldgid, mblr, hgt_median_m, shape'))
save('parcels_historic', soda('3tsw-4idn', f"intersects(the_geom, '{WKT}')"))
save('landmarks', soda('97yj-54sx', f"intersects(the_geom, '{WKT}')"))
save('historic_districts', soda('63x5-g3m4', f"intersects(the_geom, '{WKT}')"))
save('landmark_districts', soda('knm6-5ej6', f"intersects(geometry, '{WKT}')"))
save('context_statements', soda('43um-8u7u', f"intersects(the_geom, '{WKT}')"))
save('trees', soda('tkzw-k3nq', f"latitude between {BOX['s']} and {BOX['n']} and longitude between {BOX['w']} and {BOX['e']}", 'treeid, species, latitude, longitude, planteddate, dbhrange'))

# streets, park and water from OpenStreetMap
q = f'''[out:json][timeout:90];
(way["highway"]({BOX['s']},{BOX['w']},{BOX['n']},{BOX['e']});
 way["leisure"~"park|garden|playground"]({BOX['s']},{BOX['w']},{BOX['n']},{BOX['e']});
 relation["leisure"="park"]({BOX['s']},{BOX['w']},{BOX['n']},{BOX['e']});
 way["amenity"~"place_of_worship|school|library"]({BOX['s']},{BOX['w']},{BOX['n']},{BOX['e']}););
out geom tags;'''
osm = json.load(urllib.request.urlopen(urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'sf-layers'}), timeout=180))
save('osm', osm['elements'])
json.dump({'aoi': AOI, 'box': BOX}, open('data/aoi.json', 'w'))
