// Charts: trend line (Chart.js), horizontal bars (Chart.js), hour x weekday grid (HTML).
/* global Chart */
import { fmtInt, fmtCompact, formatShortDate, formatDate } from './stats.js';

export const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function baseOptions() {
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", sans-serif';
  Chart.defaults.font.size = 12;
  Chart.defaults.color = css('--text-muted');
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 250 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: css('--tip-bg'),
        titleColor: css('--text-primary'),
        bodyColor: css('--text-secondary'),
        borderColor: css('--border'),
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        boxPadding: 4,
        usePointStyle: true,
      },
    },
  };
}

const charts = new Map();
function draw(canvas, config) {
  charts.get(canvas)?.destroy();
  const chart = new Chart(canvas, config);
  charts.set(canvas, chart);
  return chart;
}

export function trendChart(canvas, { current, previous, label, unitLabel }) {
  const accent = css('--series-1');
  const ghost = css('--text-muted');
  const grid = css('--grid');
  const tick = (b) => formatShortDate(b.from);
  const title = (b) => (b.from === b.to ? formatDate(b.from) : `${formatShortDate(b.from)} – ${formatDate(b.to)}`);

  const opts = baseOptions();
  opts.interaction = { mode: 'index', intersect: false };
  opts.scales = {
    x: {
      grid: { display: false },
      border: { color: css('--axis') },
      ticks: { maxRotation: 0, autoSkipPadding: 16, callback: (_, i) => (current[i] ? tick(current[i]) : '') },
    },
    y: {
      beginAtZero: true,
      grid: { color: grid },
      border: { display: false },
      ticks: { callback: (v) => fmtCompact(v), maxTicksLimit: 5, precision: 0 },
    },
  };
  opts.plugins.tooltip.callbacks = {
    title: (items) => title(current[items[0].dataIndex]),
    label: (item) => {
      const b = item.datasetIndex === 0 ? current[item.dataIndex] : previous[item.dataIndex];
      if (!b) return '';
      const when = item.datasetIndex === 0 ? 'This period' : `Prior (${title(b)})`;
      return ` ${when}: ${fmtInt(b.value)} ${unitLabel}`;
    },
  };

  return draw(canvas, {
    type: 'line',
    data: {
      labels: current.map(tick),
      datasets: [
        {
          label,
          data: current.map((b) => b.value),
          borderColor: accent,
          backgroundColor: accent + '1a',
          fill: 'origin',
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBorderWidth: 2,
          pointHoverBorderColor: css('--surface'),
          pointBackgroundColor: accent,
          tension: 0.25,
          cubicInterpolationMode: 'monotone',
        },
        {
          label: 'Prior period',
          data: current.map((_, i) => previous[i]?.value ?? null),
          borderColor: ghost,
          borderWidth: 2,
          borderDash: [],
          pointRadius: 0,
          pointHoverRadius: 4,
          pointBackgroundColor: ghost,
          pointHoverBorderColor: css('--surface'),
          tension: 0.25,
          cubicInterpolationMode: 'monotone',
          fill: false,
        },
      ],
    },
    options: opts,
  });
}

export function barChart(canvas, rows, { valueLabel = 'crashes' } = {}) {
  const accent = css('--series-1');
  const opts = baseOptions();
  opts.indexAxis = 'y';
  opts.scales = {
    x: {
      beginAtZero: true,
      grid: { color: css('--grid') },
      border: { display: false },
      ticks: { callback: (v) => fmtCompact(v), maxTicksLimit: 5 },
    },
    y: {
      grid: { display: false },
      border: { color: css('--axis') },
      ticks: { color: css('--text-secondary'), autoSkip: false, callback: (_, i) => truncate(rows[i].label, 30) },
    },
  };
  opts.plugins.tooltip.callbacks = {
    title: (items) => rows[items[0].dataIndex].label,
    label: (item) => ` ${fmtInt(item.raw)} ${valueLabel}`,
  };
  return draw(canvas, {
    type: 'bar',
    data: {
      labels: rows.map((r) => r.label),
      datasets: [{
        data: rows.map((r) => r.n),
        backgroundColor: accent,
        hoverBackgroundColor: css('--series-1-hover'),
        borderRadius: { topRight: 4, bottomRight: 4 },
        borderSkipped: 'start',
        barThickness: 14,
      }],
    },
    options: opts,
  });
}

const truncate = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const ORDER = [1, 2, 3, 4, 5, 6, 0]; // Monday first
const hourLabel = (h) => (h === 0 ? '12a' : h < 12 ? `${h}a` : h === 12 ? '12p' : `${h - 12}p`);
const hourLong = (h) => `${hourLabel(h).replace('a', ' am').replace('p', ' pm')}`;

export function hourGrid(el, rows) {
  const grid = Array.from({ length: 7 }, () => new Array(24).fill(0));
  let max = 0;
  for (const r of rows) {
    const d = Number(r.dow);
    const h = parseInt(r.hh, 10);
    if (!(d >= 0 && d < 7 && h >= 0 && h < 24)) continue;
    grid[d][h] += Number(r.n) || 0;
    max = Math.max(max, grid[d][h]);
  }
  const ramp = css('--seq-ramp').split(',').map((s) => s.trim());
  const cells = [];
  cells.push('<div class="hg-corner"></div>');
  for (let h = 0; h < 24; h++) cells.push(`<div class="hg-hour">${h % 3 === 0 ? hourLabel(h) : ''}</div>`);
  let peak = { d: 0, h: 0, v: -1 };
  for (const d of ORDER) {
    cells.push(`<div class="hg-day">${DOW[d]}</div>`);
    for (let h = 0; h < 24; h++) {
      const v = grid[d][h];
      if (v > peak.v) peak = { d, h, v };
      const step = max ? Math.min(ramp.length - 1, Math.floor((v / max) * ramp.length)) : 0;
      const tip = `${DOW[d]} ${hourLong(h)}–${hourLong((h + 1) % 24)}: ${fmtInt(v)} crashes`;
      cells.push(`<div class="hg-cell" style="background:${ramp[step]}" data-tip="${tip}" aria-label="${tip}"></div>`);
    }
  }
  el.innerHTML = cells.join('');
  return peak.v > 0 ? `${DOW[peak.d]}s, ${hourLong(peak.h)}–${hourLong((peak.h + 1) % 24)}` : null;
}

export function destroyAll() {
  for (const c of charts.values()) c.destroy();
  charts.clear();
}
