// Small rendering helpers shared by every page: escaping, icons, outlets, story rows.
import {
  formatNumber, formatTime, getLang, isRtl, languageName, plural, t, timeAgo, topicName,
} from './i18n.js';

export const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// Inline SVG icons (24px grid, 1.75 stroke), one visual language for the whole UI.
const ICONS = {
  today: '<path d="M4 6.5A1.5 1.5 0 0 1 5.5 5h11A1.5 1.5 0 0 1 18 6.5V19H6a2 2 0 0 1-2-2z"/><path d="M18 9h2v8a2 2 0 0 1-2 2"/><path d="M8 9h6M8 12.5h6M8 16h4"/>',
  briefing: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  stories: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
  topics: '<path d="M5 9h14M5 15h14M10 4 8 20M16 4l-2 16"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  sources: '<path d="M5 11a8 8 0 0 1 8 8M5 5a14 14 0 0 1 14 14"/><circle cx="6" cy="18" r="1.4"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  prev: '<path d="m15 6-6 6 6 6"/>',
  next: '<path d="m9 6 6 6-6 6"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  alert: '<path d="M12 4 2.5 20h19z"/><path d="M12 10v4.5M12 17.2v.1"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  first: '<path d="M6 21V4h11l-2.5 4 2.5 4H6"/>',
  image: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m21 16-5-5-8 8"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
};
const DIRECTIONAL = new Set(['back', 'prev', 'next', 'external']);

export function icon(name, cls = '') {
  const flip = DIRECTIONAL.has(name) ? ' flip' : '';
  return `<svg class="icon ${cls}${flip}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name] || ''}</svg>`;
}

// ---- outlets ----
const OUTLETS = {
  algerie360: { mono: '360' },
  algerie_eco: { mono: 'AÉ' },
  dzfoot: { mono: 'DZF' },
  echorouk: { mono: 'ش', ar: 'الشروق' },
  ennahar: { mono: 'ن', ar: 'النهار' },
  elkhabar: { mono: 'خ', ar: 'الخبر' },
  elbilad: { mono: 'ب', ar: 'البلاد' },
};

export function sourceName(id, name) {
  return (getLang() === 'ar' && OUTLETS[id]?.ar) || name || id;
}

export function monogram(id, name, cls = '') {
  const mono = OUTLETS[id]?.mono || (name || id || '?').slice(0, 2).toUpperCase();
  const label = sourceName(id, name);
  return `<span class="mono ${cls}" title="${esc(label)}" aria-hidden="true">${esc(mono)}</span>`;
}

export function outletStack(outlets = [], max = 4) {
  const shown = outlets.slice(0, max).map((o) => monogram(o.source_id, o.source_name)).join('');
  const more = outlets.length > max ? `<span class="mono mono-plus" aria-hidden="true">+${outlets.length - max}</span>` : '';
  const names = outlets.map((o) => sourceName(o.source_id, o.source_name)).join(', ');
  return `<span class="outlets" role="img" aria-label="${esc(names)}">${shown}${more}</span>`;
}

// ---- language-aware text ----
const ARABIC_RE = /[؀-ۿ]/;
export const textLang = (text) => (ARABIC_RE.test(text || '') ? 'ar' : 'fr');
// A block of news (headline + summary) reads in the direction of its language. Its meta line is
// interface text, so it keeps the interface direction (`meta` attrs) and only its alignment
// follows the block (see .meta-ui in app.css).
export const blockDir = (lang) => (lang === 'ar' ? 'rtl' : 'ltr');
export const meta = (cls) => `class="${cls} meta-ui" dir="${isRtl() ? 'rtl' : 'ltr'}"`;

// Text published by an outlet, tagged with its language so the right face and leading apply.
export function content(text, tag = 'span', cls = '', lang = null) {
  const l = lang || textLang(text);
  return `<${tag} class="t ${cls}" lang="${l}" dir="auto">${esc(text)}</${tag}>`;
}

/** Pick how to show a story: in the reader's language when an outlet covered it in that language. */
export function storyView(story) {
  const versions = story.versions || {};
  const ui = getLang();
  let chosen = versions[ui];
  if (!chosen) {
    chosen = Object.values(versions).find((v) => v.article_id === story.representative_article_id)
      || { title: story.headline, summary: story.summary };
  }
  const title = chosen.title || story.headline;
  const others = Object.entries(versions)
    .filter(([, v]) => v.article_id !== chosen.article_id && v.title !== title)
    .map(([language, v]) => ({ language, title: v.title }));
  return { title, summary: chosen.summary || story.summary, lang: textLang(title), others };
}

export function languageTags(langs = []) {
  return langs.map((l) => `<abbr class="lang-tag" title="${esc(languageName(l))}">${esc(l.toUpperCase())}</abbr>`).join(' ');
}

export function topicChip(id, fallback) {
  if (!id || id === 'other') return '';
  return `<a class="chip" href="#/topic/${encodeURIComponent(id)}">${esc(topicName(id, fallback))}</a>`;
}

