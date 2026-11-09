// One story: who covered it, in which language, in what order, and how it was grouped.
import { get } from '../api.js';
import {
  formatDate, formatDuration, formatNumber, languageName, t,
} from '../i18n.js';
import {
  blockDir, content, errorBox, esc, icon, languageTags, media, meta, monogram, skeleton,
  sourceName, storyView, textLang, topicChip,
} from '../ui.js';

export async function render(el, ctx) {
  el.innerHTML = skeleton(10);
  let s;
  try {
    s = await get(`/stories/${ctx.params[0]}`);
  } catch (err) {
    if (ctx.isCurrent()) el.innerHTML = errorBox(err, () => render(el, ctx));
    return;
  }
  if (!ctx.isCurrent()) return;

  const v = storyView(s);
  ctx.setTitle(v.title);
  const articles = s.articles || [];
  const first = articles[0];
  const last = articles.at(-1);
  const byId = Object.fromEntries(articles.map((a) => [a.article_id, a]));
  const copies = s.copy_count || 0;

  el.innerHTML = `
    <a class="back-link" href="#/stories">${icon('back', 'icon-sm')}${esc(t('back_stories'))}</a>
    <div class="story-head">
      <div>
        <div class="lead-meta">${topicChip(s.topic_id, s.topic)} ${languageTags(s.languages)}</div>
        <h1 class="story-title t" lang="${v.lang}" dir="auto">${esc(v.title)}</h1>
        ${v.others.map((o) => `<p class="alt-title"><span class="lang-tag">${esc(t('also_in', { lang: languageName(o.language) }))}</span>${content(o.title, 'span', '', textLang(o.title))}</p>`).join('')}
        ${v.summary ? content(v.summary, 'p', 'lead-summary story-summary') : ''}
        <div class="facts">
          <div><div class="fact-label">${esc(t('fact_outlets'))}</div>
            <div class="fact-value">${formatNumber(s.independent_source_count)}</div>
            ${copies ? `<div class="note">${esc(t('flag_copy'))}: ${formatNumber(copies)}</div>` : ''}</div>
          <div><div class="fact-label">${esc(t('fact_articles'))}</div><div class="fact-value">${formatNumber(s.article_count)}</div></div>
          ${first ? `<div><div class="fact-label">${esc(t('fact_first'))}</div>
            <div class="fact-value">${esc(sourceName(first.source_id, first.source_name))}</div>
            <div class="note">${esc(formatDate(first.published_at, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }))}</div></div>` : ''}
          ${first && last && last !== first ? `<div><div class="fact-label">${esc(t('fact_span'))}</div>
            <div class="fact-value">${esc(formatDuration(new Date(last.published_at) - new Date(first.published_at)))}</div></div>` : ''}
        </div>
      </div>
      ${media(s.image_url, '', { eager: true })}
    </div>

    <section class="section" aria-labelledby="cov-h">
      <div class="section-head"><h2 class="section-title" id="cov-h">${esc(t('coverage'))}</h2></div>
      <ol class="timeline">${articles.map((a) => timelineItem(a, byId)).join('')}</ol>
      <p class="note">${esc(t('times_note'))}</p>
    </section>

    <section class="method" aria-labelledby="method-h">
      <h2 class="section-title" id="method-h">${esc(t('method_title'))}</h2>
      <p class="note" style="margin-top:8px">${esc(t('method_text', { avg: s.avg_similarity == null ? '—' : formatNumber(s.avg_similarity, { maximumFractionDigits: 2 }) }))}</p>
    </section>`;
}

function timelineItem(a, byId) {
  const original = a.duplicate_of && byId[a.duplicate_of];
  const flags = [
    a.published_first ? `<span class="flag first">${icon('first')}${esc(t('flag_first'))}</span>` : '',
    a.is_copy ? `<span class="flag">${icon('copy')}${esc(t('flag_copy'))}${original ? ` (${esc(sourceName(original.source_id, original.source_name))})` : ''}</span>` : '',
    a.confidence === 'medium' ? `<span class="flag">${icon('alert')}${esc(t('flag_lower'))}</span>` : '',
  ].join('');
  return `
  <li class="tl-item">
    ${monogram(a.source_id, a.source_name, 'mono-lg')}
    <div dir="${blockDir(a.language)}">
      <div ${meta('tl-head')}>
        <strong>${esc(sourceName(a.source_id, a.source_name))}</strong>
        <time datetime="${esc(a.published_at)}">${esc(formatDate(a.published_at, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }))}</time>
        <span class="lang-tag">${esc(languageName(a.language))}</span>
      </div>
      <a class="tl-title t" lang="${esc(a.language)}" dir="auto" href="${esc(a.url)}" target="_blank" rel="noopener"
         title="${esc(t('open_original'))}">${esc(a.title)}${icon('external', 'icon-sm')}</a>
      ${a.summary ? content(a.summary, 'p', 'tl-summary', a.language) : ''}
      ${flags ? `<div ${meta('flags')}>${flags}</div>` : ''}
    </div>
  </li>`;
}
