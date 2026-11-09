// Hand-rolled SVG charts: a line chart with a hover/keyboard crosshair, and sparklines.
// Follows the dataviz rules: 2px lines, 10% area wash, hairline grid, legend for 2+ series,
// text in ink colours (never the series colour), and null = "not collected", never zero.
import { formatNumber, t } from './i18n.js';
import { esc } from './ui.js';

const SVG_NS = 'http://www.w3.org/2000/svg';
const tooltip = () => document.getElementById('tooltip');

function niceMax(value) {
  if (value <= 4) return 4;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 2.5, 5, 10]) {
    if (step * magnitude >= value) return step * magnitude;
  }
  return 10 * magnitude;
}

/**
 * @param {HTMLElement} el
 * @param {{points: {label: string, title: string}[], series: {name: string, color: string, values: (number|null)[]}[],
 *          height?: number, ariaLabel?: string}} spec
 */
export function lineChart(el, spec) {
  el.classList.add('chart');
  el.setAttribute('dir', 'ltr');           // time runs left to right in every language
  el.tabIndex = 0;
  el.setAttribute('role', 'group');
  el.setAttribute('aria-label', spec.ariaLabel || '');

  const render = () => draw(el, spec);
  render();
  if (el._observer) el._observer.disconnect();
  let lastWidth = el.clientWidth;
  el._observer = new ResizeObserver(() => {
    if (Math.abs(el.clientWidth - lastWidth) > 4) { lastWidth = el.clientWidth; render(); }
  });
  el._observer.observe(el);
}