export function media(url, cls = '', { eager = false } = {}) {
  // Above the fold: fetch first and decode with the page; below it: lazy and off the main thread.
  const loading = eager ? 'fetchpriority="high"' : 'loading="lazy" decoding="async"';
  const img = url
    ? `<img src="${esc(url)}" alt="" ${loading} referrerpolicy="no-referrer">`
    : '';
  return `<div class="media ${cls}">${icon('image')}${img}</div>`;
}

export function timeEl(value) {
  if (!value) return '';
  return `<time datetime="${esc(value)}" title="${esc(new Date(value).toLocaleString())}">${esc(timeAgo(value))}</time>`;
}

export function storyRow(story, { rank } = {}) {
  const v = storyView(story);
  const outlets = story.outlets || [];
  return `
  <li class="story-row">
    ${media(story.image_url)}
    <div dir="${blockDir(v.lang)}">
      ${rank ? `<span class="rank">${formatNumber(rank)}</span>` : ''}
      <h3 class="t" lang="${v.lang}" dir="auto"><a href="#/story/${story.story_id}">${esc(v.title)}</a></h3>
      ${v.summary ? content(v.summary, 'p', 'summary') : ''}
      <div ${meta('row-meta')}>
        ${outletStack(outlets)}
        <span>${esc(plural('outlets', story.independent_source_count))}</span>
        <span>${languageTags(story.languages)}</span>
        ${timeEl(story.last_published_at)}
        ${topicChip(story.topic_id, story.topic)}
      </div>
    </div>
  </li>`;
}

export function articleItem(a) {
  return `
  <li>
    <time datetime="${esc(a.published_at)}" class="num">${esc(formatTime(a.published_at))}</time>
    <div dir="${blockDir(a.language)}">
      <a class="title t" lang="${esc(a.language)}" dir="auto" href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a>
      <div ${meta('src')}>
        <span>${esc(sourceName(a.source_id, a.source_name))}</span>
        ${a.topic_id && a.topic_id !== 'other' ? `<a href="#/topic/${esc(a.topic_id)}">${esc(topicName(a.topic_id, a.topic))}</a>` : ''}
        ${a.story_id ? `<a href="#/story/${a.story_id}">${esc(t('view_story'))}</a>` : ''}
      </div>
    </div>
  </li>`;
}

// ---- states ----
export function skeleton(lines = 6) {
  return `<div aria-busy="true" aria-label="${esc(t('loading'))}">${
    Array.from({ length: lines }, (_, i) => `<div class="skeleton" style="height:${i === 0 ? 34 : 18}px;width:${i === 0 ? 45 : 60 + ((i * 17) % 35)}%;margin:${i === 0 ? '10px 0 28px' : '0 0 14px'}"></div>`).join('')
  }</div>`;
}

export function errorBox(error, retry) {
  const id = `retry-${Math.random().toString(36).slice(2, 8)}`;
  setTimeout(() => document.getElementById(id)?.addEventListener('click', retry), 0);
  return `<div class="error-box" role="alert">
    <strong>${esc(t('error_title'))}</strong>
    <span>${esc(t('error_detail', { msg: error.message }))}</span>
    <button class="btn" id="${id}" type="button">${esc(t('retry'))}</button>
  </div>`;
}

export function changeLabel(current, previous) {
  if (previous === null || previous === undefined) return null;
  if (previous === 0) return current > 0 ? '+∞' : '0%';
  const pct = Math.round((100 * (current - previous)) / previous);
  return `${pct > 0 ? '+' : ''}${formatNumber(pct)}%`;
}

/** Wrap every occurrence of the (normalised) search terms in <mark>, without touching the text. */
export function highlight(text, terms) {
  const source = String(text ?? '');
  if (!terms?.length) return esc(source);
  // Build the normalised string with a map back to original character positions.
  let norm = '';
  const map = [];
  for (let i = 0; i < source.length; i += 1) {
    const n = normalizeChar(source[i]);
    for (let k = 0; k < n.length; k += 1) { norm += n[k]; map.push(i); }
  }
  const marks = new Array(source.length).fill(false);
  for (const term of terms) {
    let from = 0;
    for (;;) {
      const at = norm.indexOf(term, from);
      if (at < 0) break;
      for (let j = at; j < at + term.length; j += 1) marks[map[j]] = true;
      from = at + term.length;
    }
  }
  let out = '';
  let open = false;
  for (let i = 0; i < source.length; i += 1) {
    if (marks[i] && !open) { out += '<mark>'; open = true; }
    if (!marks[i] && open) { out += '</mark>'; open = false; }
    out += esc(source[i]);
  }
  return open ? `${out}</mark>` : out;
}

const FOLD = { 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ي', 'ة': 'ه' };
function normalizeChar(ch) {
  if (/[ً-ْـ]/.test(ch)) return '';
  const lower = (FOLD[ch] || ch).toLowerCase();
  if (lower.charCodeAt(0) >= 0x0250) return lower;   // same rule as the API: only Latin loses accents
  return lower.normalize('NFKD').replace(/[̀-ͯ]/g, '');
}
