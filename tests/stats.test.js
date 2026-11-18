// Unit tests for stats.js and geo.js. Run in Node (`node tests/run.mjs`) or open tests/stats.test.html.
import {
  decileOf, rankRecords, resolveRange, addDays, daysBetween, bucketSeries, sumBetween,
  pctChange, normalizeVehicles, metricByKey, buildZipRecords, rate, densityMetric, metricValue,
} from '../js/stats.js';
import { indexZips, pointInGeometry } from '../js/geo.js';

export async function runTests(geojson) {
  const results = [];
  const test = (name, fn) => {
    try { fn(); results.push({ name, ok: true }); } catch (e) { results.push({ name, ok: false, error: e.message }); }
  };
  const eq = (a, b, msg = '') => {
    if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${msg} expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
  };
  const near = (a, b, eps = 1e-9) => { if (Math.abs(a - b) > eps) throw new Error(`expected ${b}, got ${a}`); };

  test('decileOf matches pandas qcut(rank, 10) + 1 for n=20', () => {
    // pandas: pd.qcut(range(1, 21), 10, labels=False) + 1
    eq(Array.from({ length: 20 }, (_, i) => decileOf(i + 1, 20)), [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10]);
  });
  test('decileOf matches pandas for n=177', () => {
    // pandas edges: 1 + 176 * i / 10 -> first bin holds ranks 1..18
    eq(decileOf(18, 177), 1);
    eq(decileOf(19, 177), 2);
    eq(decileOf(177, 177), 10);
    eq(decileOf(1, 1), 1);
  });

  test('rankRecords ranks, averages and compares', () => {
    const mk = (zip, n, prev, pop = 10000) => ({ zip, borough: 'QUEENS', pop, n, inj: 0, kil: 0, ped: 0, cyc: 0, tagged: { n }, prevTagged: { n: prev } });
    const recs = new Map([['a', mk('a', 30, 20)], ['b', mk('b', 10, 10)], ['c', mk('c', 20, 0)]]);
    const r = rankRecords(recs, metricByKey('n'));
    eq(r.rows.map((x) => x.rec.zip), ['a', 'c', 'b']);
    eq(r.rows.map((x) => x.rank), [1, 2, 3]);
    near(r.avg, 20);
    near(r.byZip.get('a').vsAvg, 1.5);
    near(r.byZip.get('a').change, 0.5);
    eq(r.byZip.get('c').change, null);
    near(r.byZip.get('b').share, 10 / 60);
  });
  test('per-capita metric skips small-population zips', () => {
    const mk = (zip, n, pop) => ({ zip, borough: 'QUEENS', pop, n, inj: 0, kil: 0, ped: 0, cyc: 0, tagged: { n }, prevTagged: { n } });
    const recs = new Map([['a', mk('a', 100, 3000)], ['b', mk('b', 50, 50000)]]);
    const r = rankRecords(recs, metricByKey('n_pc'));
    eq(r.rows.length, 1);
    near(r.rows[0].value, 10);
    eq(rate(5, 4999), null);
  });

  test('densityMetric divides the underlying count by area', () => {
    const rec = { n: 120, inj: 30, pop: 20000, sqmi: 0.5 };
    const d = densityMetric(metricByKey('n'));
    eq([d.key, d.base, d.perArea], ['n_sqmi', 'n', true]);
    near(metricValue(rec, d), 240);
    const fromRate = densityMetric(metricByKey('inj_pc'));
    eq(fromRate.base, 'inj');
    near(metricValue(rec, fromRate), 60);
    eq(metricValue({ ...rec, sqmi: 0 }, d), null);
  });

  test('date helpers', () => {
    eq(addDays('2024-02-28', 1), '2024-02-29');
    eq(addDays('2024-03-01', -1), '2024-02-29');
    eq(daysBetween('2026-01-01', '2026-12-31'), 365);
  });
  test('resolveRange presets and prior period', () => {
    const r = resolveRange({ range: '30d' }, '2026-11-13');
    eq([r.start, r.end, r.len], ['2026-10-15', '2026-11-13', 30]);
    eq([r.prev.start, r.prev.end], ['2026-09-15', '2026-10-14']);
    const y = resolveRange({ range: 'ytd' }, '2026-11-13');
    eq(y.start, '2026-01-01');
    const c = resolveRange({ range: 'custom', start: '2027-01-01', end: '2010-01-01' }, '2026-11-13');
    eq([c.start, c.end], ['2012-07-01', '2026-11-13']);
  });
  test('bucketSeries and sumBetween', () => {
    const rows = [
      { d: '2026-01-01T00:00:00.000', n: '2' }, { d: '2026-01-02T00:00:00.000', n: '3' },
      { d: '2026-01-08T00:00:00.000', n: '5' },
    ];
    const range = { start: '2026-01-01', end: '2026-01-10', len: 10 };
    eq(bucketSeries(rows, range, 'n', 7).map((b) => b.value), [5, 5]);
    eq(bucketSeries(rows, range, 'n', 7)[1], { from: '2026-01-08', to: '2026-01-10', value: 5 });
    eq(sumBetween(rows, { start: '2026-01-02', end: '2026-01-08' }).n, 8);
  });
  test('pctChange', () => {
    near(pctChange(110, 100), 0.1);
    eq(pctChange(5, 0), null);
  });
  test('normalizeVehicles merges aliases', () => {
    const out = normalizeVehicles([
      { label: 'SEDAN', n: '10' }, { label: '4 DR SEDAN', n: '5' },
      { label: 'STATION WAGON/SPORT UTILITY VEHICLE', n: '12' }, { label: 'UNKNOWN', n: '99' },
    ]);
    eq(out, [{ label: 'Sedan', n: 15 }, { label: 'SUV / station wagon', n: 12 }]);
  });

  test('pointInGeometry handles holes', () => {
    const square = (s) => [[0, 0], [s, 0], [s, s], [0, s], [0, 0]];
    const g = { type: 'Polygon', coordinates: [square(10), square(2).map(([x, y]) => [x + 4, y + 4])] };
    eq(pointInGeometry(1, 1, g), true);
    eq(pointInGeometry(5, 5, g), false);
    eq(pointInGeometry(11, 5, g), false);
  });

  if (geojson) {
    const geo = indexZips(geojson);
    test('locate: known landmarks fall in the right zip', () => {
      eq(geo.locate(40.7580, -73.9855), '10036', 'Times Square');
      eq(geo.locate(40.6782, -73.9442), '11216', 'Crown Heights');
      eq(geo.locate(40.5822, -74.1666), '10314', 'Staten Island Mall');
      eq(geo.locate(40.8296, -73.9262), '10452', 'Yankee Stadium (west of River Ave)');
      eq(geo.locate(40.0, -73.0), null, 'Atlantic Ocean');
    });
    test('zip areas are present and plausible', () => {
      const areas = geo.features.map((f) => f.properties.sqmi);
      eq(areas.every((a) => a > 0), true, 'every zip has an area');
      const total = areas.reduce((a, b) => a + b, 0);
      if (total < 280 || total > 310) throw new Error(`total area ${total} sq mi, expected ~300 (NYC land area)`);
      const ts = geo.byZip.get('10036').properties.sqmi;
      if (!(ts > 0.3 && ts < 1)) throw new Error(`10036 area ${ts}`);
    });
    test('postal zips map to their MODZCTA polygon', () => {
      eq(geo.postalToZip.get('10110'), '10036');
      eq(geo.byZip.get('11207').properties.borough, 'BROOKLYN');
    });
    test('buildZipRecords merges tagged rows and placed points', () => {
      const { records, unplaced } = buildZipRecords(geo,
        [{ zip_code: '10036', n: '4', inj: '1' }, { zip_code: '10110', n: '1' }, { zip_code: '99998', n: '7' }],
        [{ latitude: '40.7580', longitude: '-73.9855', n: '2' }, { latitude: '40.0', longitude: '-73.0', n: '3' }],
        [{ zip_code: '10036', n: '10' }]);
      const r = records.get('10036');
      eq([r.n, r.tagged.n, r.prevTagged.n, r.placed, r.inj], [7, 5, 10, 2, 1]);
      eq(r.sqmi, geo.byZip.get('10036').properties.sqmi);
      eq(unplaced, 10);
    });
  }
  return results;
}
