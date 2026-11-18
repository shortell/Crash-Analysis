// Dashboard controller: URL state, data loading, and rendering.
import * as api from './api.js';
import { loadZips, BOROUGHS, boroughName } from './geo.js';
import {
  PRESETS, EARLIEST, METRICS, metricByKey, baseKey, formatMetric, rate,
  resolveRange, formatRange, formatDate, fmtInt, fmt1, fmtPct, pctChange,
  buildZipRecords, rankRecords, densityMetric, trendSeries, sumBetween, normalizeVehicles, titleCase,
} from './stats.js';
import { createMap } from './map.js';
import { css, trendChart, barChart, hourGrid } from './charts.js';

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

/* ---------- state (mirrored in the URL) ---------- */

const DEFAULTS = { range: '90d', start: '', end: '', area: 'all', metric: 'n', zip: '' };
let state = readURL();
let sort = { key: 'rank', dir: 'asc' };

function readURL() {
  const p = new URLSearchParams(location.search);
  const s = { ...DEFAULTS };
  for (const k of Object.keys(DEFAULTS)) if (p.get(k)) s[k] = p.get(k);
  if (!PRESETS.some((x) => x.id === s.range)) s.range = DEFAULTS.range;
  if (s.area !== 'all' && !BOROUGHS.some((b) => b.slug === s.area)) s.area = 'all';
  s.metric = metricByKey(s.metric).key;
  return s;
}

function writeURL(push) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(state)) {
    if (!v || v === DEFAULTS[k]) continue;
    if ((k === 'start' || k === 'end') && state.range !== 'custom') continue;
    p.set(k, v);
  }
  const url = `${location.pathname}${p.toString() ? '?' + p : ''}`;
  history[push ? 'pushState' : 'replaceState'](null, '', url);
}

function setState(patch, { push = true } = {}) {
  const before = state;
  state = { ...state, ...patch };
  writeURL(push);
  const changed = Object.keys(state).filter((k) => state[k] !== before[k]);
  if (changed.length === 1 && changed[0] === 'zip' && current.ranking) {
    // Selecting a zip doesn't change any other view: just update the selection.
    for (const tr of document.querySelectorAll('#zip-table tr[data-zip]')) {
      tr.classList.toggle('is-selected', tr.dataset.zip === state.zip);
    }
    renderDrawer();
    return;
  }
  render();
}

window.addEventListener('popstate', () => {
  state = readURL();
  render();
});

/* ---------- app data ---------- */

let geo;
let latest;
let zipMap;
let densityMap;
const eachMap = (fn) => [zipMap, densityMap].forEach((m) => m && fn(m));
let renderToken = 0;
const recordCache = new Map(); // range key -> { records, unplaced, complete }
let current = { ranking: null, records: null, range: null, borough: null, metric: null };
let lastFit = null;

const boroughId = () => BOROUGHS.find((b) => b.slug === state.area)?.id ?? null;
const scopeFor = (borough) => (borough ? { borough, zips: geo.zipsIn(borough) } : null);
const areaName = (borough) => (borough ? boroughName(borough) : 'NYC');

async function init() {
  buildStaticControls();
  try {
    [geo, latest] = await Promise.all([loadZips(), api.latestDate()]);
  } catch (err) {
    showBanner(`Couldn't reach NYC Open Data (${err.message}).`, init);
    return;
  }
  hideBanner();
  $('data-through').textContent = `Live NYPD collision data · updated through ${formatDate(latest)}`;
  $('custom-start').min = $('custom-end').min = EARLIEST;
  $('custom-start').max = $('custom-end').max = latest;
  $('zip-options').innerHTML = [...geo.postalToZip.keys()].sort().map((z) => `<option value="${z}">`).join('');

  const handlers = {
    onHover: (zip, on) => {
      if (!inScope(zip)) return;
      eachMap((m) => m.highlight(zip, on));
      document.querySelector(`#zip-table tr[data-zip="${zip}"]`)?.classList.toggle('is-hover', on);
    },
    onSelect: (zip) => inScope(zip) && setState({ zip }),
  };
  zipMap = createMap($('map'), geo, handlers);
  densityMap = createMap($('density-map'), geo, handlers);
  linkViews(zipMap.map, densityMap.map);
  render();
}

