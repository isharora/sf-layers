# Layers: San Francisco in Time

An illustrated, time-travelling map of San Francisco. Every building is coloured by the year it was built. Just over 2,000 sourced stories are pinned to the places where they happened, and you can search any address to read the stories closest to it.

**Live map:** https://isharora.github.io/sf-layers/ · **Alamo Square in detail:** https://isharora.github.io/sf-layers/alamo.html

## Data
- Buildings, parcels (year built), street trees, landmarks and addresses: [DataSF](https://data.sf.gov)
- Streets, parks and water: © OpenStreetMap contributors
- Stories: researched from the sources cited on each story. Stories from the second research pass were checked against those sources; earlier ones haven't had that separate check yet. Corrections are welcome.

## Building
`fetch_city.py` downloads the raw data. `build_city.py`, `build_addresses.py` and `build_city_stories.py` produce `city/`. To view it locally, serve the folder over HTTP, for example with `python3 -m http.server`.
