// Interface language: English, French or Arabic (right-to-left).
// The news itself stays in the language it was published in; only the interface changes.

const STRINGS = {
  en: {
    skip: 'Skip to content', api_docs: 'API', search_label: 'Search the news',
    search_placeholder: 'Search headlines and summaries…',
    nav_today: 'Today', nav_briefing: 'Daily briefing', nav_stories: 'Stories', nav_topics: 'Topics',
    nav_search: 'Search', nav_sources: 'Sources',
    menu_open: 'Open menu', menu_close: 'Close menu', theme_to_light: 'Switch to light theme',
    theme_to_dark: 'Switch to dark theme', lang_group: 'Interface language',
    live_updated: 'Last collected {time}', live_every: 'Feeds are read every 6 hours',
    today_sub: '{articles} from {sources} in the last 24 hours, grouped into stories across French and Arabic.',
    stat_articles: 'Articles collected', stat_shared: 'Stories covered by 2+ outlets', stat_sources: 'Outlets',
    stat_topics: 'Topics', delta_24h: '+{n} in the last 24 h', delta_multi: '{n} across both languages',
    delta_sources_ok: 'All feeds collected', delta_sources_bad: '{n} feed failing', delta_topics: 'Keyword-based',
    top_stories: 'Most covered stories', top_stories_sub: 'Last 48 hours, by number of independent outlets',
    see_all_stories: 'See all stories', latest: 'Latest reports', see_search: 'Search all articles',
    in_brief: 'In brief', in_brief_sub: 'What most outlets reported in the last 24 hours',
    open_briefing: 'Open the daily briefing',
    activity: 'Publishing activity', range_24h: '24 h', range_7d: '7 days', range_30d: '30 days',
    activity_unit_hour: 'Articles per hour', activity_unit_day: 'Articles per day',
    not_collected: 'Not collected yet', chart_summary: '{total} articles in this period, peak of {peak} on {when}.',
    topics_week: 'Topics this week', all_topics: 'All topics', keywords: 'Most used words', keywords_sub: 'Last 3 days',
    first_by: 'First: {source}', lang_fr: 'French', lang_ar: 'Arabic', lang_en: 'English',
    back_stories: 'All stories', fact_outlets: 'Independent outlets', fact_articles: 'Articles',
    fact_first: 'First reported', fact_span: 'Covered over', coverage: 'Coverage, in order of publication',
    flag_first: 'First to report', flag_copy: 'Copy of another outlet’s text', flag_lower: 'Lower-confidence match',
    open_original: 'Open the original article', also_in: 'In {lang}',
    method_title: 'How this story was grouped',
    method_text: 'Articles are grouped by meaning (multilingual sentence embeddings), shared names and words, and publication time. Average similarity {avg}. Copies of another outlet’s text are flagged and not counted as independent coverage.',
    stories_title: 'Stories',
    stories_sub: 'Articles about the same event, grouped automatically across outlets and languages.',
    period: 'Period', period_1: '24 hours', period_7: '7 days', period_14: '14 days', period_30: '30 days',
    view_story: 'View story',
    topic: 'Topic', all_topics_opt: 'All topics', language: 'Language', all_langs: 'All languages',
    only_shared: 'Covered by 2+ outlets', sort: 'Sort', sort_coverage: 'Widest coverage', sort_recent: 'Most recent',
    no_stories: 'No stories match these filters. Try a longer period or remove a filter.',
    briefing_title: 'Daily briefing', prev_day: 'Previous day', next_day: 'Next day',
    brief_summary: '{articles} from {sources}: {ar} in Arabic, {fr} in French.',
    brief_topics: 'Main topics', brief_top: 'Most covered stories', brief_also: 'Also reported',
    brief_note: 'Headlines and summaries are the outlets’ own words. Nothing on this page is written by a model.',
    brief_empty: 'No story was covered by two or more outlets on this day.',
    topics_title: 'Topics',
    topics_sub: 'How much coverage each subject gets, from keywords in headlines and summaries.',
    vs_prev: '{change} vs the previous {days} days', need_history: 'Comparison appears once a full previous period is collected',
    share: '{pct}% of articles',
    topics_note: 'Counts reflect each outlet’s feed. DzFoot publishes only football, so Sports is larger than in general news.',
    back_topics: 'All topics', per_day: 'Articles per day', topic_kw: 'Words used most in this topic',
    topic_sources: 'Who covers it', topic_stories: 'Stories in this topic', topic_latest: 'Latest articles',
    search_title: 'Search',
    search_sub: 'Searches headlines and summaries in French and Arabic. Accents and Arabic letter forms are ignored.',
    search_button: 'Search', results: '{articles} found',
    no_results: 'Nothing matches “{q}”. Check the spelling or try fewer words.',
    try_words: 'Try one of this week’s most used words', part_of_story: 'Part of a story covered by {outlets}',
    sources_title: 'Sources', sources_sub: 'The outlets collected, what they publish most and how their feeds are doing.',
    col_outlet: 'Outlet', col_articles: 'Articles', col_images: 'With image', col_shared: 'Shared stories',
    col_topics: 'Main topics', col_latest: 'Latest article', col_feed: 'Last collection',
    status_success: 'Collected', status_failed: 'Failed', runs_title: 'Recent collection runs', col_time: 'Time',
    col_status: 'Status', col_fetched: 'Read', col_new: 'New',
    sources_note: 'Counts cover what each RSS feed exposes, not everything an outlet publishes.',
    focus_general: 'General news', focus_economy: 'Economy', focus_sport: 'Sport',
    error_title: 'This page could not be loaded.', retry: 'Try again', error_detail: 'The API answered: {msg}',
    loading: 'Loading…', not_found: 'This page does not exist.', go_home: 'Go to today’s news',
    times_note: 'Times are Algiers time.',
    plural: {
      articles: { one: '1 article', other: '{n} articles' },
      outlets: { one: '1 outlet', other: '{n} outlets' },
    },
  },

  fr: {
    skip: 'Aller au contenu', api_docs: 'API', search_label: 'Rechercher dans l’actualité',
    search_placeholder: 'Rechercher dans les titres et résumés…',
    nav_today: 'Aujourd’hui', nav_briefing: 'L’essentiel du jour', nav_stories: 'Sujets', nav_topics: 'Thèmes',
    nav_search: 'Recherche', nav_sources: 'Sources',
    menu_open: 'Ouvrir le menu', menu_close: 'Fermer le menu', theme_to_light: 'Passer au thème clair',
    theme_to_dark: 'Passer au thème sombre', lang_group: 'Langue de l’interface',
    live_updated: 'Dernière collecte {time}', live_every: 'Les flux sont lus toutes les 6 heures',
    today_sub: '{articles} de {sources} ces dernières 24 heures, regroupés en sujets en français et en arabe.',
    stat_articles: 'Articles collectés', stat_shared: 'Sujets couverts par 2+ sources', stat_sources: 'Sources',
    stat_topics: 'Thèmes', delta_24h: '+{n} ces dernières 24 h', delta_multi: '{n} dans les deux langues',
    delta_sources_ok: 'Tous les flux collectés', delta_sources_bad: '{n} flux en échec', delta_topics: 'Par mots-clés',
    top_stories: 'Sujets les plus couverts', top_stories_sub: '48 dernières heures, par nombre de sources indépendantes',
    see_all_stories: 'Voir tous les sujets', latest: 'Dernières dépêches', see_search: 'Rechercher dans tous les articles',
    in_brief: 'En bref', in_brief_sub: 'Ce que la plupart des médias ont couvert ces dernières 24 heures',
    open_briefing: 'Lire l’essentiel du jour',
    activity: 'Activité de publication', range_24h: '24 h', range_7d: '7 jours', range_30d: '30 jours',
    activity_unit_hour: 'Articles par heure', activity_unit_day: 'Articles par jour',
    not_collected: 'Pas encore collecté', chart_summary: '{total} articles sur la période, pic de {peak} le {when}.',
    topics_week: 'Thèmes de la semaine', all_topics: 'Tous les thèmes', keywords: 'Mots les plus utilisés',
    keywords_sub: '3 derniers jours',
    first_by: 'En premier : {source}', lang_fr: 'Français', lang_ar: 'Arabe', lang_en: 'Anglais',
    back_stories: 'Tous les sujets', fact_outlets: 'Sources indépendantes', fact_articles: 'Articles',
    fact_first: 'Premier article', fact_span: 'Couvert pendant', coverage: 'La couverture, dans l’ordre de publication',
    flag_first: 'Premier à publier', flag_copy: 'Reprise du texte d’un autre média', flag_lower: 'Rapprochement moins sûr',
    open_original: 'Ouvrir l’article d’origine', also_in: 'En {lang}',
    method_title: 'Comment ce sujet a été constitué',
    method_text: 'Les articles sont regroupés selon leur sens (représentations multilingues), les noms et mots partagés et la date de publication. Similarité moyenne {avg}. Les reprises du texte d’un autre média sont signalées et ne comptent pas comme une couverture indépendante.',
    stories_title: 'Sujets',
    stories_sub: 'Les articles qui traitent du même événement, regroupés automatiquement entre médias et langues.',
    period: 'Période', period_1: '24 heures', period_7: '7 jours', period_14: '14 jours', period_30: '30 jours',
    view_story: 'Voir le sujet',
    topic: 'Thème', all_topics_opt: 'Tous les thèmes', language: 'Langue', all_langs: 'Toutes les langues',
    only_shared: 'Couverts par 2+ sources', sort: 'Tri', sort_coverage: 'Plus large couverture', sort_recent: 'Plus récents',
    no_stories: 'Aucun sujet ne correspond. Élargissez la période ou retirez un filtre.',
    briefing_title: 'L’essentiel du jour', prev_day: 'Jour précédent', next_day: 'Jour suivant',
    brief_summary: '{articles} de {sources} : {ar} en arabe, {fr} en français.',
    brief_topics: 'Thèmes principaux', brief_top: 'Sujets les plus couverts', brief_also: 'Également publié',
    brief_note: 'Les titres et résumés sont ceux des médias. Rien sur cette page n’est rédigé par un modèle.',
    brief_empty: 'Aucun sujet n’a été couvert par deux sources ou plus ce jour-là.',
    topics_title: 'Thèmes',
    topics_sub: 'La place de chaque thème dans l’actualité, d’après les mots-clés des titres et résumés.',
    vs_prev: '{change} par rapport aux {days} jours précédents',
    need_history: 'La comparaison apparaîtra quand une période complète aura été collectée',
    share: '{pct} % des articles',
    topics_note: 'Les chiffres reflètent le flux de chaque média. DzFoot ne publie que du football, le Sport y pèse donc plus que dans l’actualité générale.',
    back_topics: 'Tous les thèmes', per_day: 'Articles par jour', topic_kw: 'Mots les plus utilisés dans ce thème',
    topic_sources: 'Qui le couvre', topic_stories: 'Sujets de ce thème', topic_latest: 'Derniers articles',
    search_title: 'Recherche',
    search_sub: 'Recherche dans les titres et résumés, en français et en arabe. Les accents et les variantes de lettres arabes sont ignorés.',
    search_button: 'Rechercher', results: 'Résultats : {articles}',
    no_results: 'Aucun résultat pour « {q} ». Vérifiez l’orthographe ou essayez moins de mots.',
    try_words: 'Essayez un des mots les plus utilisés cette semaine',
    part_of_story: 'Fait partie d’un sujet couvert par {outlets}',
    sources_title: 'Sources', sources_sub: 'Les médias collectés, ce qu’ils publient le plus et l’état de leurs flux.',
    col_outlet: 'Média', col_articles: 'Articles', col_images: 'Avec image', col_shared: 'Sujets partagés',
    col_topics: 'Thèmes principaux', col_latest: 'Dernier article', col_feed: 'Dernière collecte',
    status_success: 'Collecté', status_failed: 'Échec', runs_title: 'Dernières collectes', col_time: 'Heure',
    col_status: 'État', col_fetched: 'Lus', col_new: 'Nouveaux',
    sources_note: 'Les chiffres couvrent ce que publie chaque flux RSS, pas toute la production d’un média.',
    focus_general: 'Généraliste', focus_economy: 'Économie', focus_sport: 'Sport',
    error_title: 'Impossible de charger cette page.', retry: 'Réessayer', error_detail: 'Réponse de l’API : {msg}',
    loading: 'Chargement…', not_found: 'Cette page n’existe pas.', go_home: 'Voir l’actualité du jour',
    times_note: 'Heures d’Alger.',
    plural: {
      articles: { one: '1 article', other: '{n} articles' },
      outlets: { one: '1 source', other: '{n} sources' },
    },
  },

  ar: {
    skip: 'انتقل إلى المحتوى', api_docs: 'واجهة API', search_label: 'ابحث في الأخبار',
    search_placeholder: 'ابحث في العناوين والملخصات…',
    nav_today: 'اليوم', nav_briefing: 'الموجز اليومي', nav_stories: 'القصص', nav_topics: 'المواضيع',
    nav_search: 'بحث', nav_sources: 'المصادر',
    menu_open: 'فتح القائمة', menu_close: 'إغلاق القائمة', theme_to_light: 'التبديل إلى الوضع الفاتح',
    theme_to_dark: 'التبديل إلى الوضع الداكن', lang_group: 'لغة الواجهة',
    live_updated: 'آخر جمع {time}', live_every: 'تُقرأ الخلاصات كل 6 ساعات',
    today_sub: '{articles} من {sources} خلال آخر 24 ساعة، مجمّعة في قصص بالعربية والفرنسية.',
    stat_articles: 'المقالات المجمّعة', stat_shared: 'قصص غطّاها مصدران أو أكثر', stat_sources: 'المصادر',
    stat_topics: 'المواضيع', delta_24h: '+{n} خلال آخر 24 ساعة', delta_multi: '{n} باللغتين',
    delta_sources_ok: 'جُمعت كل الخلاصات', delta_sources_bad: 'خلاصات متعثرة: {n}', delta_topics: 'حسب الكلمات المفتاحية',
    top_stories: 'القصص الأكثر تغطية', top_stories_sub: 'آخر 48 ساعة، حسب عدد المصادر المستقلة',
    see_all_stories: 'كل القصص', latest: 'آخر الأخبار', see_search: 'البحث في كل المقالات',
    in_brief: 'باختصار', in_brief_sub: 'ما نشرته أغلب المصادر خلال آخر 24 ساعة',
    open_briefing: 'قراءة الموجز اليومي',
    activity: 'نشاط النشر', range_24h: '24 س', range_7d: '7 أيام', range_30d: '30 يومًا',
    activity_unit_hour: 'المقالات في الساعة', activity_unit_day: 'المقالات في اليوم',
    not_collected: 'لم تُجمع بعد', chart_summary: 'المقالات في هذه الفترة: {total}، والذروة {peak} يوم {when}.',
    topics_week: 'مواضيع الأسبوع', all_topics: 'كل المواضيع', keywords: 'الكلمات الأكثر استخدامًا',
    keywords_sub: 'آخر 3 أيام',
    first_by: 'الأول: {source}', lang_fr: 'الفرنسية', lang_ar: 'العربية', lang_en: 'الإنجليزية',
    back_stories: 'كل القصص', fact_outlets: 'مصادر مستقلة', fact_articles: 'المقالات',
    fact_first: 'أول نشر', fact_span: 'مدة التغطية', coverage: 'التغطية حسب ترتيب النشر',
    flag_first: 'أول من نشر', flag_copy: 'نسخة من نص مصدر آخر', flag_lower: 'تطابق أقل ثقة',
    open_original: 'فتح المقال الأصلي', also_in: 'بـ{lang}',
    method_title: 'كيف جُمعت هذه القصة',
    method_text: 'تُجمع المقالات حسب المعنى (تمثيلات دلالية متعددة اللغات)، والأسماء والكلمات المشتركة، ووقت النشر. متوسط التشابه {avg}. يُشار إلى النسخ المنقولة عن نص مصدر آخر ولا تُحتسب تغطيةً مستقلة.',
    stories_title: 'القصص',
    stories_sub: 'مقالات تتناول الحدث نفسه، مجمّعة تلقائيًا عبر المصادر واللغات.',
    period: 'الفترة', period_1: '24 ساعة', period_7: '7 أيام', period_14: '14 يومًا', period_30: '30 يومًا',
    view_story: 'عرض القصة',
    topic: 'الموضوع', all_topics_opt: 'كل المواضيع', language: 'اللغة', all_langs: 'كل اللغات',
    only_shared: 'غطّاها مصدران أو أكثر', sort: 'الترتيب', sort_coverage: 'الأوسع تغطية', sort_recent: 'الأحدث',
    no_stories: 'لا توجد قصص مطابقة. جرّب فترة أطول أو أزل أحد الخيارات.',
    briefing_title: 'الموجز اليومي', prev_day: 'اليوم السابق', next_day: 'اليوم التالي',
    brief_summary: '{articles} من {sources}: {ar} بالعربية و{fr} بالفرنسية.',
    brief_topics: 'المواضيع الرئيسية', brief_top: 'القصص الأكثر تغطية', brief_also: 'أخبار أخرى',
    brief_note: 'العناوين والملخصات بكلمات المصادر نفسها. لا شيء في هذه الصفحة كتبه نموذج آلي.',
    brief_empty: 'لم يغطِّ مصدران أو أكثر أي قصة في هذا اليوم.',
    topics_title: 'المواضيع',
    topics_sub: 'حجم التغطية لكل موضوع، حسب الكلمات المفتاحية في العناوين والملخصات.',
    vs_prev: '{change} مقارنة بالفترة السابقة ({days} أيام)',
    need_history: 'تظهر المقارنة بعد جمع فترة سابقة كاملة',
    share: '{pct}% من المقالات',
    topics_note: 'الأرقام تعكس خلاصة كل مصدر. موقع DzFoot لا ينشر إلا كرة القدم، لذلك تبدو الرياضة أكبر مما هي عليه في الأخبار العامة.',
    back_topics: 'كل المواضيع', per_day: 'المقالات يوميًا', topic_kw: 'الكلمات الأكثر استخدامًا في هذا الموضوع',
    topic_sources: 'من يغطيه', topic_stories: 'قصص في هذا الموضوع', topic_latest: 'أحدث المقالات',
    search_title: 'بحث',
    search_sub: 'يبحث في العناوين والملخصات بالفرنسية والعربية، مع تجاهل الحركات واختلاف أشكال الحروف.',
    search_button: 'ابحث', results: 'النتائج: {articles}',
    no_results: 'لا نتائج لـ«{q}». تحقّق من الإملاء أو جرّب كلمات أقل.',
    try_words: 'جرّب إحدى الكلمات الأكثر استخدامًا هذا الأسبوع', part_of_story: 'ضمن قصة غطّاها {outlets}',
    sources_title: 'المصادر', sources_sub: 'المصادر التي تُجمع، وما تنشره أكثر، وحالة خلاصاتها.',
    col_outlet: 'المصدر', col_articles: 'المقالات', col_images: 'مع صورة', col_shared: 'قصص مشتركة',
    col_topics: 'المواضيع الرئيسية', col_latest: 'آخر مقال', col_feed: 'آخر جمع',
    status_success: 'تمّ الجمع', status_failed: 'فشل', runs_title: 'آخر عمليات الجمع', col_time: 'الوقت',
    col_status: 'الحالة', col_fetched: 'المقروءة', col_new: 'الجديدة',
    sources_note: 'الأرقام تخص ما تعرضه خلاصة RSS لكل مصدر، لا كل ما ينشره.',
    focus_general: 'أخبار عامة', focus_economy: 'اقتصاد', focus_sport: 'رياضة',
    error_title: 'تعذّر تحميل هذه الصفحة.', retry: 'إعادة المحاولة', error_detail: 'ردّ الواجهة: {msg}',
    loading: 'جارٍ التحميل…', not_found: 'هذه الصفحة غير موجودة.', go_home: 'العودة إلى أخبار اليوم',
    times_note: 'الأوقات بتوقيت الجزائر.',
    plural: {
      articles: {
        zero: 'لا مقالات', one: 'مقال واحد', two: 'مقالان', few: '{n} مقالات', many: '{n} مقالًا', other: '{n} مقال',
      },
      outlets: {
        zero: 'لا مصادر', one: 'مصدر واحد', two: 'مصدران', few: '{n} مصادر', many: '{n} مصدرًا', other: '{n} مصدر',
      },
    },
  },
};