// Keep the two maps' pan and zoom in step. The flag stops them re-triggering each other.
function linkViews(a, b) {
  let syncing = false;
  const follow = (src, dst) => src.on('move', () => {
    if (syncing) return;
    syncing = true;
    dst.setView(src.getCenter(), src.getZoom(), { animate: false });
    syncing = false;
  });
  follow(a, b);
  follow(b, a);
}

const inScope = (zip) => {
  const b = boroughId();
  return !b || geo.byZip.get(zip)?.properties.borough === b;
};

/* ---------- controls ---------- */

function buildStaticControls() {
  $('range-control').innerHTML = PRESETS.map((p) => `<button type="button" role="radio" data-range="${p.id}">${p.label}</button>`).join('');
  $('borough-control').innerHTML = [{ slug: 'all', short: 'All NYC' }, ...BOROUGHS]
    .map((b) => `<button type="button" role="radio" data-area="${b.slug}">${b.short}</button>`).join('');
  $('metric-select').innerHTML = METRICS.map((m) => `<option value="${m.key}">${m.label}</option>`).join('');

  $('range-control').addEventListener('click', (e) => {
    const id = e.target.closest('button')?.dataset.range;
    if (!id) return;
    if (id === 'custom') {
      const r = current.range ?? resolveRange(state, latest);
      setState({ range: 'custom', start: state.start || r.start, end: state.end || r.end });
    } else setState({ range: id, start: '', end: '' });
  });
  for (const id of ['custom-start', 'custom-end']) {
    $(id).addEventListener('change', () => {
      const start = $('custom-start').value;
      const end = $('custom-end').value;
      if (start && end) setState({ range: 'custom', start, end });
    });
  }
  $('borough-control').addEventListener('click', (e) => {
    const area = e.target.closest('button')?.dataset.area;
    if (area && area !== state.area) {
      const zip = state.zip && area !== 'all' && geo.byZip.get(state.zip)?.properties.borough !== BOROUGHS.find((b) => b.slug === area)?.id ? '' : state.zip;
      setState({ area, zip });
    }
  });
  $('metric-select').addEventListener('change', (e) => {
    sort = { key: 'rank', dir: 'asc' };
    setState({ metric: e.target.value });
  });
  $('search-form').addEventListener('submit', (e) => {
    e.preventDefault();
    searchZip($('zip-search').value.trim(), true);
  });
  $('zip-search').addEventListener('input', (e) => {
    $('search-error').textContent = '';
    const v = e.target.value.trim();
    if (v.length === 5 && geo?.postalToZip.has(v)) searchZip(v, false);
  });
  $('drawer-close').addEventListener('click', closeDrawer);
  $('scrim').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && state.zip) closeDrawer();
  });
  $('export-csv').addEventListener('click', exportCSV);
  setupTheme();
  setupTooltips();
}

function searchZip(value, showError) {
  if (!geo) return;
  const zip = geo.postalToZip.get(value);
  if (!zip) {
    if (showError) $('search-error').textContent = value ? `${value} isn't a NYC zip code` : '';
    return;
  }
  $('search-error').textContent = '';
  const b = geo.byZip.get(zip).properties.borough;
  setState({ zip, area: state.area === 'all' || boroughId() === b ? state.area : 'all' });
  $('zip-search').blur();
}

function closeDrawer() {
  setState({ zip: '' });
}

function syncControls(range) {
  for (const b of $('range-control').children) b.setAttribute('aria-checked', String(b.dataset.range === state.range));
  for (const b of $('borough-control').children) b.setAttribute('aria-checked', String(b.dataset.area === state.area));
  $('metric-select').value = state.metric;
  $('custom-range').hidden = state.range !== 'custom';
  $('custom-start').value = range.start;
  $('custom-end').value = range.end;
}

/* ---------- theme ---------- */

