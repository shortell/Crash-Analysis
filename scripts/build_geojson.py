"""One-off build step: convert the MODZCTA shapefile into the compact GeoJSON the site loads.

Not needed at runtime. Re-run only if the zip boundaries change:

    pip install geopandas requests
    python scripts/build_geojson.py path/to/nyc_zip_code_map.shp

The shapefile is NYC DOHMH's MODZCTA boundaries (NYC Open Data). The copy this
project used lives in git history: `git checkout 7c1843e -- data/nyc_shapefile`.

Each feature keeps:
  zip      MODZCTA code (the polygon id used everywhere in the app)
  zips     every postal zip that maps to it (crash records use postal zips)
  pop      population estimate (for per-capita rates)
  borough  majority borough of all crashes ever recorded with that zip
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import requests

API = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
OUT = Path(__file__).resolve().parent.parent / "data" / "nyc_zips.geojson"
TOLERANCE = 0.00012  # degrees, about 12 m
BOROUGHS = {"MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"}


def prefix_borough(zip_code):
    p = zip_code[:3]
    if p in ("100", "101", "102"):
        return "MANHATTAN"
    if p == "103":
        return "STATEN ISLAND"
    if p == "104":
        return "BRONX"
    if p == "112":
        return "BROOKLYN"
    return "QUEENS"


def zip_borough_counts():
    rows = requests.get(API, params={
        "$select": "zip_code, borough, count(*) as n",
        "$where": "zip_code is not null and borough is not null",
        "$group": "zip_code, borough",
        "$limit": 50000,
    }, timeout=300).json()
    counts = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r.get("borough") in BOROUGHS:
            counts[r["zip_code"].strip()][r["borough"]] += int(r["n"])
    return counts


def split_zips(*values):
    out = []
    for v in values:
        for z in (v or "").split(","):
            z = z.strip()
            if z and z not in out:
                out.append(z)
    return out


def main(shp):
    gdf = gpd.read_file(shp).to_crs(4326)
    gdf = gdf[gdf["modzcta"] != "99999"]  # placeholder polygon with no population
    gdf["geometry"] = gdf.geometry.simplify(TOLERANCE, preserve_topology=True)
    counts = zip_borough_counts()

    features = []
    for _, row in gdf.iterrows():
        zips = split_zips(row["modzcta"], row["zcta"], row["label"])
        tally = defaultdict(int)
        for z in zips:
            for b, n in counts.get(z, {}).items():
                tally[b] += n
        borough = max(tally, key=tally.get) if tally else prefix_borough(row["modzcta"])
        geom = json.loads(gpd.GeoSeries([row.geometry]).to_json())["features"][0]["geometry"]
        features.append({
            "type": "Feature",
            "properties": {
                "zip": row["modzcta"],
                "zips": zips,
                "pop": int(row["pop_est"] or 0),
                "borough": borough,
            },
            "geometry": geom,
        })

    text = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
    # round coordinates to 5 decimals (~1 m) to shrink the file
    import re
    text = re.sub(r"-?\d+\.\d{6,}", lambda m: f"{float(m.group()):.5f}".rstrip("0"), text)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {len(features)} zips, {OUT.stat().st_size / 1024:.0f} KB -> {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
