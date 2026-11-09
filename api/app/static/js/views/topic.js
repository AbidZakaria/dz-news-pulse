// One topic: daily coverage by language, its vocabulary, who covers it, and its stories.
import { get } from '../api.js';
import { legend, lineChart } from '../charts.js';
import { formatDay, formatNumber, getLang, languageName, plural, t, topicName } from '../i18n.js';
import {
  articleItem, errorBox, esc, icon, monogram, skeleton, sourceName, storyRow, textLang,
} from '../ui.js';

export async function render(el, ctx) {
  const id = ctx.params[0];
  const days = [7, 14, 30].includes(Number(ctx.query.days)) ? Number(ctx.query.days) : 7;
  el.innerHTML = skeleton(10);
  let data;
  try {
    const [topic, stories, latest] = await Promise.all([
      get(`/topics/${encodeURIComponent(id)}`, { days }),
      get('/stories', { topic: id, days, limit: 8 }),
      get('/articles', { topic: id, days, limit: 10 }),
    ]);
    data = { topic, stories, latest };
  } catch (err) {
    if (ctx.isCurrent()) el.innerHTML = errorBox(err, () => render(el, ctx));
    return;
  }
  if (!ctx.isCurrent()) return;

  const { topic, stories, latest } = data;
  const name = topicName(topic.topic_id, topic.topic);
  ctx.setTitle(name);
  const maxShare = Math.max(1, ...topic.sources.map((s) => s.share_pct));

  el.innerHTML = `
    <a class="back-link" href="#/topics">${icon('back', 'icon-sm')}${esc(t('back_topics'))}</a>
    <div class="page-head">
      <div>
        <h1 class="page-title">${esc(name)}</h1>
        <p class="page-sub">${esc(plural('articles', topic.articles))}, ${esc(plural('outlets', topic.sources?.length ?? 0))}${getLang() === 'en' && topic.description ? `. ${esc(topic.description)}` : ''}</p>
      </div>
      <div class="seg" role="group" aria-label="${esc(t('period'))}">
        ${[7, 14, 30].map((d) => `<a href="#/topic/${esc(id)}?days=${d}" aria-current="${d === days}">${esc(t(`period_${d}`))}</a>`).join('')}
      </div>
    </div>
    <div class="layout">
      <div class="col-main">
        <section class="section" aria-labelledby="pd-h">
          <div class="section-head"><h2 class="section-title" id="pd-h">${esc(t('per_day'))}</h2></div>
          <div id="topic-legend"></div>
          <div id="topic-chart" style="min-height:200px"></div>
        </section>
        <section class="section" aria-labelledby="ts-h">
          <div class="section-head"><h2 class="section-title" id="ts-h">${esc(t('topic_stories'))}</h2>
            <a class="more-link" href="#/stories?topic=${esc(id)}&days=30">${esc(t('see_all_stories'))}</a></div>
          ${stories.length ? `<ul class="story-list">${stories.map((s) => storyRow(s)).join('')}</ul>` : `<p class="empty">${esc(t('no_stories'))}</p>`}
        </section>
      </div>
      <aside class="side">
        <section aria-labelledby="who-h">
          <div class="section-head"><h2 class="section-title" id="who-h">${esc(t('topic_sources'))}</h2></div>
          <div style="display:grid;gap:12px">${topic.sources.map((s) => `
            <div style="display:grid;grid-template-columns:26px minmax(0,1fr) 40px;gap:10px;align-items:center">
              ${monogram(s.source_id, s.source_name)}
              <div><div style="font-size:14px">${esc(sourceName(s.source_id, s.source_name))}</div>
                <div class="bar-track" style="margin-top:5px"><div class="bar-fill" style="width:${(100 * s.share_pct) / maxShare}%"></div></div></div>
              <span class="num muted" style="text-align:end;font-size:13px">${formatNumber(s.articles)}</span>
            </div>`).join('')}</div>
        </section>
        ${topic.keywords.length ? `<section aria-labelledby="tk-h">
          <div class="section-head"><h2 class="section-title" id="tk-h">${esc(t('topic_kw'))}</h2></div>
          <div class="chips">${topic.keywords.map((k) => `<a class="chip t" lang="${textLang(k.keyword)}" href="#/search?q=${encodeURIComponent(k.keyword)}">${esc(k.keyword)} <b class="num">${formatNumber(k.mentions)}</b></a>`).join('')}</div>
        </section>` : ''}
        <section aria-labelledby="tl-h">
          <div class="section-head"><h2 class="section-title" id="tl-h">${esc(t('topic_latest'))}</h2></div>
          <ul class="compact">${latest.map(articleItem).join('')}</ul>
        </section>
      </aside>
    </div>`;

  const series = [
    { name: languageName('fr'), color: 'var(--fr)', values: topic.daily.map((d) => d.fr) },
    { name: languageName('ar'), color: 'var(--ar)', values: topic.daily.map((d) => d.ar) },
  ];
  el.querySelector('#topic-legend').innerHTML = legend(series);
  lineChart(el.querySelector('#topic-chart'), {
    points: topic.daily.map((d) => ({ label: formatDay(d.day, { day: 'numeric', month: 'short' }), title: formatDay(d.day) })),
    series,
    height: 200,
    ariaLabel: `${t('per_day')}: ${name}`,
  });
}
