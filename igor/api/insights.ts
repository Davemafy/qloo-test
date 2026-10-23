import type { IncomingMessage, ServerResponse } from 'http';
export default async function handler(req: IncomingMessage & { method?: string; query?: Record<string,string> }, res: ServerResponse & { setHeader(name:string,value:string):void; statusCode:number; end(data?:string):void }) {
  res.setHeader('Content-Type','application/json; charset=utf-8');
  res.setHeader('Cache-Control','no-store');
  if (req.method !== 'GET') { res.statusCode=405; res.end(JSON.stringify({error:'Use GET'})); return; }
  const key = process.env.QLOO_API_KEY;
  if (!key) { res.statusCode=503; res.end(JSON.stringify({error:'Live mode is not configured yet. Add QLOO_API_KEY to the deployment environment.'})); return; }
  const url = new URL('https://hackathon.api.qloo.com/v2/insights');
  const q = req.query || {};
  const city = String(q.city || 'New York City').slice(0,100);
  const taste = String(q.taste || 'hip_hop').slice(0,100);
  const tag = taste.startsWith('urn:') ? taste : 'urn:tag:genre:music:' + taste.toLowerCase().replace(/[^a-z0-9_ -]/g,'').replace(/[ -]+/g,'_');
  url.searchParams.set('filter.type','urn:entity:place');
  url.searchParams.set('filter.location.query',city);
  url.searchParams.set('filter.location.radius','0');
  url.searchParams.set('signal.interests.tags',tag);
  url.searchParams.set('take','10');
  url.searchParams.set('feature.explainability','true');
  try {
    const upstream = await fetch(url.toString(), {headers:{Authorization:'Bearer '+key,Accept:'application/json'}});
    const body = await upstream.json();
    if (!upstream.ok) { res.statusCode=upstream.status; res.end(JSON.stringify({error:'Qloo request failed',status:upstream.status,details:body})); return; }
    res.statusCode=200; res.end(JSON.stringify({mode:'live',city,taste,results:body?.results?.entities || body?.results || [],warnings:body?.warnings || []}));
  } catch { res.statusCode=502; res.end(JSON.stringify({error:'Could not reach Qloo. Try again shortly.'})); }
}