// Topic names come from the topics seed (dbt/seeds/topics.csv); the API returns ids.
const TOPICS = {
  politics: ['Politics & Government', 'Politique & Gouvernement', 'السياسة والحكومة'],
  economy: ['Economy & Energy', 'Économie & Énergie', 'الاقتصاد والطاقة'],
  sports: ['Sports', 'Sport', 'رياضة'],
  security: ['Security & Justice', 'Sécurité & Justice', 'الأمن والعدالة'],
  health: ['Health', 'Santé', 'الصحة'],
  society: ['Society & Education', 'Société & Éducation', 'المجتمع والتعليم'],
  culture: ['Culture & Media', 'Culture & Médias', 'الثقافة والإعلام'],
  international: ['International', 'International', 'دولي'],
  tech: ['Science & Technology', 'Science & Technologie', 'العلوم والتكنولوجيا'],
  transport: ['Transport & Infrastructure', 'Transport & Infrastructures', 'النقل والبنية التحتية'],
  weather: ['Weather & Environment', 'Météo & Environnement', 'الطقس والبيئة'],
  other: ['Other', 'Autre', 'أخرى'],
};
export const TOPIC_IDS = Object.keys(TOPICS);

const LOCALES = { en: 'en-GB', fr: 'fr-FR', ar: 'ar-DZ' };
const LANGS = ['en', 'fr', 'ar'];
const TZ = 'Africa/Algiers';

