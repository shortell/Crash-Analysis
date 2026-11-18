// Pure data logic: dates, metrics, per-zip aggregation, ranking and deciles.
import { counts } from './api.js';

/* ---------- dates (all ISO 'YYYY-MM-DD', computed in UTC) ---------- */

const DAY = 86400000;
export const toDate = (iso) => new Date(iso + 'T00:00:00Z');
export const toISO = (d) => d.toISOString().slice(0, 10);
export const addDays = (iso, n) => toISO(new Date(toDate(iso).getTime() + n * DAY));
export const daysBetween = (a, b) => Math.round((toDate(b) - toDate(a)) / DAY) + 1; // inclusive

export const EARLIEST = '2012-07-01'; // first month in the NYPD collisions dataset

export const PRESETS = [
  { id: '30d', label: '30 days', days: 30 },
  { id: '90d', label: '90 days', days: 90 },
  { id: 'ytd', label: 'Year to date' },
  { id: '12m', label: '12 months', days: 365 },
  { id: 'custom', label: 'Custom' },
];

export function resolveRange(state, latest) {
  let { start, end } = state;
  if (state.range === 'custom' && start && end) {
    if (start > end) [start, end] = [end, start];
    if (start < EARLIEST) start = EARLIEST;
    if (end > latest) end = latest;
  } else {
    const preset = PRESETS.find((p) => p.id === state.range) ?? PRESETS[1];
    end = latest;
    start = preset.id === 'ytd' ? latest.slice(0, 4) + '-01-01' : addDays(latest, -((preset.days ?? 90) - 1));
  }
  const len = daysBetween(start, end);
  return { start, end, len, prev: { start: addDays(start, -len), end: addDays(start, -1) } };
}

const fmtDate = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
const fmtShort = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
export const formatDate = (iso) => fmtDate.format(toDate(iso));
export const formatShortDate = (iso) => fmtShort.format(toDate(iso));
export function formatRange({ start, end }) {
  return start.slice(0, 4) === end.slice(0, 4)
    ? `${formatShortDate(start)} – ${formatDate(end)}`
    : `${formatDate(start)} – ${formatDate(end)}`;
}

/* ---------- numbers ---------- */

const nf = new Intl.NumberFormat('en-US');
const nf1 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });
export const fmtInt = (v) => (v == null ? '–' : nf.format(Math.round(v)));
export const fmt1 = (v) => (v == null ? '–' : nf1.format(v));
export const fmtCompact = (v) => (v == null ? '–' : v < 10000 ? nf.format(Math.round(v)) : compact.format(v));
export function fmtPct(v) {
  if (v == null || !Number.isFinite(v)) return '–';
  const pct = v * 100;
  const s = Math.abs(pct) < 10 ? pct.toFixed(1) : Math.round(pct).toString();
  return (pct > 0 ? '+' : '') + s + '%';
}
export const pctChange = (cur, prev) => (prev > 0 ? (cur - prev) / prev : null);

// "prior 90 days" for short periods, "prior 6.9 years" for long ones.
export const priorLabel = (len) => (len <= 366 ? `prior ${len} days` : `prior ${(len / 365.25).toFixed(1)} years`);

/* ---------- metrics ---------- */

export const MIN_BASE_FOR_CHANGE = 5;
export const MIN_POP_FOR_RATE = 5000; // tiny-population zips (e.g. Financial District) make rates meaningless

export const METRICS = [
  { key: 'n', label: 'Crashes', short: 'Crashes' },
  { key: 'inj', label: 'Injuries', short: 'Injuries' },
  { key: 'kil', label: 'Deaths', short: 'Deaths' },
  { key: 'ped', label: 'Pedestrians injured or killed', short: 'Pedestrians' },
  { key: 'cyc', label: 'Cyclists injured or killed', short: 'Cyclists' },
  { key: 'n_pc', label: 'Crashes per 10k residents', short: 'Crashes / 10k', base: 'n', perCapita: true },
  { key: 'inj_pc', label: 'Injuries per 10k residents', short: 'Injuries / 10k', base: 'inj', perCapita: true },
];
export const metricByKey = (key) => METRICS.find((m) => m.key === key) ?? METRICS[0];
export const baseKey = (m) => m.base ?? m.key;

export function rate(count, pop) {
  return pop >= MIN_POP_FOR_RATE ? (count / pop) * 10000 : null;
}

