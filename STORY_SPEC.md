# Story specification: "Layers: Alamo Square & Environs"

We're building an illustrated, time-travelling map of the neighbourhood around Alamo Square, San Francisco. Tapping a block reveals its stories. **Stories are the heart of the project**: vivid, human, specific and true.

## Study area
Six blocks in every direction around Alamo Square: roughly Gough St (east) to Masonic Ave (west), O'Farrell St (north) to Waller St (south). Corner coordinates (lon, lat):
NE (-122.4245, 37.78435) · NW (-122.44751, 37.78107) · SW (-122.44514, 37.76929) · SE (-122.42224, 37.77293).
Only include stories whose place lies inside this area. Stories right on a boundary street count.

## Output
Write a JSON array of story objects to `/Users/ishita/sf-layers/stories/<your-theme-id>.json`. Aim for **10–18 strong stories**. Prefer depth and specificity over volume.

```json
{
  "id": "theme-short-slug",
  "title": "The Ham and Eggs Fire",                    // evocative, ≤ 8 words
  "year": 1906,                                        // main year (number)
  "yearEnd": null,                                     // for spans, else null
  "place": {
    "label": "395 Hayes Street",                       // a human-readable place
    "lat": 37.7768, "lon": -122.4232,                  // geocoded (see below)
    "precision": "building"                            // building | block | street | area
  },
  "hook": "…",                                         // ≤ 30 words: the line that makes you want to read on
  "story": "…",                                        // 110–220 words, narrative, concrete, true; mark citations [1], [2]
  "people": [{ "name": "…", "role": "…" }],            // real people in the story (may be empty)
  "sources": [                                         // 2–4, the more authoritative the better
    { "title": "…", "publisher": "…", "year": 2011, "url": "https://…", "supports": "which claim" }
  ],
  "photo": null                                        // OPTIONAL, see below
}
```

## Truth rules (strict)
- Every specific fact (names, dates, numbers, addresses, quotes) must be supported by one of your sources, and you must have actually opened the source (WebFetch) to confirm it. **Never invent or embellish.** If sources disagree, say so or leave the detail out.
- Good sources:
  - SF Planning landmark designation reports and historic context statements, National Register nominations, NPS
  - SF Public Library, Western Neighborhoods Project (OpenSFHistory / outsidelands.org), FoundSF (a community wiki: check it against another source where you can)
  - Museum of the City of SF (sfmuseum.org), Calisphere, newspapers (SF Chronicle, SF Examiner), academic books and papers, and Wikipedia only as a pointer to its cited sources
- Quotes: only if you found them verbatim in a source.
- Write for curious locals: warm, specific, surprising, no fluff. Past tense for history. No speculation presented as fact.

## Geocoding
Use the city's address database (open, no key):
`curl -sL "https://data.sf.gov/resource/3mea-di5p.json?\$where=address='710 STEINER ST'"` → `latitude`, `longitude` (addresses in caps, street type abbreviated: ST, AVE, BLVD).
For an intersection or a vanished address, use the nearest existing address or the midpoint of the block, and set precision to `block` or `street`. Check the point is inside the study area.

## Photos (optional, secondary)
Only include a photo when it is clearly free to reuse, e.g. Wikimedia Commons with a public-domain or CC licence, or the Library of Congress with "no known restrictions":
`"photo": { "url": "<direct image URL>", "page": "<source page>", "credit": "…", "license": "…", "year": 1906 }`. Otherwise leave it `null`.

## Validate before finishing
`python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert all(k in s for s in d for k in ['id','title','year','place','hook','story','sources']); print(len(d),'stories ok')" /Users/ishita/sf-layers/stories/<file>.json`
Return a short list of your story titles with their year and place.
