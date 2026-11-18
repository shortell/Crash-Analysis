# NYC Crash Analysis

A live dashboard of New York City motor vehicle crashes by zip code: where they happen, how severe they are, when they happen, and what causes them. It's built for **injury law firms** deciding where to advertise or open offices, but anyone can use it.

It is a static site with no server and no database. The browser queries [NYC Open Data](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95) directly, so the numbers are always current, and hosting costs nothing.

## Features

- **Live data**: every view is queried from the NYPD collisions dataset, which is updated daily.
- **Periods**: last 30 days, 90 days, year to date, 12 months, or a custom range back to July 2012. Every number is compared with the prior period of equal length.
- **Areas**: citywide or any borough. Ranks and deciles are recomputed within the selected area.
- **Metrics**: crashes, injuries, deaths, pedestrian and cyclist casualties, and crashes or injuries per 10,000 residents.
- **Zip map**: zip codes shaded white (low) to red (high) by decile, with hover details. Hovering a map zip highlights its table row and vice versa.
- **Density map**: the same metric per square mile, so large zips don't rank high just for being large. It pans, zooms and highlights in step with the main map.
- **Ranking table**: rank, value, multiple of the average zip, and change vs the prior period. Sortable, and exportable to CSV.
- **Trends**: daily, weekly or 30-day totals against the prior period.
- **When crashes happen**: an hour × weekday heat grid.
- **Causes and vehicles**: top contributing factors and vehicle types.
- **Zip details**: click any zip or search for one to see its totals, citywide and borough rank, trend, most dangerous intersections, and top factors.
- **Shareable URLs**: every filter lives in the URL, and the back button works.
- Light and dark themes, plus a mobile layout.

## How missing zip codes are handled

About a quarter of NYPD crash records have no zip code, but nearly all of those have coordinates. The dashboard groups those crashes by location and places each one into its zip with a point-in-polygon lookup against the zip boundaries. (The old version guessed with k-nearest-neighbours.) The few crashes with neither a zip nor usable coordinates are counted in a footnote under the map.

Change vs the prior period is computed from crashes recorded with a zip code in both periods, so the comparison is like for like.

## Project layout

```
index.html              the whole app (one page)
css/styles.css          styles, light and dark tokens
js/app.js               controller: URL state, loading, rendering
js/api.js               NYC Open Data (SoQL) queries + localStorage cache
js/stats.js             ranking, deciles, per-capita rates, time buckets
js/geo.js               zip polygons, point-in-polygon lookup
js/map.js               Leaflet choropleth
js/charts.js            Chart.js trend and bar charts, hour grid
data/nyc_zips.geojson   MODZCTA zip boundaries + population, borough, area (258 KB)
scripts/build_geojson.py  one-off script that produced the GeoJSON
tests/                  unit tests for stats.js and geo.js
```

Leaflet and Chart.js load from cdnjs. There is no build step.

## Run locally

```sh
python -m http.server 8000     # then open http://localhost:8000
node tests/run.mjs             # unit tests (or open tests/stats.test.html in the browser)
```

The page has to be served over HTTP, not opened as a file, because it loads ES modules and the GeoJSON with `fetch`.

## Deploy (free)

**GitHub Pages:** in the repository go to Settings → Pages, set *Source* to "Deploy from a branch", pick the branch and `/ (root)`, and save. The `.nojekyll` file makes Pages serve the files as they are.

Any static host works the same way, for example Cloudflare Pages or Netlify with no build command and the repository root as the output directory.

## Data sources

- Crashes: [Motor Vehicle Collisions – Crashes](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95), NYPD via NYC Open Data.
- Zip boundaries and population: [Modified Zip Code Tabulation Areas (MODZCTA)](https://data.cityofnewyork.us/Health/Modified-Zip-Code-Tabulation-Areas-MODZCTA-/pri4-ifjk), NYC DOHMH.
- Basemap: Esri World Gray Canvas.

Zip areas are computed from the full-resolution boundaries in NY State Plane feet. Per-square-mile density uses each zip's whole area, so zips containing large parks or airports look less dense than their streets are.

Per-resident rates are only shown for zips with at least 5,000 residents. Below that, rates are dominated by commuters and visitors (e.g. the Financial District).

## Notes

- Calls to NYC Open Data are anonymous, which is fine at this traffic level. If the site gets heavy use, register a free [app token](https://dev.socrata.com/docs/app-tokens.html) and add it as an `$$app_token` parameter in `js/api.js`.
- Results are cached in the browser for 6 hours, so repeat visits and filter changes don't re-query the API.
