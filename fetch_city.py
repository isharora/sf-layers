#!/usr/bin/env python3
"""Download city-wide base data for Layers: San Francisco."""
import json, os, time, urllib.request, urllib.parse
os.makedirs('data_city', exist_ok=True)

def soda(dsid, select, where=None, order=':id', page=50000):
    rows, off = [], 0
    while True:
        q = {'$select': select, '$limit': page, '$offset': off, '$order': order}
        if where: q['$where'] = where
        url = f"https://data.sf.gov/resource/{dsid}.json?" + urllib.parse.urlencode(q)
        for a in range(5):
            try:
                chunk = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sf-layers'}), timeout=300)); break
            except Exception as e:
                err = e; time.sleep(5 * (a + 1))
        else:
            raise err
        rows += chunk; off += page
        print(f'  {dsid}: {len(rows)}', flush=True)
        if len(chunk) < page: return rows

def save(name, rows):
    json.dump(rows, open(f'data_city/{name}.json', 'w'), separators=(',', ':'))
    print(f'{name}: {len(rows)} rows', flush=True)

if not os.path.exists('data_city/buildings.json'):
    save('buildings', soda('ynuv-fyni', 'mblr, hgt_median_m, simplify_preserve_topology(shape, 0.000004) as g'))
if not os.path.exists('data_city/parcels.json'):
    save('parcels', soda('3tsw-4idn', 'apn, yearbuilt, lowstnum, stname, sttype, simplify_preserve_topology(the_geom, 0.000006) as g'))
if not os.path.exists('data_city/trees.json'):
    save('trees', soda('tkzw-k3nq', 'latitude, longitude', 'latitude is not null'))
if not os.path.exists('data_city/landmarks.json'):
    save('landmarks', soda('97yj-54sx', 'apn, name, address, landmarkno, yeardesignated, designationdocument, the_geom'))
if not os.path.exists('data_city/osm.json'):
    B = '37.700,-122.525,37.835,-122.350'
    q = f'''[out:json][timeout:300];
(way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified|living_street|pedestrian|footway|path|steps)$"]({B});
 way["leisure"~"^(park|garden|golf_course|nature_reserve)$"]({B});
 relation["leisure"~"^(park|nature_reserve|golf_course)$"]({B});
 way["natural"~"^(water|beach|sand)$"]({B});
 relation["natural"="water"]({B}););
out geom tags;'''
    for a in range(4):
        try:
            osm = json.load(urllib.request.urlopen(urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'sf-layers'}), timeout=600)); break
        except Exception as e:
            err = e; time.sleep(20)
    else:
        raise err
    save('osm', osm['elements'])
print('done')
