// Today: the most covered story leads, the other big stories follow; analytics sit in the
// side column, quiet, so the news stays the focus.
import { get } from '../api.js';
import { legend, lineChart, sparkline } from '../charts.js';
import {
  formatDate, formatDay, formatNumber, formatTime, languageName, plural, t, topicName,
} from '../i18n.js';
import {
  articleItem, blockDir, content, errorBox, esc, languageTags, media, meta, outletStack, skeleton,
  sourceName, storyRow, storyView, timeEl, topicChip,
} from '../ui.js';

let activityWindow = '24h';

export async function render(el, ctx) {
  ctx.setTitle(t('nav_today'));
  el.innerHTML = skeleton(9);
  let data;
  try {
    const [ov, top, brief, topics, latest, kwFr, kwAr] = await Promise.all([
      get('/overview'),
      get('/stories', { days: 3, hours: 48, min_sources: 2, limit: 9 }),
      get('/stories', { days: 2, hours: 24, min_sources: 2, limit: 3 }),
      get('/topics', { days: 7 }),
      get('/articles', { days: 2, limit: 8 }),
      get('/keywords/trending', { days: 3, language: 'fr', limit: 10 }),
      get('/keywords/trending', { days: 3, language: 'ar', limit: 10 }),
    ]);
    // A quiet news day can have no story covered twice: fall back to the newest stories.
    const stories = top.length ? top : await get('/stories', { days: 3, sort: 'recent', limit: 9 });
    data = { ov, stories, brief, topics, latest, kwFr, kwAr };
  } catch (err) {
    if (ctx.isCurrent()) el.innerHTML = errorBox(err, () => render(el, ctx));
    return;
  }
  if (!ctx.isCurrent()) return;

  const { ov, stories, brief, topics, latest, kwFr, kwAr } = data;
  const [lead, ...rest] = stories;
  el.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">${esc(ov.latest_article_at ? formatDate(ov.latest_article_at) : t('nav_today'))}</h1>
        <p class="page-sub">${esc(t('today_sub', {
          articles: plural('articles', ov.articles_24h ?? 0), sources: plural('outlets', ov.sources ?? 0),
        }))}</p>
      </div>
    </div>
    <div class="layout">
      <div class="col-main">
        ${lead ? `<section class="section">${leadStory(lead)}</section>` : ''}
        ${rest.length ? `
        <section class="section" aria-labelledby="top-h">
          <div class="section-head">
            <div><h2 class="section-title" id="top-h">${esc(t('top_stories'))}</h2>
              <p class="note">${esc(t('top_stories_sub'))}</p></div>
            <a class="more-link" href="#/stories">${esc(t('see_all_stories'))}</a>
          </div>
          <ul class="story-list">${rest.map((s) => storyRow(s)).join('')}</ul>
        </section>` : ''}
        <section class="section" aria-labelledby="latest-h">
          <div class="section-head">
            <h2 class="section-title" id="latest-h">${esc(t('latest'))}</h2>
            <a class="more-link" href="#/search">${esc(t('see_search'))}</a>
          </div>
          <ul class="compact">${latest.map(articleItem).join('')}</ul>
          <p class="note" style="margin-top:10px">${esc(t('times_note'))}</p>
        </section>
      </div>
      <aside class="side" aria-label="${esc(t('nav_topics'))}">
        ${statsBlock(ov)}
        ${briefBlock(brief)}
        <section aria-labelledby="act-h">
          <div class="section-head">
            <h2 class="section-title" id="act-h">${esc(t('activity'))}</h2>
            <div class="seg" role="group" aria-label="${esc(t('period'))}" id="act-range">
              ${['24h', '7d', '30d'].map((w) => `<button type="button" data-w="${w}" aria-pressed="${w === activityWindow}">${esc(t(`range_${w}`))}</button>`).join('')}
            </div>
          </div>
          <div id="act-legend"></div>
          <div id="act-chart" style="min-height:180px"></div>
        </section>
        ${topicsBlock(topics)}
        ${keywordsBlock(kwFr, kwAr)}
      </aside>
    </div>`;

  el.querySelector('#act-range').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-w]');
    if (!btn) return;
    activityWindow = btn.dataset.w;
    el.querySelectorAll('#act-range button').forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
    drawActivity(el);
  });
  drawActivity(el);
}

function leadStory(s) {
  const v = storyView(s);
  const first = s.outlets?.[0];
  return `
  <article class="lead" dir="${blockDir(v.lang)}">
    <a href="#/story/${s.story_id}" tabindex="-1" aria-hidden="true">${media(s.image_url, '', { eager: true })}</a>
    <div ${meta('lead-meta')}>${topicChip(s.topic_id, s.topic)} ${languageTags(s.languages)} ${timeEl(s.last_published_at)}</div>
    <h2 class="lead-title t" lang="${v.lang}" dir="auto"><a href="#/story/${s.story_id}">${esc(v.title)}</a></h2>
    ${v.summary ? content(v.summary, 'p', 'lead-summary') : ''}
    <div ${meta('coverage-line')}>
      ${outletStack(s.outlets, 6)}
      <span>${esc(plural('outlets', s.independent_source_count))}, ${esc(plural('articles', s.article_count))}</span>
      ${first ? `<span class="muted">${esc(t('first_by', { source: sourceName(first.source_id, first.source_name) }))}</span>` : ''}
    </div>
  </article>`;
}

function statsBlock(ov) {
  const items = [
    [t('stat_articles'), ov.total_articles, t('delta_24h', { n: formatNumber(ov.articles_24h ?? 0) })],
    [t('stat_shared'), ov.multi_source_stories ?? 0, t('delta_multi', { n: formatNumber(ov.multilingual_stories ?? 0) })],
    [t('stat_sources'), ov.sources, ov.sources_failing
      ? t('delta_sources_bad', { n: formatNumber(ov.sources_failing) }) : t('delta_sources_ok')],
    [t('stat_topics'), ov.topics_detected, t('delta_topics')],
  ];
  return `<section class="stats" aria-label="${esc(t('stat_articles'))}">${items.map(([label, value, delta]) => `
    <div><div class="stat-label">${esc(label)}</div><div class="stat-value">${formatNumber(value ?? 0)}</div>
      <div class="stat-delta">${esc(delta)}</div></div>`).join('')}</section>`;
}

function briefBlock(brief) {
  if (!brief.length) return '';
  return `<section aria-labelledby="brief-h">
    <div class="section-head"><h2 class="section-title" id="brief-h">${esc(t('in_brief'))}</h2></div>
    <p class="note" style="margin:-6px 0 14px">${esc(t('in_brief_sub'))}</p>
    <ol class="brief-list">${brief.map((s) => {
      const v = storyView(s);
      return `<li><div dir="${blockDir(v.lang)}"><a class="t" lang="${v.lang}" href="#/story/${s.story_id}">${esc(v.title)}</a>
        <div ${meta('sub')}>${esc(plural('outlets', s.independent_source_count))}</div></div></li>`;
    }).join('')}</ol>
    <p style="margin-top:16px"><a class="more-link" href="#/briefing">${esc(t('open_briefing'))}</a></p>
  </section>`;
}

function topicsBlock(topics) {
  const rows = topics.filter((x) => x.topic_id !== 'other').slice(0, 8);
  if (!rows.length) return '';
  const max = Math.max(1, ...rows.map((x) => x.articles));
  // A trend line once there are enough collected days; until then, the share of coverage.
  const trend = (x) => sparkline(x.daily)
    || `<span class="bar-track" aria-hidden="true"><span class="bar-fill" style="display:block;width:${(100 * x.articles) / max}%"></span></span>`;
  return `<section aria-labelledby="topics-h">
    <div class="section-head"><h2 class="section-title" id="topics-h">${esc(t('topics_week'))}</h2>
      <a class="more-link" href="#/topics">${esc(t('all_topics'))}</a></div>
    <div class="topic-rows">${rows.map((x) => `
      <a class="topic-row" href="#/topic/${esc(x.topic_id)}">
        <span class="name">${esc(topicName(x.topic_id, x.topic))}</span>
        ${trend(x)}
        <span class="count num">${formatNumber(x.articles)}</span>
      </a>`).join('')}</div>
  </section>`;
}

function keywordsBlock(fr, ar) {
  if (!fr.length && !ar.length) return '';
  const chips = (rows, lang) => `<div class="chips" dir="${lang === 'ar' ? 'rtl' : 'ltr'}">${rows.map((k) => `
    <a class="chip t" lang="${lang}" href="#/search?q=${encodeURIComponent(k.keyword)}">${esc(k.keyword)} <b class="num">${formatNumber(k.mentions)}</b></a>`).join('')}</div>`;
  return `<section aria-labelledby="kw-h">
    <div class="section-head"><h2 class="section-title" id="kw-h">${esc(t('keywords'))}</h2>
      <span class="note">${esc(t('keywords_sub'))}</span></div>
    ${fr.length ? `<p class="note" style="margin-bottom:8px">${esc(languageName('fr'))}</p>${chips(fr, 'fr')}` : ''}
    ${ar.length ? `<p class="note" style="margin:16px 0 8px">${esc(languageName('ar'))}</p>${chips(ar, 'ar')}` : ''}
  </section>`;
}

async function drawActivity(el) {
  const box = el.querySelector('#act-chart');
  if (!box) return;
  let data;
  try {
    data = await get('/activity', { window: activityWindow });
  } catch (err) {
    box.innerHTML = errorBox(err, () => drawActivity(el));
    return;
  }
  if (!el.contains(box)) return;
  const hourly = data.unit === 'hour';
  const points = data.buckets.map((b) => (hourly
    ? { label: formatTime(b.bucket), title: formatDate(b.bucket, { weekday: 'short', hour: '2-digit', minute: '2-digit' }) }
    : { label: formatDay(b.bucket, { day: 'numeric', month: 'short' }), title: formatDay(b.bucket) }));
  const series = [
    { name: languageName('fr'), color: 'var(--fr)', values: data.buckets.map((b) => b.fr) },
    { name: languageName('ar'), color: 'var(--ar)', values: data.buckets.map((b) => b.ar) },
  ];
  // Text summary for screen readers: total and peak.
  const totals = data.buckets.map((b) => (b.fr ?? 0) + (b.ar ?? 0));
  const peak = Math.max(0, ...totals);
  const peakAt = totals.indexOf(peak);
  const summary = t('chart_summary', {
    total: formatNumber(totals.reduce((a, b) => a + b, 0)), peak: formatNumber(peak),
    when: peakAt >= 0 ? points[peakAt].title : '',
  });
  el.querySelector('#act-legend').innerHTML = legend(series);
  lineChart(box, { points, series, height: 180, ariaLabel: `${t(hourly ? 'activity_unit_hour' : 'activity_unit_day')}. ${summary}` });
}
