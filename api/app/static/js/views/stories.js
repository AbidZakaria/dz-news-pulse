// Stories: every grouped event, filterable. Filters live in the URL so a view can be shared.
import { get } from '../api.js';
import { languageName, t, TOPIC_IDS, topicName } from '../i18n.js';
import { errorBox, esc, skeleton, storyRow } from '../ui.js';

const PERIODS = { 1: 'period_1', 7: 'period_7', 30: 'period_30' };

export async function render(el, ctx) {
  ctx.setTitle(t('stories_title'));
  const q = {
    days: PERIODS[ctx.query.days] ? Number(ctx.query.days) : 7,
    topic: TOPIC_IDS.includes(ctx.query.topic) ? ctx.query.topic : '',
    language: ['fr', 'ar'].includes(ctx.query.language) ? ctx.query.language : '',
    shared: ctx.query.shared !== '0',
    sort: ctx.query.sort === 'recent' ? 'recent' : 'coverage',
  };

  el.innerHTML = `
    <div class="page-head"><div>
      <h1 class="page-title">${esc(t('stories_title'))}</h1>
      <p class="page-sub">${esc(t('stories_sub'))}</p>
    </div></div>
    <form class="filters" id="story-filters">
      <div class="seg" role="group" aria-label="${esc(t('period'))}">
        ${Object.entries(PERIODS).map(([d, key]) => `<button type="button" name="days" value="${d}" aria-pressed="${Number(d) === q.days}">${esc(t(key))}</button>`).join('')}
      </div>
      <label class="visually-hidden" for="f-topic">${esc(t('topic'))}</label>
      <select class="select" id="f-topic" name="topic">
        <option value="">${esc(t('all_topics_opt'))}</option>
        ${TOPIC_IDS.filter((id) => id !== 'other').map((id) => `<option value="${id}" ${id === q.topic ? 'selected' : ''}>${esc(topicName(id))}</option>`).join('')}
      </select>
      <label class="visually-hidden" for="f-lang">${esc(t('language'))}</label>
      <select class="select" id="f-lang" name="language">
        <option value="">${esc(t('all_langs'))}</option>
        ${['ar', 'fr'].map((l) => `<option value="${l}" ${l === q.language ? 'selected' : ''}>${esc(languageName(l))}</option>`).join('')}
      </select>
      <label class="check"><input type="checkbox" name="shared" ${q.shared ? 'checked' : ''}> ${esc(t('only_shared'))}</label>
      <label class="visually-hidden" for="f-sort">${esc(t('sort'))}</label>
      <select class="select" id="f-sort" name="sort">
        <option value="coverage" ${q.sort === 'coverage' ? 'selected' : ''}>${esc(t('sort_coverage'))}</option>
        <option value="recent" ${q.sort === 'recent' ? 'selected' : ''}>${esc(t('sort_recent'))}</option>
      </select>
    </form>
    <div id="story-results" class="readable">${skeleton(6)}</div>`;

  const form = el.querySelector('#story-filters');
  const update = (patch) => {
    const next = { ...q, ...patch };
    ctx.navigate('/stories', {
      days: next.days === 7 ? '' : next.days, topic: next.topic, language: next.language,
      shared: next.shared ? '' : '0', sort: next.sort === 'coverage' ? '' : next.sort,
    });
  };
  form.addEventListener('click', (e) => {
    const btn = e.target.closest('button[name="days"]');
    if (btn) update({ days: Number(btn.value) });
  });
  form.addEventListener('change', (e) => {
    const { name } = e.target;
    if (name === 'shared') update({ shared: e.target.checked });
    else if (name) update({ [name]: e.target.value });
  });
  form.addEventListener('submit', (e) => e.preventDefault());

  const box = el.querySelector('#story-results');
  try {
    const rows = await get('/stories', {
      days: q.days === 1 ? 2 : q.days, hours: q.days === 1 ? 24 : '',
      topic: q.topic, language: q.language, min_sources: q.shared ? 2 : 1,
      sort: q.sort, limit: 60,
    });
    if (!ctx.isCurrent()) return;
    box.innerHTML = rows.length
      ? `<ul class="story-list">${rows.map((s) => storyRow(s)).join('')}</ul>`
      : `<p class="empty">${esc(t('no_stories'))}</p>`;
  } catch (err) {
    if (ctx.isCurrent()) box.innerHTML = errorBox(err, () => render(el, ctx));
  }
}
