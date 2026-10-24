"""Bounded public-safe place discovery probe; no private application imports."""
import json, os
from pathlib import Path
from gathering_probe import Harness, rows, now

def main():
    h=Harness()
    report={"at":now(),"scope":"Three cultural place queries and one reverse place-to-artist query. No LLM calls. Not a travel or dining outcome study.","status":"blocked","cases":[]}
    try:
        seeds={"Radiohead":"70CAE5BF-2F4C-445C-A3E5-4EDACFC3591C","Kendrick Lamar":"C915A918-39C5-47A3-A101-D9FA1DECBD9C"}
        for city,artist in [("Tokyo","Radiohead"),("Tokyo","Kendrick Lamar"),("Amsterdam","Radiohead")]:
            if h.qloo_calls>=4:raise ValueError("request_cap")
            params={"filter.type":"urn:entity:place","signal.interests.entities":seeds[artist],"filter.location.query":city,"filter.location.radius":"0","feature.explainability":"true","take":"10"}
            body=h.qloo("/v2/insights",params)
            entities=rows(body)
            case={"city":city,"artist":artist,"ids":[x["entity_id"] for x in entities],"count":len(entities),"locality":body.get("query",{}).get("locality")}
            report["cases"].append(case)
            if not entities:raise ValueError("empty_places")
        place=report["cases"][0]["ids"][0]
        body=h.qloo("/v2/insights",{"filter.type":"urn:entity:artist","signal.interests.entities":place,"feature.explainability":"true","take":"10"})
        report["reverse"]={"seed_place_id":place,"artist_ids":[x["entity_id"] for x in rows(body)]}
        a,b,c=[set(x["ids"]) for x in report["cases"]]
        report["overlap"]={"taste_intersection":len(a&b),"taste_jaccard":len(a&b)/len(a|b),"city_intersection":len(a&c)}
        report["status"]="executed"
        report["limitations"]=["Seed IDs came from earlier verified API responses.","Location matching must be inspected in raw query metadata.","Place-to-artist is not proof of restaurant-atmosphere compatibility.","Prices, access, travel times and availability remain unknown."]
    except Exception as e:report["error"]=str(e)[:150]
    report.update(qloo_requests=h.qloo_calls,model_requests=h.model_calls,qloo_records=h.records)
    raw=json.dumps(report,indent=2)
    for name in ("QLOO_API_KEY","GEMINI_API_KEY"):
        if os.environ.get(name):raw=raw.replace(os.environ[name],"[REDACTED]")
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/place-probe.json").write_text(raw)
    print(json.dumps({"status":report["status"],"qloo_requests":h.qloo_calls,"model_requests":h.model_calls}))
    return 0 if report["status"]=="executed" else 1
if __name__=="__main__":raise SystemExit(main())
