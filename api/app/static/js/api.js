// Thin client for the FastAPI endpoints, with a short-lived cache so moving between pages
// (and back) does not refetch what is already on screen.

const cache = new Map();
const TTL_MS = 60_000;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export function qs(params) {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '' && v !== false) search.set(k, v);
  }
  const s = search.toString();
  return s ? `?${s}` : '';
}

export async function get(path, params = {}) {
  const url = path + qs(params);
  const hit = cache.get(url);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.data;
  let response;
  try {
    response = await fetch(url, { headers: { Accept: 'application/json' } });
  } catch (_) {
    throw new ApiError('The API cannot be reached. Is the stack running?', 0);
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : response.statusText;
    throw new ApiError(detail, response.status);
  }
  cache.set(url, { at: Date.now(), data: body });
  return body;
}
