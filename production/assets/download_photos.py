#!/usr/bin/env python3
import csv, hashlib, io, json, re, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"dist"; PHOTOS=OUT/"photos"
HEAD={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
def get(url):
    r=requests.get(url,headers=HEAD,timeout=22,stream=True)
    r.raise_for_status()
    data=bytearray()
    for c in r.iter_content(262144):
        data.extend(c)
        if len(data)>28000000: raise ValueError("oversize")
    return bytes(data),r
def attempt(row):
    ident,provider,page=row
    candidates=[]
    if provider=="Pexels":
        n=re.search(r"-(\d+)/?$",page).group(1)
        candidates.append(f"https://images.pexels.com/photos/{n}/pexels-photo-{n}.jpeg?auto=compress&cs=tinysrgb&w=2600")
    else:
        ident2=page.split("/")[-1].split("-")[-1]
        try:
            data,r=get("https://unsplash.com/napi/photos/"+ident2)
            obj=json.loads(data)
            for key in ("full","raw","regular"):
                u=obj.get("urls",{}).get(key)
                if u: candidates.append(u+("&" if "?" in u else "?")+"w=2600&q=90")
        except Exception: pass
        candidates.append(page+"/download?force=true&w=2600")
    try:
        html,_=get(page)
        soup=BeautifulSoup(html,"html.parser")
        for key in ("og:image:secure_url","og:image","twitter:image"):
            for tag in soup.find_all("meta",attrs={"property":key})+soup.find_all("meta",attrs={"name":key}):
                u=tag.get("content")
                if u and u.startswith("https://"): candidates.append(u)
    except Exception: pass
    errors=[]
    for url in dict.fromkeys(candidates):
        try:
            data,_=get(url)
            im=Image.open(io.BytesIO(data)); im.load()
            if min(im.size)<550 or max(im.size)<1000: raise ValueError(f"low resolution {im.size}")
            path=PHOTOS/(ident+".jpg")
            im.convert("RGB").save(path,"JPEG",quality=93,optimize=True)
            b=path.read_bytes()
            return {"id":ident,"provider":provider,"page":page,"status":"downloaded","file":"photos/"+path.name,"width":im.width,"height":im.height,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"source_image":url,"error":""}
        except Exception as e: errors.append(str(e)[:120])
    return {"id":ident,"provider":provider,"page":page,"status":"failed","file":"","width":"","height":"","bytes":"","sha256":"","source_image":"","error":" | ".join(errors[-3:]) or "No download candidates"}
def main():
    PHOTOS.mkdir(parents=True,exist_ok=True)
    rows=[tuple(line.strip().split("|",2)) for line in (ROOT/"production/assets/igor-photo-sources.txt").read_text().splitlines() if line.strip() and not line.startswith("#")]
    with ThreadPoolExecutor(max_workers=4) as executor:
        items=sorted((f.result() for f in as_completed([executor.submit(attempt,r) for r in rows])),key=lambda r:r["id"])
    with (OUT/"SOURCES.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
    ok=[x for x in items if x["status"]=="downloaded"]
    report={"total":len(items),"downloaded":len(ok),"failed":len(items)-len(ok),"items":items}
    (OUT/"REPORT.json").write_text(json.dumps(report,indent=2))
    (OUT/"LICENSE_AND_USAGE.txt").write_text("Production reference assets; check individual photographer terms and third-party rights before publication.\nUnsplash: https://unsplash.com/license\nPexels: https://www.pexels.com/license/\nPhotographs must not imply real Igor users, bookings or Qloo-selected venues.\n")
    if ok:
        cell_w,cell_h=420,270
        sheet=Image.new("RGB",(cell_w*4,cell_h*((len(ok)+3)//4)),"#f5f3ee")
        d=ImageDraw.Draw(sheet)
        for i,row in enumerate(ok):
            im=Image.open(OUT/row["file"])
            im=ImageOps.fit(im,(408,235))
            x=(i%4)*cell_w+6;y=(i//4)*cell_h+6
            sheet.paste(im,(x,y));d.text((x+4,y+239),row["id"]+" · "+row["provider"],fill="#202020")
        sheet.save(OUT/"CONTACT_SHEET.jpg",quality=90)
    name=OUT/"IGOR_OutcomeOS_Real_Photos.zip"
    with zipfile.ZipFile(name,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob("*"):
            if p.is_file() and p!=name:z.write(p,p.relative_to(OUT))
    print(f"Downloaded {len(ok)}/{len(items)} photos; packaged {name} ({name.stat().st_size} bytes)")
if __name__=="__main__":main()