function draw(el, spec) {
  const width = Math.max(260, el.clientWidth);
  const height = spec.height || 180;
  const pad = { l: 34, r: 10, t: 10, b: 26 };
  const n = spec.points.length;
  const all = spec.series.flatMap((s) => s.values).filter((v) => v !== null && v !== undefined);
  const yMax = niceMax(Math.max(1, ...all));
  const step = n > 1 ? (width - pad.l - pad.r) / (n - 1) : 0;
  const x = (i) => pad.l + i * step;
  const y = (v) => pad.t + (height - pad.t - pad.b) * (1 - v / yMax);
  const base = y(0);

  const parts = [];
  // gridlines + y ticks
  for (const v of [0, yMax / 2, yMax]) {
    parts.push(`<line class="gridline" x1="${pad.l}" x2="${width - pad.r}" y1="${y(v)}" y2="${y(v)}"/>`);
    parts.push(`<text class="axis-label" x="${pad.l - 8}" y="${y(v) + 4}" text-anchor="end">${formatNumber(v)}</text>`);
  }
  // "not collected" bands: points where every series is null
  const missing = spec.points.map((_, i) => spec.series.every((s) => s.values[i] === null || s.values[i] === undefined));
  for (let i = 0; i < n; i += 1) {
    if (!missing[i] || (i > 0 && missing[i - 1])) continue;
    let j = i;
    while (j + 1 < n && missing[j + 1]) j += 1;
    const x0 = Math.max(pad.l, x(i) - step / 2);
    const x1 = Math.min(width - pad.r, x(j) + step / 2);
    parts.push(`<rect class="gap-band" x="${x0}" y="${pad.t}" width="${x1 - x0}" height="${base - pad.t}" rx="4"/>`);
    if (x1 - x0 > 90) {
      parts.push(`<text class="gap-label" x="${(x0 + x1) / 2}" y="${pad.t + 18}" text-anchor="middle">${esc(t('not_collected'))}</text>`);
    }
  }
  // x tick labels (about 5, never crowded)
  const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor((width - pad.l) / 80))));
  for (let i = 0; i < n; i += every) {
    const anchor = i === 0 ? 'start' : 'middle';
    parts.push(`<text class="axis-label" x="${x(i)}" y="${height - 6}" text-anchor="${anchor}">${esc(spec.points[i].label)}</text>`);
  }
  // series: area wash + 2px line, broken at nulls
  for (const s of spec.series) {
    const segments = [];
    let current = [];
    s.values.forEach((v, i) => {
      if (v === null || v === undefined) { if (current.length) segments.push(current); current = []; } else current.push(i);
    });
    if (current.length) segments.push(current);
    for (const seg of segments) {
      const line = seg.map((i, k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)},${y(s.values[i]).toFixed(1)}`).join('');
      const area = `${line}L${x(seg.at(-1)).toFixed(1)},${base}L${x(seg[0]).toFixed(1)},${base}Z`;
      parts.push(`<path class="area" d="${area}" style="fill:${s.color}"/>`);
      parts.push(`<path class="line" d="${line}" style="stroke:${s.color}"/>`);
      if (seg.length === 1) parts.push(`<circle cx="${x(seg[0])}" cy="${y(s.values[seg[0]])}" r="3" style="fill:${s.color}"/>`);
    }
  }
  parts.push('<g class="hover" visibility="hidden"><line class="cursor"/></g>');
  parts.push(`<rect class="hit" x="${pad.l - step / 2}" y="0" width="${width - pad.l - pad.r + step}" height="${height}" fill="transparent"/>`);

  el.innerHTML = `<svg viewBox="0 0 ${width} ${height}" height="${height}" xmlns="${SVG_NS}">${parts.join('')}</svg>`;

  const svg = el.querySelector('svg');
  const hover = svg.querySelector('.hover');
  const cursor = hover.querySelector('.cursor');
  const dots = spec.series.map((s) => {
    const c = document.createElementNS(SVG_NS, 'circle');
    c.setAttribute('r', '4.5');
    c.setAttribute('class', 'dot');
    c.style.fill = s.color;
    hover.appendChild(c);
    return c;
  });
  let index = null;

  const show = (i, clientX, clientY) => {
    index = Math.max(0, Math.min(n - 1, i));
    hover.setAttribute('visibility', 'visible');
    cursor.setAttribute('x1', x(index)); cursor.setAttribute('x2', x(index));
    cursor.setAttribute('y1', pad.t); cursor.setAttribute('y2', base);
    spec.series.forEach((s, k) => {
      const v = s.values[index];
      dots[k].setAttribute('visibility', v === null || v === undefined ? 'hidden' : 'visible');
      if (v !== null && v !== undefined) { dots[k].setAttribute('cx', x(index)); dots[k].setAttribute('cy', y(v)); }
    });
    const rows = spec.series.map((s) => {
      const v = s.values[index];
      const value = v === null || v === undefined ? '—' : formatNumber(v);
      return `<div class="tt-row"><span><i style="background:${s.color}"></i>${esc(s.name)}</span><b class="num">${value}</b></div>`;
    }).join('');
    const tip = tooltip();
    tip.innerHTML = `<div class="tt-title">${esc(spec.points[index].title)}</div>${rows}`;
    tip.hidden = false;
    const box = svg.getBoundingClientRect();
    const scale = box.width / width;
    const px = clientX ?? box.left + x(index) * scale;
    const py = clientY ?? box.top + pad.t * scale;
    const tw = tip.offsetWidth;
    const left = px + 14 + tw > window.innerWidth - 8 ? px - 14 - tw : px + 14;
    tip.style.left = `${Math.max(8, left)}px`;
    tip.style.top = `${Math.max(8, py - 10)}px`;
  };
  const hide = () => { hover.setAttribute('visibility', 'hidden'); tooltip().hidden = true; index = null; };

  svg.addEventListener('pointermove', (e) => {
    const box = svg.getBoundingClientRect();
    const sx = ((e.clientX - box.left) / box.width) * width;
    show(Math.round((sx - pad.l) / (step || 1)), e.clientX, e.clientY);
  });
  svg.addEventListener('pointerleave', hide);
  el.onkeydown = (e) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      show((index ?? n - 1) + (e.key === 'ArrowRight' ? 1 : -1));
    } else if (e.key === 'Escape') hide();
  };
  el.onblur = hide;
}

/** A tiny trend line. `wide` stretches to its container (no end dot, which would distort). */
export function sparkline(values, { wide = false } = {}) {
  const w = wide ? 240 : 72;
  const h = wide ? 36 : 24;
  if (!values?.length) return '';
  const max = Math.max(1, ...values.filter((v) => v !== null));
  const step = values.length > 1 ? (w - 4) / (values.length - 1) : 0;
  // Null = not collected: the line starts where collection starts, at its true position in time.
  const pts = values.map((v, i) => (v === null ? null : [2 + i * step, h - 2 - ((h - 4) * v) / max])).filter(Boolean);
  if (pts.length < 3) return '';          // two points are not a trend
  const d = pts.map(([px, py], i) => `${i ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join('');
  const [lx, ly] = pts.at(-1);
  const dot = wide ? '' : `<circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="2.5"/>`;
  const aspect = wide ? ' preserveAspectRatio="none"' : '';
  return `<svg class="spark" viewBox="0 0 ${w} ${h}"${aspect} aria-hidden="true"><path d="${d}" vector-effect="non-scaling-stroke"/>${dot}</svg>`;
}

export function legend(series) {
  return `<div class="legend">${series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join('')}</div>`;
}