export function metricValue(rec, m) {
  if (m.perCapita) return rate(rec[m.base], rec.pop);
  if (m.perArea) return rec.sqmi > 0 ? rec[m.base] / rec.sqmi : null;
  return rec[m.key];
}

// The per-square-mile version of a metric (per-resident metrics use their underlying count).
export function densityMetric(m) {
  const base = metricByKey(baseKey(m));
  return {
    key: `${base.key}_sqmi`,
    label: `${base.label} per square mile`,
    short: `${base.short} / sq mi`,
    base: base.key,
    perArea: true,
  };
}

export const formatMetric = (v, m) => (m.perCapita ? fmt1(v) : fmtInt(v));

/* ---------- aggregation ---------- */

const ZERO = () => ({ n: 0, inj: 0, kil: 0, ped: 0, cyc: 0 });
const KEYS = ['n', 'inj', 'kil', 'ped', 'cyc'];
function addInto(target, c) {
  for (const k of KEYS) target[k] += c[k];
}
export function sumRows(rows) {
  const total = ZERO();
  for (const r of rows) addInto(total, counts(r));
  return total;
}

// Combine zip-tagged totals with zip-less points placed by polygon lookup.
// `tagged` / `prevTagged` keep the zip-tagged-only numbers so that period-over-period
// change compares like with like.
export function buildZipRecords(geo, zipRows, pointRows, prevZipRows) {
  const records = new Map();
  for (const f of geo.features) {
    const { zip, borough, pop } = f.properties;
    records.set(zip, { zip, borough, pop, sqmi: f.properties.sqmi ?? 0, ...ZERO(), tagged: ZERO(), prevTagged: ZERO(), placed: 0 });
  }
  let unplaced = 0;

  for (const row of zipRows) {
    const c = counts(row);
    const rec = records.get(geo.postalToZip.get(String(row.zip_code).trim()));
    if (!rec) { unplaced += c.n; continue; }
    addInto(rec, c);
    addInto(rec.tagged, c);
  }
  for (const row of prevZipRows ?? []) {
    const rec = records.get(geo.postalToZip.get(String(row.zip_code).trim()));
    if (rec) addInto(rec.prevTagged, counts(row));
  }
  for (const row of pointRows ?? []) {
    const c = counts(row);
    const rec = records.get(geo.locate(Number(row.latitude), Number(row.longitude)));
    if (!rec) { unplaced += c.n; continue; }
    addInto(rec, c);
    rec.placed += c.n;
  }
  return { records, unplaced };
}

/* ---------- ranking ---------- */

// Equivalent to pandas `qcut(rank, 10, labels=False) + 1` used by the original app:
// decile 1 holds the highest-ranked (worst) zips.
export function decileOf(rank, n) {
  if (n <= 1) return 1;
  for (let i = 1; i <= 10; i++) {
    if (rank <= 1 + ((n - 1) * i) / 10 + 1e-9) return i;
  }
  return 10;
}

export function rankRecords(records, metric, borough = null) {
  const rows = [];
  for (const rec of records.values()) {
    if (borough && rec.borough !== borough) continue;
    const value = metricValue(rec, metric);
    if (value == null) continue;
    rows.push({ rec, value });
  }
  rows.sort((a, b) => b.value - a.value || a.rec.zip.localeCompare(b.rec.zip));
  const total = rows.reduce((s, r) => s + r.value, 0);
  const avg = rows.length ? total / rows.length : 0;
  const k = baseKey(metric);
  rows.forEach((r, i) => {
    r.rank = i + 1;
    r.decile = decileOf(r.rank, rows.length);
    r.vsAvg = avg > 0 ? r.value / avg : null;
    r.share = !metric.perCapita && !metric.perArea && total > 0 ? r.value / total : null;
    // Percent change on tiny counts (1 -> 6 deaths = +500%) is noise, so require a base of 5.
    r.change = r.rec.prevTagged[k] >= MIN_BASE_FOR_CHANGE ? pctChange(r.rec.tagged[k], r.rec.prevTagged[k]) : null;
  });
  return { rows, avg, total, byZip: new Map(rows.map((r) => [r.rec.zip, r])) };
}

/* ---------- time series ---------- */

