// Node runner for tests/stats.test.js:  node tests/run.mjs
import { readFile } from 'node:fs/promises';
import { runTests } from './stats.test.js';

const geojson = JSON.parse(await readFile(new URL('../data/nyc_zips.geojson', import.meta.url), 'utf8'));
const results = await runTests(geojson);
for (const r of results) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${r.ok ? '' : `\n      ${r.error}`}`);
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
