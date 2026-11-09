// Search: every word must appear in the headline or summary, in either language.
import { get } from '../api.js';
import { formatDate, languageName, plural, t, topicName } from '../i18n.js';
import {
  blockDir, errorBox, esc, highlight, media, meta, skeleton, sourceName, textLang,
} from '../ui.js';

const formatTimeShort = (v) => formatDate(v, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

export async function render(el, ctx) {
  ctx.setTitle(t('search_title'));
  const q = (ctx.query.q || '').trim();
  const language = ['fr', 'ar'].includes(ctx.query.language) ? ctx.query.language : '';
  const topInput = document.getElementById('top-q');
  if (topInput) topInput.value = q;

  el.innerHTML = `
    <div class="page-head"><div>
      <h1 class="page-title">${esc(t('search_title'))}</h1>
      <p class="page-sub">${esc(t('search_sub'))}</p>
    </div></div>
    <form class="search-hero" id="search-form" role="search">
      <label class="visually-hidden" for="search-q">${esc(t('search_label'))}</label>
      <input id="search-q" name="q" type="search" value="${esc(q)}" placeholder="${esc(t('search_placeholder'))}"
             autocomplete="off" spellcheck="false" enterkeyhint="search" dir="auto">
      <button class="btn btn-primary" type="submit">${esc(t('search_button'))}</button>
    </form>
    <div class="filters" style="margin-top:16px">
      <div class="seg" role="group" aria-label="${esc(t('language'))}">
        ${[['', t('all_langs')], ['fr', languageName('fr')], ['ar', languageName('ar')]].map(([code, label]) => `
          <button type="button" data-lang="${code}" aria-pressed="${code === language}">${esc(label)}</button>`).join('')}
      </div>
    </div>
    <div id="search-results" class="readable"></div>`;

  const form = el.querySelector('#search-form');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const next = form.q.value.trim();
    if (next.length >= 2) ctx.navigate('/search', { q: next, language });
  });
  el.querySelector('.filters').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-lang]');
    if (btn) ctx.navigate('/search', { q, language: btn.dataset.lang });
  });

  const box = el.querySelector('#search-results');
  if (q.length < 2) {
    if (!q) el.querySelector('#search-q').focus({ preventScroll: true });
    box.innerHTML = await suggestions();
    return;
  }
  box.innerHTML = skeleton(6);
  try {
    const res = await get('/search', { q, language, limit: 60 });
    if (!ctx.isCurrent()) return;
    if (!res.total) {
      box.innerHTML = `<p class="empty">${esc(t('no_results', { q }))}</p>${await suggestions()}`;
      return;
    }
    box.innerHTML = `
      <p class="result-count" aria-live="polite">${esc(t('results', { articles: plural('articles', res.total) }))}</p>
      <ul class="story-list">${res.results.map((a) => result(a, res.terms)).join('')}</ul>`;
  } catch (err) {
    if (ctx.isCurrent()) box.innerHTML = errorBox(err, () => render(el, ctx));
  }
}

function result(a, terms) {
  return `
  <li class="story-row">
    ${media(a.image_url)}
    <div dir="${blockDir(a.language)}">
      <h3 class="t" lang="${esc(a.language)}"><a href="${esc(a.url)}" target="_blank" rel="noopener">${highlight(a.title, terms)}</a></h3>
      ${a.summary ? `<p class="summary t" lang="${esc(a.language)}">${highlight(a.summary, terms)}</p>` : ''}
      <div ${meta('row-meta')}>
        <span>${esc(sourceName(a.source_id, a.source_name))}</span>
        <span>${esc(formatTimeShort(a.published_at))}</span>
        ${a.topic_id && a.topic_id !== 'other' ? `<a class="chip" href="#/topic/${esc(a.topic_id)}">${esc(topicName(a.topic_id, a.topic))}</a>` : ''}
        ${a.story_id ? `<a class="chip" href="#/story/${a.story_id}">${esc(t('view_story'))}</a>` : ''}
      </div>
    </div>
  </li>`;
}

async function suggestions() {
  try {
    const words = await get('/keywords/trending', { days: 7, limit: 16 });
    if (!words.length) return '';
    return `<section class="section"><h2 class="section-title" style="margin-bottom:12px">${esc(t('try_words'))}</h2>
      <div class="chips">${words.map((k) => `<a class="chip t" lang="${textLang(k.keyword)}" href="#/search?q=${encodeURIComponent(k.keyword)}">${esc(k.keyword)}</a>`).join('')}</div></section>`;
  } catch (_) {
    return '';
  }
}
