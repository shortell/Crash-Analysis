// Zip-code polygons: loading, postal-zip lookup, and point-in-polygon placement.

export const BOROUGHS = [
  { id: 'BRONX', slug: 'bronx', name: 'The Bronx', short: 'Bronx' },
  { id: 'BROOKLYN', slug: 'brooklyn', name: 'Brooklyn', short: 'Brooklyn' },
  { id: 'MANHATTAN', slug: 'manhattan', name: 'Manhattan', short: 'Manhattan' },
  { id: 'QUEENS', slug: 'queens', name: 'Queens', short: 'Queens' },
  { id: 'STATEN ISLAND', slug: 'staten-island', name: 'Staten Island', short: 'Staten Is.' },
];

export const boroughName = (id) => BOROUGHS.find((b) => b.id === id)?.name ?? id;

function bbox(geometry) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const polys = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  for (const poly of polys) {
    for (const ring of poly) {
      for (const [x, y] of ring) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  return [minX, minY, maxX, maxY];
}

// Even-odd ray casting over every ring, so holes are handled for free.
export function pointInGeometry(x, y, geometry) {
  const polys = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  let inside = false;
  for (const poly of polys) {
    for (const ring of poly) {
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i];
        const [xj, yj] = ring[j];
        if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
          inside = !inside;
        }
      }
    }
  }
  return inside;
}

export function indexZips(geojson) {
  const features = geojson.features.map((f) => ({ ...f, bbox: bbox(f.geometry) }));
  const byZip = new Map(features.map((f) => [f.properties.zip, f]));
  const postalToZip = new Map();
  for (const f of features) {
    for (const z of f.properties.zips) postalToZip.set(z, f.properties.zip);
  }

  function locate(lat, lon) {
    for (const f of features) {
      const [minX, minY, maxX, maxY] = f.bbox;
      if (lon < minX || lon > maxX || lat < minY || lat > maxY) continue;
      if (pointInGeometry(lon, lat, f.geometry)) return f.properties.zip;
    }
    return null;
  }

  const zipsIn = (borough) =>
    features.filter((f) => f.properties.borough === borough).flatMap((f) => f.properties.zips);

  return { geojson: { ...geojson, features }, features, byZip, postalToZip, locate, zipsIn };
}

export async function loadZips(url = 'data/nyc_zips.geojson') {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Could not load zip boundaries (HTTP ${res.status})`);
  return indexZips(await res.json());
}
