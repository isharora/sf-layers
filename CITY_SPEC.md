# City-wide story specification: "Layers: San Francisco"

We're expanding an illustrated, time-travelling map of San Francisco to the whole city. Tapping a place reveals short, vivid, **true** stories. Match the quality of the existing Alamo Square stories: specific, human, surprising and rigorously sourced.

## Your assignment
You get one neighbourhood (a polygon file) and an era slice. Only write stories whose place lies **inside your neighbourhood polygon** and whose main year falls **inside your era slice**. Other researchers cover the other eras of your neighbourhood.
- Polygon: `/Users/ishita/sf-layers/regions/<slug>.json` (GeoJSON geometry, lon/lat).
- **Excluded area:** the blocks around Alamo Square are already done. Skip any place inside this polygon (lon, lat): (-122.4245, 37.78435), (-122.44751, 37.78107), (-122.44514, 37.76929), (-122.42224, 37.77293).

## Output
Write a JSON array to the file path you are given. Aim for **12–16 strong stories**, spread across the neighbourhood rather than clustered on one corner, and across different topics.

```json
{
  "id": "<slug>-<short-story-slug>",
  "title": "…",                         // evocative, ≤ 8 words
  "theme": "…",                         // exactly one of the THEMES below
  "year": 1906, "yearEnd": null,        // main year; end year for spans
  "place": { "label": "…", "lat": 37.0, "lon": -122.0, "precision": "building|block|street|area" },
  "hook": "…",                          // ≤ 30 words, makes you want to read on
  "story": "…",                         // 110–220 words, narrative, concrete, true; cite with [1], [2]
  "people": [{ "name": "…", "role": "…" }],
  "sources": [{ "title": "…", "publisher": "…", "year": 2011, "url": "https://…", "supports": "…" }],   // 2–4
  "photo": null                          // optional; only clearly free-to-reuse images (Wikimedia Commons PD/CC, LoC "no known restrictions"): {url, page, credit, license, year}
}
```

THEMES (pick one per story): `indigenous-early` (Ohlone, Spanish/Mexican era, pre-Gold Rush), `gold-rush-victorian` (1848–1905 city-building, Victorian life), `quake1906` (the earthquake, fire, refugee camps, rebuilding), `communities` (immigrant and ethnic communities, neighbourhoods and faith), `labor-industry` (work, waterfront, factories, strikes, commerce), `war-military` (forts, shipyards, wartime), `civil-rights` (activism, displacement, redevelopment, protest), `arts-counterculture` (music, literature, Beats, hippies, punk, film), `lgbtq`, `architecture-landmarks` (buildings, engineering, landmarks), `parks-nature` (parks, dunes, shoreline, wildlife), `modern-city` (late 20th century to today).

## Truth rules (strict)
- Every specific fact (names, dates, numbers, addresses, quotes) must be supported by a source **you actually opened**. Never invent or embellish. When sources disagree, say so in the story or leave the detail out.
- Good sources:
  - SF Planning (landmark designation reports, historic context statements), National Register nominations, NPS / Presidio Trust
  - SF Public Library, Western Neighborhoods Project (outsidelands.org, OpenSFHistory), FoundSF (a community wiki: check it against another source where you can), the Museum of the City of SF (sfmuseum.org), NoeHill (quotes the city's landmark reports)
  - Chinese Historical Society of America, GLBT Historical Society, Calisphere, newspapers (SF Chronicle / SFGATE, Examiner), books and academic papers, and Wikipedia only as a pointer to its sources
- **Web search is limited.** Use WebSearch sparingly (about 20 queries at most) and prefer fetching known sources directly with WebFetch or `curl -sL`. For example FoundSF pages (`https://www.foundsf.org/index.php?title=...`), `https://www.outsidelands.org/...`, `https://noehill.com/...`, sfmuseum.org and Wikipedia articles, then follow their citations.
- Write for curious locals: warm, specific, surprising, no fluff. No speculation presented as fact.

## Geocoding
Use the city's address database (open, no key):
`curl -sL "https://data.sf.gov/resource/3mea-di5p.json?\$where=address='600 MONTGOMERY ST'"` → `latitude`, `longitude`.
Addresses are in caps with abbreviated street types (ST, AVE, BLVD). For an intersection, park or vanished address, use the nearest existing address or a point inside the site, and set precision to `block`, `street` or `area`.

## Validate before finishing
Check every point is inside your polygon and outside the excluded area, and that the JSON is valid:
```
python3 - <<'PY'
import json; from shapely.geometry import shape, Point, Polygon
reg = shape(json.load(open('/Users/ishita/sf-layers/regions/<slug>.json'))['geometry'])
ex = Polygon([(-122.4245,37.78435),(-122.44751,37.78107),(-122.44514,37.76929),(-122.42224,37.77293)])
d = json.load(open('<your output file>'))
for s in d:
    p = Point(s['place']['lon'], s['place']['lat'])
    assert all(k in s for k in ['id','title','theme','year','place','hook','story','sources']), s.get('id')
    print(('OK ' if reg.buffer(0.0004).contains(p) and not ex.contains(p) else 'OUT'), s['id'])
print(len(d), 'stories')
PY
```
Fix or remove anything marked OUT. Return a short list of story titles with year and place.
