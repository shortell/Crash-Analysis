// NYC Open Data (Socrata) client: builds SoQL queries, dedupes in-flight requests,
// and caches results in localStorage so repeat visits don't re-query the API.

const BASE = 'https://data.cityofnewyork.us/resource/h9gi-nx95.json';
const CACHE_PREFIX = 'nyc-crash:v1:';
const HOUR = 3600 * 1000;
const memory = new Map();

const SUMS = [
  'count(*) as n',
  'sum(number_of_persons_injured) as inj',
  'sum(number_of_persons_killed) as kil',
  'sum(number_of_pedestrians_injured) as pi',
  'sum(number_of_pedestrians_killed) as pk',
  'sum(number_of_cyclist_injured) as ci',
  'sum(number_of_cyclist_killed) as ck',
].join(', ');

// Pull the severity sums out of a grouped row into plain numbers.
export function counts(row) {
  const num = (k) => Number(row[k]) || 0;
  return {
    n: num('n'),
    inj: num('inj'),
    kil: num('kil'),
    ped: num('pi') + num('pk'),
    cyc: num('ci') + num('ck'),
  };
}

function cacheGet(key) {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + key);
    if (!raw) return null;
    const { t, ttl, rows } = JSON.parse(raw);
    return Date.now() - t < ttl ? rows : null;
  } catch {
    return null;
  }
}

function cacheSet(key, rows, ttl) {
  const value = JSON.stringify({ t: Date.now(), ttl, rows });
  try {
    localStorage.setItem(CACHE_PREFIX + key, value);
  } catch {
    // Quota hit: drop our old entries and try once more; if it still fails, skip caching.
    try {
      Object.keys(localStorage)
        .filter((k) => k.startsWith(CACHE_PREFIX))
        .forEach((k) => localStorage.removeItem(k));
      localStorage.setItem(CACHE_PREFIX + key, value);
    } catch { /* caching is best-effort */ }
  }
}

export function soql(params, ttl = 6 * HOUR) {
  const key = new URLSearchParams(params).toString();
  if (memory.has(key)) return memory.get(key);

  const hit = cacheGet(key);
  if (hit) {
    const p = Promise.resolve(hit);
    memory.set(key, p);
    return p;
  }

  const p = fetch(`${BASE}?${key}`)
    .then((res) => {
      if (!res.ok) throw new Error(`NYC Open Data returned HTTP ${res.status}`);
      return res.json();
    })
    .then((rows) => {
      cacheSet(key, rows, ttl);
      return rows;
    })
    .catch((err) => {
      memory.delete(key); // allow a retry
      throw err;
    });
  memory.set(key, p);
  return p;
}

const q = (s) => `'${String(s).replace(/'/g, "''")}'`;

function dateWhere({ start, end }) {
  return `crash_date between ${q(start + 'T00:00:00')} and ${q(end + 'T23:59:59')}`;
}

// scope: { borough, zips } -> extra SoQL filter for KPIs and charts.
// A borough matches crashes tagged with that borough OR with one of its zips,
// because about a third of records leave the borough blank.
export function scopeWhere(scope) {
  if (!scope) return '';
  const zipList = scope.zips?.length ? `zip_code in (${scope.zips.map(q).join(',')})` : '';
  if (scope.borough) {
    const b = `borough = ${q(scope.borough)}`;
    return zipList ? `(${b} or ${zipList})` : b;
  }
  return zipList;
}

function where(range, scope, ...extra) {
  return [dateWhere(range), scopeWhere(scope), ...extra].filter(Boolean).join(' and ');
}

export async function latestDate() {
  const rows = await soql({ $select: 'max(crash_date) as d' }, HOUR);
  return rows[0].d.slice(0, 10);
}

// Per-zip totals for crashes that have a zip code.
export function zipTotals(range) {
  return soql({
    $select: `zip_code, ${SUMS}`,
    $where: where(range, null, 'zip_code is not null'),
    $group: 'zip_code',
    $limit: 5000,
  });
}

// Crashes with no zip but with coordinates, grouped by location.
// These are placed into zips client-side with a point-in-polygon lookup.
export async function unzippedPoints(range) {
  const pageSize = 50000;
  const all = [];
  for (let offset = 0; offset < 20 * pageSize; offset += pageSize) {
    const rows = await soql({
      $select: `latitude, longitude, ${SUMS}`,
      $where: where(range, null, 'zip_code is null',
        'latitude between 40.45 and 40.95', 'longitude between -74.30 and -73.65'),
      $group: 'latitude, longitude',
      $order: 'latitude, longitude',
      $limit: pageSize,
      $offset: offset,
    });
    all.push(...rows);
    if (rows.length < pageSize) break;
  }
  return all;
}

// Crashes with neither zip nor usable coordinates (shown as a footnote).
export function unlocatedTotal(range) {
  return soql({
    $select: 'count(*) as n',
    $where: where(range, null, 'zip_code is null',
      '(latitude is null or latitude not between 40.45 and 40.95 or longitude not between -74.30 and -73.65)'),
  }).then((rows) => Number(rows[0]?.n) || 0);
}

export function daily(range, scope) {
  return soql({
    $select: `crash_date as d, ${SUMS}`,
    $where: where(range, scope),
    $group: 'd',
    $order: 'd',
    $limit: 50000,
  });
}

export function hourGrid(range, scope) {
  return soql({
    $select: 'date_extract_dow(crash_date) as dow, substring(crash_time, 1, 2) as hh, count(*) as n',
    $where: where(range, scope),
    $group: 'dow, hh',
    $limit: 1000,
  });
}

export function factors(range, scope) {
  return soql({
    $select: `contributing_factor_vehicle_1 as label, ${SUMS}`,
    $where: where(range, scope, 'contributing_factor_vehicle_1 is not null',
      "contributing_factor_vehicle_1 not in ('Unspecified', 'Does Not Apply')"),
    $group: 'label',
    $order: 'n DESC',
    $limit: 12,
  });
}

export function vehicles(range, scope) {
  return soql({
    $select: 'upper(vehicle_type_code1) as label, count(*) as n',
    $where: where(range, scope, 'vehicle_type_code1 is not null'),
    $group: 'label',
    $order: 'n DESC',
    $limit: 40,
  });
}

export function intersections(range, scope) {
  return soql({
    $select: `upper(on_street_name) as a, upper(cross_street_name) as b, ${SUMS}`,
    $where: where(range, scope, 'on_street_name is not null', 'cross_street_name is not null'),
    $group: 'a, b',
    $order: 'n DESC',
    $limit: 8,
  });
}