function initialLang() {
  const fromUrl = new URLSearchParams(location.search).get('lang');   // shareable: /?lang=ar
  if (LANGS.includes(fromUrl)) return fromUrl;
  try {
    const saved = localStorage.getItem('dz.lang');
    if (LANGS.includes(saved)) return saved;
  } catch (_) { /* storage blocked */ }
  for (const l of navigator.languages || []) {
    const short = l.slice(0, 2).toLowerCase();
    if (LANGS.includes(short)) return short;
  }
  return 'en';
}

let lang = initialLang();

export const getLang = () => lang;
export const locale = () => LOCALES[lang];
export const isRtl = () => lang === 'ar';

export function setLang(next) {
  if (!LANGS.includes(next)) return;
  lang = next;
  try { localStorage.setItem('dz.lang', next); } catch (_) { /* storage blocked */ }
  applyDocumentLang();
}

export function applyDocumentLang() {
  document.documentElement.lang = lang;
  document.documentElement.dir = isRtl() ? 'rtl' : 'ltr';
}

function fill(text, vars) {
  return text.replace(/\{(\w+)\}/g, (_, k) => (vars && k in vars ? vars[k] : `{${k}}`));
}

export function t(key, vars) {
  const text = STRINGS[lang][key] ?? STRINGS.en[key] ?? key;
  return fill(text, vars);
}

