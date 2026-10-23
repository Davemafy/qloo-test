import type { IncomingMessage, ServerResponse } from 'http';

const ALLOWED_CITIES = new Set([
  'New York City',
  'London',
  'Los Angeles',
  'Tokyo',
  'Lagos',
  'Abuja',
]);
const ALLOWED_TYPES = new Set(['place', 'artist', 'movie', 'tv_show', 'book', 'brand']);
const ALLOWED_TASTES = new Set([
  'hip_hop',
  'indie_rock',
  'jazz',
  'electronic',
  'soul',
]);

export default async function handler(
  req: IncomingMessage & { method?: string; query?: Record<string, string> },
  res: ServerResponse & {
    setHeader(name: string, value: string): void;
    statusCode: number;
    end(data?: string): void;
  },
) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Allow', 'GET');

  if (req.method !== 'GET') {
    res.statusCode = 405;
    res.end(JSON.stringify({ error: 'Use GET' }));
    return;
  }

  // Fail closed: adding an API key alone must not enable billable traffic.
  if (process.env.QLOO_LIVE_ENABLED !== 'true') {
    res.statusCode = 503;
    res.end(JSON.stringify({ error: 'Live recommendations are temporarily disabled.' }));
    return;
  }

  const key = process.env.QLOO_API_KEY;
  if (!key) {
    res.statusCode = 503;
    res.end(JSON.stringify({ error: 'Live mode is not configured.' }));
    return;
  }

  const q = req.query || {};
  const city = String(q.city || 'New York City');
  const taste = String(q.taste || 'hip_hop');
  const type = String(q.type || 'place');

  // Strict allowlists prevent arbitrary upstream query construction.
  if (!ALLOWED_CITIES.has(city)) {
    res.statusCode = 400;
    res.end(JSON.stringify({ error: 'Unsupported city.' }));
    return;
  }
  if (!ALLOWED_TYPES.has(type)) {
    res.statusCode = 400;
    res.end(JSON.stringify({ error: 'Unsupported cultural category.' }));
    return;
  }
  if (!ALLOWED_TASTES.has(taste)) {
    res.statusCode = 400;
    res.end(JSON.stringify({ error: 'Unsupported taste.' }));
    return;
  }

  const url = new URL('https://hackathon.api.qloo.com/v2/insights');
  url.searchParams.set('filter.type', 'urn:entity:' + type);
  if (type === 'place') {
    url.searchParams.set('filter.location.query', city);
    url.searchParams.set('filter.location.radius', '0');
  }
  url.searchParams.set('signal.interests.tags', 'urn:tag:genre:music:' + taste);
  url.searchParams.set('take', '10');
  url.searchParams.set('feature.explainability', 'true');

  try {
    const upstream = await fetch(url.toString(), {
      headers: { Authorization: 'Bearer ' + key, Accept: 'application/json' },
      signal: AbortSignal.timeout(8000),
    });
    if (!upstream.ok) {
      // Do not reflect upstream response bodies or provider details to callers.
      res.statusCode = upstream.status === 429 ? 429 : 502;
      res.end(JSON.stringify({ error: upstream.status === 429 ? 'Recommendation provider is rate-limiting requests.' : 'Recommendation provider request failed.' }));
      return;
    }

    const body = await upstream.json();
    res.statusCode = 200;
    res.end(JSON.stringify({
      mode: 'live',
      city,
      taste,
      type,
      results: body?.results?.entities || body?.results || [],
      warnings: body?.warnings || [],
    }));
  } catch {
    res.statusCode = 502;
    res.end(JSON.stringify({ error: 'Could not reach the recommendation provider. Try again shortly.' }));
  }
}
