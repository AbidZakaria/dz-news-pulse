// App shell: navigation, language and theme switches, the "last collected" status and a
// small hash router (#/story/12, #/stories?topic=sports ...) so every view is linkable.
import { get } from './api.js';
import { applyDocumentLang, getLang, setLang, t, timeAgo, translateStatic } from './i18n.js';
import { esc, icon } from './ui.js';
import * as today from './views/today.js';
import * as briefing from './views/briefing.js';
import * as stories from './views/stories.js';
import * as story from './views/story.js';
import * as topics from './views/topics.js';
import * as topic from './views/topic.js';
import * as search from './views/search.js';
import * as sources from './views/sources.js';

const NAV = [
  { key: 'today', path: '/', label: 'nav_today' },
  { key: 'briefing', path: '/briefing', label: 'nav_briefing' },
  { key: 'stories', path: '/stories', label: 'nav_stories' },
  { key: 'topics', path: '/topics', label: 'nav_topics' },
  { key: 'search', path: '/search', label: 'nav_search' },
  { key: 'sources', path: '/sources', label: 'nav_sources' },
];

const ROUTES = [
  { re: /^\/?$/, view: today, nav: 'today' },
  { re: /^\/briefing$/, view: briefing, nav: 'briefing' },
  { re: /^\/stories$/, view: stories, nav: 'stories' },
  { re: /^\/story\/(\d+)$/, view: story, nav: 'stories' },
  { re: /^\/topics$/, view: topics, nav: 'topics' },
  { re: /^\/topic\/([\w-]+)$/, view: topic, nav: 'topics' },
  { re: /^\/search$/, view: search, nav: 'search' },
  { re: /^\/sources$/, view: sources, nav: 'sources' },
];

const $ = (id) => document.getElementById(id);
const view = $('view');
const scrollPositions = new Map();
let renderToken = 0;
let linkNavigation = false;
let currentHash = location.hash;

export function navigate(path, query = {}) {
  const search = new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== '' && v !== false)).toString();
  linkNavigation = true;
  location.hash = `#${path}${search ? `?${search}` : ''}`;
}