const pluralRules = {};
export function plural(key, n) {
  pluralRules[lang] ??= new Intl.PluralRules(LOCALES[lang]);
  const forms = STRINGS[lang].plural[key];
  const form = forms[pluralRules[lang].select(n)] ?? forms.other;
  return fill(form, { n: formatNumber(n) });
}

export function topicName(id, fallback) {
  const names = TOPICS[id];
  if (!names) return fallback || id || '';
  return names[LANGS.indexOf(lang)];
}

export function languageName(code) {
  return t(`lang_${code}`);
}

// ---- numbers, dates and times (Algiers time, the outlets' own clock) ----
export function formatNumber(n, opts) {
  return new Intl.NumberFormat(LOCALES[lang], opts).format(n);
}

export function formatDate(value, opts = { weekday: 'long', day: 'numeric', month: 'long' }) {
  return new Intl.DateTimeFormat(LOCALES[lang], { timeZone: TZ, ...opts }).format(new Date(value));
}

export function formatTime(value) {
  return new Intl.DateTimeFormat(LOCALES[lang], { timeZone: TZ, hour: '2-digit', minute: '2-digit' })
    .format(new Date(value));
}

// A calendar day ('2026-11-09') shown as a date, without shifting it through time zones.
export function formatDay(day, opts = { weekday: 'long', day: 'numeric', month: 'long' }) {
  return new Intl.DateTimeFormat(LOCALES[lang], { timeZone: 'UTC', ...opts })
    .format(new Date(`${day}T12:00:00Z`));
}

export function timeAgo(value, now = Date.now()) {
  const seconds = (new Date(value).getTime() - now) / 1000;
  const rtf = new Intl.RelativeTimeFormat(LOCALES[lang], { numeric: 'auto', style: 'short' });
  const abs = Math.abs(seconds);
  if (abs < 60) return rtf.format(0, 'minute');
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute');
  if (abs < 86400) return rtf.format(Math.round(seconds / 3600), 'hour');
  if (abs < 86400 * 30) return rtf.format(Math.round(seconds / 86400), 'day');
  return formatDate(value, { day: 'numeric', month: 'short', year: 'numeric' });
}

export function formatDuration(ms) {
  const hours = ms / 3600000;
  const unit = hours < 48 ? 'hour' : 'day';
  const value = unit === 'hour' ? Math.max(1, Math.round(hours)) : Math.round(hours / 24);
  return new Intl.NumberFormat(LOCALES[lang], { style: 'unit', unit, unitDisplay: 'long' }).format(value);
}

export function translateStatic(root = document) {
  root.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
}
