// Sources: each outlet's output and topic mix, and the health of the collection pipeline.
import { get } from '../api.js';
import { formatDate, formatNumber, languageName, t, topicName } from '../i18n.js';
import {
  errorBox, esc, icon, monogram, skeleton, sourceName, timeEl,
} from '../ui.js';

const FOCUS = { general: 'focus_general', economy: 'focus_economy', sport: 'focus_sport' };

export async function render(el, ctx) {
  ctx.setTitle(t('sources_title'));
  el.innerHTML = skeleton(10);
  let data;
  try {
    const [sources, runs] = await Promise.all([get('/sources'), get('/pipeline/runs', { limit: 14 })]);
    data = { sources, runs };
  } catch (err) {
    if (ctx.isCurrent()) el.innerHTML = errorBox(err, () => render(el, ctx));
    return;
  }
  if (!ctx.isCurrent()) return;
  const { sources, runs } = data;
  const names = Object.fromEntries(sources.map((s) => [s.source_id, s.source_name]));

  const status = (value) => (value === 'success'
    ? `<span class="status ok">${icon('check', 'icon-sm')}${esc(t('status_success'))}</span>`
    : `<span class="status bad">${icon('alert', 'icon-sm')}${esc(t('status_failed'))}</span>`);

  el.innerHTML = `
    <div class="page-head"><div>
      <h1 class="page-title">${esc(t('sources_title'))}</h1>
      <p class="page-sub">${esc(t('sources_sub'))}</p>
    </div></div>
    <div class="table-wrap">
      <table class="table">
        <thead><tr>
          <th scope="col">${esc(t('col_outlet'))}</th>
          <th scope="col" class="n">${esc(t('col_articles'))}</th>
          <th scope="col" class="n hide-sm">${esc(t('col_images'))}</th>
          <th scope="col" class="n hide-sm">${esc(t('col_shared'))}</th>
          <th scope="col" class="hide-sm">${esc(t('col_topics'))}</th>
          <th scope="col">${esc(t('col_latest'))}</th>
          <th scope="col">${esc(t('col_feed'))}</th>
        </tr></thead>
        <tbody>${sources.map((s) => `
          <tr>
            <td><div class="src-cell">${monogram(s.source_id, s.source_name, 'mono-lg')}
              <div><a href="${esc(s.website)}" target="_blank" rel="noopener" style="font-weight:600">${esc(sourceName(s.source_id, s.source_name))}</a>
                <small>${esc(languageName(s.language))}, ${esc(t(FOCUS[s.focus] || 'focus_general'))}</small></div></div></td>
            <td class="n">${formatNumber(s.articles)}</td>
            <td class="n hide-sm">${s.articles ? `${formatNumber(Math.round((100 * s.with_image) / s.articles))}%` : '—'}</td>
            <td class="n hide-sm">${formatNumber(s.shared_stories)}</td>
            <td class="hide-sm"><div class="chips">${(s.top_topics || []).filter((x) => x.topic_id !== 'other').slice(0, 3).map((x) => `
              <a class="chip" href="#/topic/${esc(x.topic_id)}">${esc(topicName(x.topic_id, x.topic))} <b class="num">${formatNumber(x.articles)}</b></a>`).join('')}</div></td>
            <td>${timeEl(s.latest_article_at)}</td>
            <td>${s.last_run_status ? status(s.last_run_status) : '—'}</td>
          </tr>`).join('')}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:14px">${esc(t('sources_note'))}</p>

    <section class="section" aria-labelledby="runs-h">
      <div class="section-head"><h2 class="section-title" id="runs-h">${esc(t('runs_title'))}</h2>
        <a class="more-link" href="/docs#/pipeline/pipeline_runs_pipeline_runs_get">${esc(t('api_docs'))}</a></div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr>
            <th scope="col">${esc(t('col_time'))}</th><th scope="col">${esc(t('col_outlet'))}</th>
            <th scope="col">${esc(t('col_status'))}</th><th scope="col" class="n">${esc(t('col_fetched'))}</th>
            <th scope="col" class="n">${esc(t('col_new'))}</th>
          </tr></thead>
          <tbody>${runs.map((r) => `
            <tr>
              <td class="num">${esc(formatDate(r.finished_at, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }))}</td>
              <td>${esc(sourceName(r.source_id, names[r.source_id]))}</td>
              <td title="${esc(r.error || '')}">${status(r.status)}</td>
              <td class="n">${formatNumber(r.fetched_count ?? 0)}</td>
              <td class="n">${formatNumber(r.inserted_count ?? 0)}</td>
            </tr>`).join('')}</tbody>
        </table>
      </div>
      <p class="note" style="margin-top:14px">${esc(t('times_note'))}</p>
    </section>`;
}
