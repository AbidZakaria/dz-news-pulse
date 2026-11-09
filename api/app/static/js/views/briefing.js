// Daily briefing: one day in a single readable column. Extractive only: every headline and
// summary is the outlet's own text; the ranking is the number of independent outlets.
import { get } from '../api.js';
import { formatDay, formatNumber, plural, t, topicName } from '../i18n.js';
import {
  articleItem, blockDir, content, errorBox, esc, icon, meta, outletStack, skeleton, storyView,
} from '../ui.js';

export async function render(el, ctx) {
  ctx.setTitle(t('briefing_title'));
  el.innerHTML = skeleton(10);
  const date = /^\d{4}-\d{2}-\d{2}$/.test(ctx.query.date || '') ? ctx.query.date : undefined;
  let b;
  try {
    b = await get('/briefing', { date });
  } catch (err) {
    if (ctx.isCurrent()) el.innerHTML = errorBox(err, () => render(el, ctx));
    return;
  }
  if (!ctx.isCurrent()) return;

  const days = b.days.map((d) => d.day);
  const at = days.indexOf(b.date);
  const older = at >= 0 && at + 1 < days.length ? days[at + 1] : null;
  const newer = at > 0 ? days[at - 1] : null;
  const dayLink = (day, label, iconName) => (day
    ? `<a class="btn" href="#/briefing?date=${day}" aria-label="${esc(label)}" title="${esc(label)}">${icon(iconName)}</a>`
    : `<span class="btn" aria-disabled="true" style="opacity:.4">${icon(iconName)}</span>`);

  el.innerHTML = `
    <div style="max-width:780px">
      <div class="page-head">
        <div>
          <h1 class="page-title">${esc(t('briefing_title'))}</h1>
          <p class="page-sub">${esc(formatDay(b.date, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }))}</p>
        </div>
        <div style="display:flex;gap:8px">${dayLink(older, t('prev_day'), 'prev')}${dayLink(newer, t('next_day'), 'next')}</div>
      </div>

      <p style="font-size:17px">${esc(t('brief_summary', {
        articles: plural('articles', b.articles), sources: plural('outlets', b.sources),
        ar: formatNumber(b.ar), fr: formatNumber(b.fr),
      }))}</p>
      ${b.topics.length ? `<div class="chips" style="margin-top:14px" aria-label="${esc(t('brief_topics'))}">${b.topics.map((x) => `
        <a class="chip" href="#/topic/${esc(x.topic_id)}">${esc(topicName(x.topic_id, x.topic))} <b class="num">${formatNumber(x.articles)}</b></a>`).join('')}</div>` : ''}

      <section class="section" aria-labelledby="bt-h">
        <h2 class="section-title" id="bt-h" style="margin-bottom:18px">${esc(t('brief_top'))}</h2>
        ${b.stories.length ? `<ol class="brief-list" style="gap:28px">${b.stories.map((s) => {
          const v = storyView(s);
          return `<li><div dir="${blockDir(v.lang)}">
            <a class="t brief-headline" lang="${v.lang}" href="#/story/${s.story_id}">${esc(v.title)}</a>
            ${v.summary ? content(v.summary, 'p', 'tl-summary') : ''}
            <div ${meta('row-meta')}>${outletStack(s.outlets)}<span>${esc(plural('outlets', s.independent_source_count))}</span>
              <span>${esc(plural('articles', s.article_count))}</span></div>
          </div></li>`;
        }).join('')}</ol>` : `<p class="empty">${esc(t('brief_empty'))}</p>`}
      </section>

      ${b.also.length ? `<section class="section" aria-labelledby="ba-h">
        <h2 class="section-title" id="ba-h" style="margin-bottom:12px">${esc(t('brief_also'))}</h2>
        <ul class="compact">${b.also.map(articleItem).join('')}</ul>
      </section>` : ''}

      <p class="note" style="margin-top:36px">${esc(t('brief_note'))} ${esc(t('times_note'))}</p>
    </div>`;
}