const THEMES = ['system', 'light', 'dark'];
const themeNow = () => {
  const t = document.documentElement.dataset.theme;
  return t === 'light' || t === 'dark' ? t : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

function setupTheme() {
  let pref = document.documentElement.dataset.theme || 'system';
  const label = () => {
    $('theme-label').textContent = pref[0].toUpperCase() + pref.slice(1);
    $('theme-toggle').setAttribute('aria-label', `Theme: ${pref}. Click to change.`);
  };
  label();
  $('theme-toggle').addEventListener('click', () => {
    pref = THEMES[(THEMES.indexOf(pref) + 1) % THEMES.length];
    if (pref === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = pref;
    try { localStorage.setItem('nyc-crash:theme', pref); } catch { /* ignore */ }
    label();
    if (geo) render();
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => geo && render());
}

function colors() {
  const ramp = css('--seq-ramp').split(',').map((s) => s.trim());
  return {
    ramp: ramp.slice().reverse(), // decile 1 = highest
    empty: css('--empty'),
    outline: css('--map-outline'),
    highlight: css('--map-highlight'),
  };
}

/* ---------- tooltips for HTML charts ---------- */

function setupTooltips() {
  const tip = $('tip');
  document.addEventListener('pointerover', (e) => {
    const t = e.target.closest('[data-tip]');
    if (!t) return;
    tip.textContent = t.dataset.tip;
    tip.hidden = false;
  });
  document.addEventListener('pointermove', (e) => {
    if (tip.hidden) return;
    if (!e.target.closest('[data-tip]')) { tip.hidden = true; return; }
    const w = tip.offsetWidth;
    const x = Math.min(window.innerWidth - w - 8, Math.max(8, e.clientX - w / 2));
    tip.style.left = `${x}px`;
    tip.style.top = `${e.clientY - tip.offsetHeight - 12}px`;
  });
  document.addEventListener('pointerout', (e) => {
    if (e.target.closest('[data-tip]') && !e.relatedTarget?.closest?.('[data-tip]')) tip.hidden = true;
  });
}

/* ---------- banner / loading ---------- */

function showBanner(message, retry) {
  const el = $('banner');
  el.innerHTML = `<span>${esc(message)}</span>${retry ? '<button class="btn" type="button">Retry</button>' : ''}`;
  el.hidden = false;
  el.querySelector('button')?.addEventListener('click', () => { hideBanner(); retry(); });
}
const hideBanner = () => { $('banner').hidden = true; };

function loading(card, on) {
  card.classList.toggle('is-loading', on);
  if (on) card.classList.remove('has-error');
}
function failed(card, err) {
  card.classList.remove('is-loading');
  card.classList.add('has-error');
  card.dataset.error = `Couldn't load this from NYC Open Data. ${err.message}`;
  showBanner('Some data failed to load from NYC Open Data. It may be busy; try again in a moment.', render);
}
const cardOf = (id) => $(id).closest('.card');

/* ---------- render ---------- */

function render() {
  if (!geo) return;
  const token = ++renderToken;
  const live = () => token === renderToken;
  const range = resolveRange(state, latest);
  const borough = boroughId();
  const metric = metricByKey(state.metric);
  const scope = scopeFor(borough);
  const span = { start: range.prev.start, end: range.end };

  syncControls(range);
  hideBanner();
  document.title = `${areaName(borough)} crashes · ${formatRange(range)}`;

  // KPIs + trend: one daily query covering the current and prior period.
  const pDaily = api.daily(span, scope);
  renderKPIs(pDaily, range, borough, live);
  renderTrend(pDaily, range, borough, metric, live);

  renderHours(api.hourGrid(range, scope), live);
  renderBars('factor-chart', api.factors(range, scope).then((rows) =>
    rows.map((r) => ({ label: r.label, n: Number(r.n) || 0 })).slice(0, 10)), live);
  renderBars('vehicle-chart', api.vehicles(range, scope).then((rows) => normalizeVehicles(rows)), live);

  renderZips(range, borough, metric, live);
}

function renderKPIs(pDaily, range, borough, live) {
  const tiles = [
    { key: 'n', label: 'Crashes' },
    { key: 'inj', label: 'People injured' },
    { key: 'kil', label: 'People killed' },
    { key: 'ped', label: 'Pedestrians hurt', title: 'Pedestrians injured or killed' },
    { key: 'cyc', label: 'Cyclists hurt', title: 'Cyclists injured or killed' },
  ];
  const el = $('kpis');
  el.innerHTML = tiles.map((t) => `
    <div class="card kpi">
      <div class="kpi-label">${t.label}</div>
      <div class="kpi-value"><span class="skeleton" style="width:60%">0</span></div>
      <div class="kpi-delta"><span class="skeleton" style="width:80%">.</span></div>
    </div>`).join('');

  pDaily.then((rows) => {
    if (!live()) return;
    const cur = sumBetween(rows, range);
    const prev = sumBetween(rows, range.prev);
    el.innerHTML = tiles.map((t) => {
      const ch = pctChange(cur[t.key], prev[t.key]);
      const cls = ch == null || Math.abs(ch) < 0.005 ? '' : ch > 0 ? 'delta-up' : 'delta-down';
      const arrow = cls === 'delta-up' ? '▲ ' : cls === 'delta-down' ? '▼ ' : '';
      const perDay = cur[t.key] / range.len;
      return `
        <div class="card kpi" title="${esc(t.title ?? t.label)} in ${esc(areaName(borough))}, ${esc(formatRange(range))}">
          <div class="kpi-label">${t.label}</div>
          <div class="kpi-value">${fmtInt(cur[t.key])}</div>
          <div class="kpi-delta"><span class="${cls}">${arrow}${fmtPct(ch)}</span> vs prior ${range.len} days
            <span class="hide-sm">· ${perDay >= 10 ? fmtInt(perDay) : fmt1(perDay)}/day</span></div>
        </div>`;
    }).join('');
  }).catch((err) => {
    if (!live()) return;
    el.innerHTML = '';
    showBanner(`Couldn't load totals from NYC Open Data (${err.message}). It may be busy; try again in a moment.`, render);
  });
}

function renderTrend(pDaily, range, borough, metric, live) {
  const card = cardOf('trend-chart');
  const key = baseKey(metric);
  const label = metricByKey(key).label;
  $('trend-title').textContent = `${label} over time`;
  loading(card, true);
  pDaily.then((rows) => {
    if (!live()) return;
    loading(card, false);
    const series = trendSeries(rows, range, key);
    $('trend-sub').textContent = `${areaName(borough)} · ${trendSummary(rows, range, key, series.mode, label)}`;
    trendChart($('trend-chart'), { series, unitLabel: label.toLowerCase() });
  }).catch((err) => live() && failed(card, err));
}

// "7-day average · 236 a day, +0.1% vs the prior 90 days"
function trendSummary(rows, range, key, mode, label) {
  const cur = sumBetween(rows, range)[key];
  const prev = sumBetween(rows, range.prev)[key];
  const perDay = cur / range.len;
  const rate = perDay >= 10 ? fmtInt(perDay) : fmt1(perDay);
  const how = mode === 'avg7' ? '7-day average' : `${mode} totals`;
  const change = pctChange(cur, prev);
  return `${how} · ${rate} ${label.toLowerCase()} a day`
    + (change == null ? '' : `, ${fmtPct(change)} vs the prior ${range.len} days`);
}

function renderHours(promise, live) {
  const card = cardOf('hour-grid');
  loading(card, true);
  promise.then((rows) => {
    if (!live()) return;
    loading(card, false);
    const peak = hourGrid($('hour-grid'), rows);
    $('hours-sub').textContent = peak ? `Crashes by hour and weekday · busiest: ${peak}` : 'No crashes in this period';
  }).catch((err) => live() && failed(card, err));
}

function renderBars(id, promise, live) {
  const card = cardOf(id);
  loading(card, true);
  promise.then((rows) => {
    if (!live()) return;
    loading(card, false);
    barChart($(id), rows);
  }).catch((err) => live() && failed(card, err));
}

/* ---------- zip map + table ---------- */

async function renderZips(range, borough, metric, live) {
  const key = `${range.start}|${range.end}`;
  const mapCard = cardOf('map');
  const tableCard = cardOf('zip-table');
  const cached = recordCache.get(key);

  if (cached) {
    drawZips(cached, range, borough, metric);
    if (cached.complete) return;
  } else {
    loading(mapCard, true);
    loading(tableCard, true);
    $('zip-status').textContent = '';
  }

  const pPoints = api.unzippedPoints(range);
  const pUnlocated = api.unlocatedTotal(range).catch(() => null);
  let tagged, prevTagged;
  try {
    [tagged, prevTagged] = await Promise.all([api.zipTotals(range), api.zipTotals(range.prev)]);
  } catch (err) {
    if (live()) { failed(mapCard, err); failed(tableCard, err); }
    return;
  }
  if (!live()) return;

  if (!cached) {
    const partial = { ...buildZipRecords(geo, tagged, null, prevTagged), complete: false };
    recordCache.set(key, partial);
    loading(mapCard, false);
    loading(tableCard, false);
    drawZips(partial, range, borough, metric);
  }
  $('zip-status').innerHTML = '<span class="spinner"></span>Placing crashes that have no zip code onto the map…';

  try {
    const [points, unlocated] = await Promise.all([pPoints, pUnlocated]);
    const built = { ...buildZipRecords(geo, tagged, points, prevTagged), complete: true, unlocated };
    recordCache.set(key, built);
    if (live()) drawZips(built, range, borough, metric);
  } catch (err) {
    if (live()) $('zip-status').textContent = `Showing only crashes recorded with a zip code (couldn't load the rest: ${err.message}).`;
  }
}

function drawZips(data, range, borough, metric) {
  const ranking = rankRecords(data.records, metric, borough);
  current = { ranking, records: data.records, range, borough, metric, data };

  const where = borough ? boroughName(borough) : 'NYC';
  $('map-title').textContent = `${metric.label} by zip code`;
  $('map-sub').textContent = `${where} · ${formatRange(range)} · shaded by decile`;

  const c = colors();
  $('legend').innerHTML = `<span>Top 10%</span><div class="legend-ramp">${c.ramp.map((col) => `<i style="background:${col}"></i>`).join('')}</div><span>Bottom 10%</span>`
    + (metric.perCapita ? `<span style="margin-left:auto"><i class="decile-chip" style="background:${c.empty}"></i>Too few residents</span>` : '');

  const inArea = (f) => !borough || f.properties.borough === borough;
  zipMap.setTheme(themeNow());
  zipMap.update({ ranking, inScope: inArea, colors: c, tooltip: (zip) => zipTooltip(zip, metric, current.ranking) });

  // Density map: the same count divided by each zip's area.
  const dMetric = densityMetric(metric);
  const dRanking = rankRecords(data.records, dMetric, borough);
  current.densityRanking = dRanking;
  $('density-title').textContent = `${dMetric.label} by zip code`;
  $('density-sub').textContent = `${where} · ${formatRange(range)} · adjusts for zip size, since bigger zips naturally see more ${metricByKey(dMetric.base).short.toLowerCase()}`;
  $('density-legend').innerHTML = `<span>Top 10%</span><div class="legend-ramp">${c.ramp.map((col) => `<i style="background:${col}"></i>`).join('')}</div><span>Bottom 10%</span>`;
  densityMap.setTheme(themeNow());
  densityMap.update({ ranking: dRanking, inScope: inArea, colors: c, tooltip: (zip) => zipTooltip(zip, dMetric, current.densityRanking) });
  renderDensityInsight(dRanking, dMetric, ranking, borough);
  const fitKey = borough ?? 'all';
  if (lastFit !== fitKey) {
    zipMap.fit(geo.features.filter((f) => !borough || f.properties.borough === borough));
    lastFit = fitKey;
  }

  if (data.complete) {
    const placed = [...data.records.values()].reduce((s, r) => s + r.placed, 0);
    const missing = (data.unplaced || 0) + (data.unlocated || 0);
    $('zip-status').textContent = `Citywide, ${fmtInt(placed)} crashes without a zip code were placed by location.`
      + (missing ? ` ${fmtInt(missing)} couldn't be located and are left out of the zip ranking.` : '');
  }

  renderTable(ranking, borough, metric, c);
  renderInsight(ranking, metric, borough);
  $('export-csv').disabled = !ranking.rows.length;
  renderDrawer();
}

function zipTooltip(zip, metric, ranking) {
  const r = ranking?.byZip.get(zip);
  const rec = current.records?.get(zip);
  if (!rec) return zip;
  const name = `<div class="tip-title">${zip} · ${esc(boroughName(rec.borough))}</div>`;
  if (!r) return `${name}${metric.perCapita ? 'Too few residents for a per-resident rate' : 'No crashes'}`;
  return `${name}${formatMetric(r.value, metric)} ${esc(metric.short.toLowerCase())}<br>`
    + (metric.perArea ? `${fmtInt(rec[metric.base])} ${esc(metricByKey(metric.base).short.toLowerCase())} over ${rec.sqmi.toFixed(2)} sq mi<br>` : '')
    + `Rank ${r.rank} of ${ranking.rows.length} · decile ${r.decile}<br>`
    + `${r.vsAvg ? r.vsAvg.toFixed(2) + '× the average zip' : ''}`;
}

function renderDensityInsight(dRanking, dMetric, countRanking, borough) {
  const el = $('density-insight');
  const top = dRanking.rows[0];
  if (!top) { el.textContent = ''; return; }
  const where = borough ? `in ${boroughName(borough)}` : 'citywide';
  const unit = dMetric.short.toLowerCase();
  let text = `Densest ${where}: ${top.rec.zip} at ${fmtInt(top.value)} ${unit}, ${top.vsAvg.toFixed(1)}× the average zip.`;
  // Show how the zip with the most crashes fares once size is taken into account.
  const biggest = countRanking.rows[0];
  const biggestDensity = biggest && dRanking.byZip.get(biggest.rec.zip);
  if (biggestDensity && biggest.rec.zip !== top.rec.zip) {
    text += ` ${biggest.rec.zip}, #1 by total, ranks #${biggestDensity.rank} by density (${biggest.rec.sqmi.toFixed(1)} sq mi).`;
  }
  el.textContent = text;
}

function renderInsight(ranking, metric, borough) {
  const el = $('table-insight');
  const n = ranking.rows.length;
  if (!n) { el.textContent = 'No zips to rank in this period.'; return; }
  const where = borough ? `in ${boroughName(borough)}` : 'citywide';
  if (metric.perCapita) {
    const top = ranking.rows[0];
    el.textContent = `${top.rec.zip} has the highest rate ${where}: ${fmt1(top.value)} per 10k residents, ${top.vsAvg.toFixed(1)}× the average zip.`;
    return;
  }
  const top = ranking.rows.filter((r) => r.decile === 1);
  const share = top.reduce((s, r) => s + r.value, 0) / (ranking.total || 1);
  el.textContent = `The top ${top.length} of ${n} zips ${where} account for ${Math.round(share * 100)}% of ${metric.short.toLowerCase()}.`;
}

const COLUMNS = [
  { key: 'rank', label: 'Rank', cls: 'left', get: (r) => r.rank },
  { key: 'zip', label: 'Zip', cls: 'left', get: (r) => r.rec.zip },
  { key: 'borough', label: 'Borough', cls: 'left', citywideOnly: true, get: (r) => boroughName(r.rec.borough) },
  { key: 'value', label: null, get: (r) => r.value },
  { key: 'vsAvg', label: '× avg', title: 'Multiple of the average zip in this area', get: (r) => r.vsAvg },
  { key: 'change', label: 'vs prior', title: 'Change from the previous period of equal length, for crashes recorded with a zip code. Shown when the prior period had at least 5.', get: (r) => r.change },
];

function renderTable(ranking, borough, metric, c) {
  const cols = COLUMNS.filter((col) => !(col.citywideOnly && borough));
  const table = $('zip-table');
  table.tHead.innerHTML = `<tr>${cols.map((col) => {
    const sorted = sort.key === col.key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : null;
    return `<th class="${col.cls ?? ''}" ${sorted ? `aria-sort="${sorted}"` : ''} ${col.title ? `title="${esc(col.title)}"` : ''}>
      <button type="button" data-sort="${col.key}">${esc(col.label ?? metric.short)}</button></th>`;
  }).join('')}</tr>`;

  const col = COLUMNS.find((x) => x.key === sort.key) ?? COLUMNS[0];
  const rows = ranking.rows.slice().sort((a, b) => {
    const va = col.get(a);
    const vb = col.get(b);
    if (va == null) return 1;
    if (vb == null) return -1;
    const d = typeof va === 'string' ? va.localeCompare(vb) : va - vb;
    return sort.dir === 'asc' ? d : -d;
  });

  table.tBodies[0].innerHTML = rows.length ? rows.map((r) => {
    const ch = r.change;
    const chCls = ch == null || Math.abs(ch) < 0.005 ? 'muted' : ch > 0 ? 'delta-up' : 'delta-down';
    return `<tr data-zip="${r.rec.zip}" class="${r.rec.zip === state.zip ? 'is-selected' : ''}" tabindex="0">
      <td class="left"><i class="decile-chip" style="background:${c.ramp[r.decile - 1]}" title="Decile ${r.decile}"></i>${r.rank}</td>
      <td class="left zip">${r.rec.zip}</td>
      ${borough ? '' : `<td class="left muted">${esc(boroughName(r.rec.borough))}</td>`}
      <td class="metric-col">${formatMetric(r.value, metric)}</td>
      <td>${r.vsAvg == null ? '–' : r.vsAvg.toFixed(2) + '×'}</td>
      <td class="${chCls}">${fmtPct(ch)}</td>
    </tr>`;
  }).join('') : `<tr class="empty-row"><td colspan="${cols.length}">No data for this period.</td></tr>`;
}

$('zip-table').addEventListener('click', (e) => {
  const sortKey = e.target.closest('button[data-sort]')?.dataset.sort;
  if (sortKey) {
    const numericDesc = !['rank', 'zip', 'borough'].includes(sortKey);
    sort = sort.key === sortKey ? { key: sortKey, dir: sort.dir === 'asc' ? 'desc' : 'asc' } : { key: sortKey, dir: numericDesc ? 'desc' : 'asc' };
    if (current.ranking) renderTable(current.ranking, current.borough, current.metric, colors());
    return;
  }
  const zip = e.target.closest('tr[data-zip]')?.dataset.zip;
  if (zip) setState({ zip });
});
$('zip-table').addEventListener('keydown', (e) => {
  const zip = e.target.closest?.('tr[data-zip]')?.dataset.zip;
  if (zip && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setState({ zip }); }
});
$('zip-table').addEventListener('mouseover', (e) => {
  const zip = e.target.closest('tr[data-zip]')?.dataset.zip;
  if (zip) eachMap((m) => m.highlight(zip, true));
});
$('zip-table').addEventListener('mouseout', (e) => {
  const zip = e.target.closest('tr[data-zip]')?.dataset.zip;
  if (zip && !e.relatedTarget?.closest?.(`tr[data-zip="${zip}"]`)) eachMap((m) => m.highlight(zip, false));
});

/* ---------- zip detail drawer ---------- */

let drawerFor = null;

function renderDrawer() {
  const zip = state.zip;
  const feature = zip && geo.byZip.get(zip);
  const open = Boolean(feature && current.records);
  const wasOpen = !$('drawer').hidden;
  $('drawer').hidden = !open;
  $('scrim').hidden = !open || window.innerWidth >= 1280;
  document.body.classList.toggle('drawer-open', open);
  if (wasOpen !== open) setTimeout(() => eachMap((m) => m.invalidate()), 0);
  zipMap.select(open ? zip : null);
  densityMap.select(open ? zip : null, { fly: false }); // follows zipMap's view via linkViews
  if (!open) { drawerFor = null; return; }

  const { range, metric, records } = current;
  const rec = records.get(zip);
  const { pop, borough } = feature.properties;
  const city = rankRecords(records, metric);
  const boro = rankRecords(records, metric, borough);
  const cr = city.byZip.get(zip);
  const br = boro.byZip.get(zip);
  const key = `${zip}|${range.start}|${range.end}|${metric.key}|${current.data.complete}`;
  if (drawerFor === key) return;
  const firstOpen = !drawerFor?.startsWith(zip + '|');
  drawerFor = key;

  $('drawer-borough').textContent = boroughName(borough);
  $('drawer-title').textContent = zip;
  const others = feature.properties.zips.filter((z) => z !== zip);
  $('drawer-pop').textContent = `${pop ? fmtInt(pop) + ' residents' : 'Population unknown'}${others.length ? ` · includes ${others.join(', ')}` : ''}`;

  const tile = (label, v) => `<div class="stat"><div class="stat-label">${label}</div><div class="stat-value">${v}</div></div>`;
  const rankRow = (label, r, of) => r
    ? `<div class="rank-row"><div><strong>#${r.rank}</strong> <span class="muted">of ${of}</span><p class="card-sub">${label}</p></div>
       <div style="text-align:right"><strong>Decile ${r.decile}</strong><p class="card-sub">${r.vsAvg.toFixed(2)}× average</p></div></div>`
    : `<div class="rank-row"><p class="card-sub">${label}: not ranked${metric.perCapita ? ' (too few residents)' : ''}</p></div>`;

  const scope = { zips: feature.properties.zips };
  $('drawer-body').innerHTML = `
    <section class="drawer-section">
      <h3>${esc(formatRange(range))}</h3>
      <div class="stat-grid">
        ${tile('Crashes', fmtInt(rec.n))}
        ${tile('Injured', fmtInt(rec.inj))}
        ${tile('Killed', fmtInt(rec.kil))}
        ${tile('Pedestrians', fmtInt(rec.ped))}
        ${tile('Cyclists', fmtInt(rec.cyc))}
        ${tile('Crashes / 10k', fmt1(rate(rec.n, pop)))}
        ${tile('Crashes / sq mi', rec.sqmi > 0 ? fmtInt(rec.n / rec.sqmi) : '–')}
        ${tile('Injured / sq mi', rec.sqmi > 0 ? fmtInt(rec.inj / rec.sqmi) : '–')}
        ${tile('Area', rec.sqmi ? rec.sqmi.toFixed(2) + ' sq mi' : '–')}
      </div>
    </section>
    <section class="drawer-section">
      <h3>Ranking by ${esc(metric.label.toLowerCase())}</h3>
      <div class="rank-list">
        ${rankRow('Citywide', cr, city.rows.length)}
        ${rankRow(`In ${boroughName(borough)}`, br, boro.rows.length)}
      </div>
    </section>
    <section class="drawer-section card-like" id="d-trend">
      <h3>Crashes over time</h3>
      <p class="card-sub" id="d-trend-sub">Crashes recorded with this zip code</p>
      <div class="chart-box"><canvas id="d-trend-chart" role="img" aria-label="Crash trend for ${zip}"></canvas></div>
    </section>
    <section class="drawer-section">
      <h3>Most dangerous intersections</h3>
      <ul class="list" id="d-streets"><li><span class="skeleton" style="width:100%">.</span></li></ul>
    </section>
    <section class="drawer-section">
      <h3>Top contributing factors</h3>
      <ul class="list" id="d-factors"><li><span class="skeleton" style="width:100%">.</span></li></ul>
    </section>`;
  if (firstOpen) $('drawer-body').scrollTop = 0;

  const still = () => drawerFor === key;
  const span = { start: range.prev.start, end: range.end };
  api.daily(span, scope).then((rows) => {
    if (!still()) return;
    const series = trendSeries(rows, range, 'n');
    $('d-trend-sub').textContent = `Crashes recorded with this zip code · ${trendSummary(rows, range, 'n', series.mode, 'Crashes')}`;
    trendChart($('d-trend-chart'), { series, unitLabel: 'crashes' });
  }).catch(() => still() && ($('d-trend').querySelector('.chart-box').textContent = 'Couldn’t load the trend.'));

  const list = (id, rows, label, value) => {
    $(id).innerHTML = rows.length
      ? rows.map((r) => `<li><span>${esc(label(r))}</span><span>${value(r)}</span></li>`).join('')
      : '<li><span class="muted">None recorded</span></li>';
  };
  api.intersections(range, scope).then((rows) => still() && list('d-streets', rows,
    (r) => `${titleCase(r.a)} & ${titleCase(r.b)}`,
    (r) => `${fmtInt(r.n)} crashes · ${fmtInt(Number(r.inj) || 0)} injured`))
    .catch(() => still() && ($('d-streets').innerHTML = '<li><span class="muted">Couldn’t load</span></li>'));
  api.factors(range, scope).then((rows) => still() && list('d-factors', rows.slice(0, 6),
    (r) => r.label, (r) => `${fmtInt(r.n)}`))
    .catch(() => still() && ($('d-factors').innerHTML = '<li><span class="muted">Couldn’t load</span></li>'));
}

/* ---------- CSV export ---------- */

function exportCSV() {
  const { ranking, range, borough, metric } = current;
  if (!ranking) return;
  const header = ['rank', 'decile', 'zip', 'borough', 'population', 'crashes', 'injured', 'killed',
    'pedestrians_injured_or_killed', 'cyclists_injured_or_killed', 'crashes_per_10k', 'sq_mi', 'crashes_per_sq_mi', `${metric.key}_vs_avg`, `${metric.key}_change_vs_prior`];
  const lines = [header.join(',')];
  for (const r of ranking.rows) {
    const x = r.rec;
    lines.push([r.rank, r.decile, x.zip, `"${boroughName(x.borough)}"`, x.pop, x.n, x.inj, x.kil, x.ped, x.cyc,
      rate(x.n, x.pop)?.toFixed(2) ?? '', x.sqmi, x.sqmi > 0 ? (x.n / x.sqmi).toFixed(1) : '', r.vsAvg?.toFixed(3) ?? '', r.change?.toFixed(4) ?? ''].join(','));
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `nyc-crashes_${borough ? borough.toLowerCase().replace(' ', '-') : 'citywide'}_${metric.key}_${range.start}_${range.end}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

window.addEventListener('resize', () => {
  if (state.zip) $('scrim').hidden = $('drawer').hidden || window.innerWidth >= 1280;
});

init();
