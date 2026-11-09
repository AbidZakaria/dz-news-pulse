// Topics: share of coverage per subject, a daily trend, and an honest comparison with the
// previous period (shown only once that period has been fully collected).
import { get } from '../api.js';
import { sparkline } from '../charts.js';
import { formatDay, formatNumber, t, topicName } from '../i18n.js';
import { changeLabel, errorBox, esc, skeleton } from '../ui.js';

const WINDOWS = [7, 14, 30];

export async function render(el, ctx) {
  ctx.setTitle(t('topics_title'));
  const days = WINDOWS.includes(Number(ctx.query.days)) ? Number(ctx.query.days) : 7;
  el.innerHTML = skeleton(8);
  let rows;
  try {
    rows = await get('/topics', { days });
  } catch (err) {
    if (ctx.isCurrent()) el.innerHTML = errorBox(err, () => render(el, ctx));
    return;
  }
  if (!ctx.isCurrent()) return;

  // "Other" is what no keyword matched: keep it, but last.
  rows.sort((a, b) => (a.topic_id === 'other') - (b.topic_id === 'other'));
  const range = rows.length ? `${formatDay(rows[0].daily_from, { day: 'numeric', month: 'short' })} – ${formatDay(lastDay(rows[0]), { day: 'numeric', month: 'short' })}` : '';
  const noHistory = rows.every((x) => x.prev_articles === null);
  el.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">${esc(t('topics_title'))}</h1>
        <p class="page-sub">${esc(t('topics_sub'))}</p>
      </div>
      <div class="seg" role="group" aria-label="${esc(t('period'))}">
        ${WINDOWS.map((d) => `<a href="#/topics?days=${d}" aria-current="${d === days}">${esc(t(`period_${d}`))}</a>`).join('')}
      </div>
    </div>
    ${range ? `<p class="note" style="margin:-12px 0 18px">${esc(range)}${noHistory ? `. ${esc(t('need_history'))}.` : ''}</p>` : ''}
    <div class="topic-grid">${rows.map((x) => card(x, days)).join('')}</div>
    <p class="note" style="margin-top:28px">${esc(t('topics_note'))}</p>`;
}

function lastDay(row) {
  const d = new Date(`${row.daily_from}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + row.daily.length - 1);
  return d.toISOString().slice(0, 10);
}

function card(x, days) {
  const change = changeLabel(x.articles, x.prev_articles);
  return `
  <a class="topic-card" href="#/topic/${esc(x.topic_id)}">
    <div class="top"><h3>${esc(topicName(x.topic_id, x.topic))}</h3><span class="big num">${formatNumber(x.articles)}</span></div>
    <div class="bar-track" aria-hidden="true"><div class="bar-fill" style="width:${Math.max(1, x.share_pct)}%"></div></div>
    ${sparkline(x.daily, { wide: true })}
    <div class="foot">
      <span>${esc(t('share', { pct: formatNumber(x.share_pct) }))}</span>
      ${change ? `<span>${esc(t('vs_prev', { change, days: formatNumber(days) }))}</span>` : ''}
    </div>
  </a>`;
}