// Calendar buckets for the trend chart. Each option is offered only when the period
// is long enough for it to be useful (and short enough not to drown in points).
export const GRANULARITIES = [
  { id: 'daily', label: 'Daily', allowed: (len) => len <= 366 },
  { id: 'weekly', label: 'Weekly', allowed: (len) => len >= 14 && len <= 1100 },
  { id: 'monthly', label: 'Monthly', allowed: (len) => len >= 60 },
  { id: 'yearly', label: 'Yearly', allowed: (len) => len >= 730 },
];

export function defaultGranularity(len) {
  return len <= 45 ? 'daily' : len <= 400 ? 'weekly' : 'monthly';
}

// The requested granularity if the period allows it, otherwise the default.
export function resolveGranularity(requested, len) {
  const g = GRANULARITIES.find((x) => x.id === requested);
  return g && g.allowed(len) ? g.id : defaultGranularity(len);
}

// Start and end (inclusive) of the calendar period containing `iso`.
function periodOf(iso, gran) {
  if (gran === 'daily') return [iso, iso];
  if (gran === 'weekly') {
    const monday = addDays(iso, -((toDate(iso).getUTCDay() + 6) % 7));
    return [monday, addDays(monday, 6)];
  }
  if (gran === 'monthly') {
    const start = iso.slice(0, 7) + '-01';
    const d = toDate(start);
    const next = toISO(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1)));
    return [start, addDays(next, -1)];
  }
  return [iso.slice(0, 4) + '-01-01', iso.slice(0, 4) + '-12-31'];
}

// Sum daily rows into calendar buckets. Buckets cut off by the range ends are clipped
// to the range and flagged `partial`, with the number of days they cover.
export function trendSeries(dailyRows, range, key, gran) {
  const byDay = new Map(dailyRows.map((r) => [r.d.slice(0, 10), counts(r)[key]]));
  const points = [];
  let day = range.start;
  while (day <= range.end) {
    const [pStart, pEnd] = periodOf(day, gran);
    const to = pEnd < range.end ? pEnd : range.end;
    let value = 0;
    for (let d = day; d <= to; d = addDays(d, 1)) value += byDay.get(d) ?? 0;
    const days = daysBetween(day, to);
    const periodDays = daysBetween(pStart, pEnd);
    points.push({ from: day, to, value, days, periodDays, partial: days < periodDays });
    day = addDays(to, 1);
  }
  return { gran, points };
}

export function sumBetween(dailyRows, range) {
  return sumRows(dailyRows.filter((r) => {
    const d = r.d.slice(0, 10);
    return d >= range.start && d <= range.end;
  }));
}

/* ---------- category cleanup ---------- */

const VEHICLE_ALIASES = [
  [/^(4 DR SEDAN|2 DR SEDAN|SEDAN|3-DOOR)$/, 'Sedan'],
  [/STATION WAGON|SPORT UTILITY|^SUV/, 'SUV / station wagon'],
  [/^TAXI|^CAB$|YELLOW CAB|LIVERY/, 'Taxi / livery'],
  [/^PICK-?UP/, 'Pickup truck'],
  [/^(BOX TRUCK|BOX T)/, 'Box truck'],
  [/^BUS|OMNIBUS|SCHOOL BUS/, 'Bus'],
  [/^E-?BIKE|^E-BIK|MOPED|^SCOOTER|E-SCOOTER|^MINIBIKE/, 'E-bike / moped / scooter'],
  [/^BIKE$|^BICYCLE|^BICYCLIST/, 'Bicycle'],
  [/^MOTORCYCLE|^MOTORBIKE/, 'Motorcycle'],
  [/^VAN$|^PASSENGER VAN/, 'Van'],
  [/TRACTOR TRUCK|SEMI/, 'Tractor-trailer'],
  [/AMBULANCE|FIRE TRUCK|FDNY|POLICE/, 'Emergency vehicle'],
];

export function normalizeVehicles(rows, limit = 10) {
  const merged = new Map();
  for (const r of rows) {
    const raw = (r.label || '').trim();
    if (!raw || raw === 'UNKNOWN' || raw === 'UNK') continue;
    const name = VEHICLE_ALIASES.find(([re]) => re.test(raw))?.[1]
      ?? raw.charAt(0) + raw.slice(1).toLowerCase();
    merged.set(name, (merged.get(name) ?? 0) + (Number(r.n) || 0));
  }
  return [...merged].map(([label, n]) => ({ label, n })).sort((a, b) => b.n - a.n).slice(0, limit);
}

export function titleCase(s) {
  return String(s || '').toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase());
}