function parseHash() {
  const raw = location.hash.replace(/^#/, '') || '/';
  const [path, queryString = ''] = raw.split('?');
  return { path, query: Object.fromEntries(new URLSearchParams(queryString)) };
}

async function route() {
  const { path, query } = parseHash();
  const match = ROUTES.map((r) => ({ r, m: path.match(r.re) })).find((x) => x.m);
  const token = ++renderToken;
  closeMenu();
  renderNav(match?.r.nav);
  document.body.dataset.route = match?.r.nav || '';
  if (match?.r.nav !== 'search') $('top-q').value = '';

  if (!match) {
    document.title = 'DZ News Pulse';
    view.innerHTML = `<div class="empty"><h1 class="page-title">${esc(t('not_found'))}</h1>
      <p style="margin-top:14px"><a class="more-link" href="#/">${esc(t('go_home'))}</a></p></div>`;
    return;
  }
  const ctx = {
    params: match.m.slice(1),
    query,
    navigate,
    isCurrent: () => token === renderToken,
    setTitle: (title) => { document.title = title ? `${title} · DZ News Pulse` : 'DZ News Pulse'; },
  };
  try {
    await match.r.view.render(view, ctx);
  } catch (err) {
    console.error(err);
  }
  if (token !== renderToken) return;
  const saved = scrollPositions.get(location.hash);
  if (!linkNavigation && saved !== undefined) window.scrollTo(0, saved);
  else if (linkNavigation) {
    window.scrollTo(0, 0);
    // Move focus to the new page for keyboard and screen-reader users, unless a view focused a field.
    if (!view.contains(document.activeElement)) view.focus({ preventScroll: true });
  }
  linkNavigation = false;
}

function renderNav(active) {
  $('nav').innerHTML = NAV.map((n) => `
    <a href="#${n.path}" ${n.key === active ? 'aria-current="page"' : ''}>${icon(n.key)}<span>${esc(t(n.label))}</span></a>`).join('');
}

function renderChrome() {
  translateStatic();
  $('top-q').placeholder = t('search_placeholder');
  $('top-search').querySelector('.top-search-icon').innerHTML = icon('search');
  $('lang-switch').setAttribute('aria-label', t('lang_group'));
  $('lang-switch').innerHTML = [['en', 'EN'], ['fr', 'FR'], ['ar', 'ع']].map(([code, label]) => `
    <button type="button" lang="${code}" data-lang="${code}" aria-pressed="${code === getLang()}"
      title="${{ en: 'English', fr: 'Français', ar: 'العربية' }[code]}">${label}</button>`).join('');
  renderThemeButton();
  renderMenuButton(false);
  renderLive();
}

function renderThemeButton() {
  const dark = document.documentElement.dataset.theme !== 'light';
  const btn = $('theme-btn');
  btn.innerHTML = icon(dark ? 'sun' : 'moon');
  btn.setAttribute('aria-label', t(dark ? 'theme_to_light' : 'theme_to_dark'));
  btn.title = btn.getAttribute('aria-label');
  document.querySelector('meta[name="theme-color"]').content = dark ? '#0b1424' : '#f3f6fb';
}

function renderMenuButton(open) {
  const btn = $('menu-btn');
  btn.innerHTML = icon(open ? 'close' : 'menu');
  btn.setAttribute('aria-expanded', String(open));
  btn.setAttribute('aria-label', t(open ? 'menu_close' : 'menu_open'));
}

function openMenu() {
  $('sidebar').classList.add('open');
  $('scrim').hidden = false;
  renderMenuButton(true);
  $('nav').querySelector('a')?.focus();
}

function closeMenu() {
  if (!$('sidebar').classList.contains('open')) return;
  $('sidebar').classList.remove('open');
  $('scrim').hidden = true;
  renderMenuButton(false);
}

// ---- "last collected" status (refreshed every 5 minutes) ----
let lastRun = null;
async function refreshLive() {
  try {
    const ov = await get('/overview');
    lastRun = ov.last_run_at;
  } catch (_) { lastRun = null; }
  renderLive();
}

function renderLive() {
  const el = $('live');
  if (!lastRun) { el.innerHTML = ''; return; }
  const stale = Date.now() - new Date(lastRun).getTime() > 7 * 3600 * 1000;
  el.innerHTML = `<span class="live-dot${stale ? ' stale' : ''}" aria-hidden="true"></span>
    <span>${esc(t('live_updated', { time: timeAgo(lastRun) }))}<br><span class="muted">${esc(t('live_every'))}</span></span>`;
}

// ---- events ----
$('menu-btn').addEventListener('click', () => ($('sidebar').classList.contains('open') ? closeMenu() : openMenu()));
$('scrim').addEventListener('click', closeMenu);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeMenu(); });

$('theme-btn').addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('dz.theme', next); } catch (_) { /* storage blocked */ }
  renderThemeButton();
  route();                         // charts read colours from CSS, redraw them
});

$('lang-switch').addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-lang]');
  if (!btn || btn.dataset.lang === getLang()) return;
  setLang(btn.dataset.lang);
  renderChrome();
  route();
});

$('top-search').addEventListener('submit', (e) => {
  e.preventDefault();
  const q = $('top-q').value.trim();
  if (q.length >= 2) navigate('/search', { q });
});

document.addEventListener('click', (e) => {
  const a = e.target.closest('a[href^="#/"]');
  if (a && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) linkNavigation = true;
});

// Publishers' images: fade in once loaded; if one refuses to load, keep the placeholder.
document.addEventListener('load', (e) => {
  if (e.target.tagName === 'IMG' && e.target.closest('.media')) e.target.classList.add('ready');
}, true);
document.addEventListener('error', (e) => {
  if (e.target.tagName === 'IMG' && e.target.closest('.media')) e.target.remove();
}, true);

window.addEventListener('hashchange', () => {
  scrollPositions.set(currentHash, window.scrollY);
  currentHash = location.hash;
  route();
});
window.addEventListener('scroll', () => { scrollPositions.set(location.hash, window.scrollY); }, { passive: true });

// ---- boot ----
if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
applyDocumentLang();
renderChrome();
route();
refreshLive();
setInterval(refreshLive, 5 * 60 * 1000);
