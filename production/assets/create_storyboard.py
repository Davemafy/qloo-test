#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json, math, zipfile
P=Path(__file__).resolve().parents[2]; OUT=P/'dist'/'storyboard'; FRAME=OUT/'frames'; PLATE=OUT/'photo_plates'
FRAME.mkdir(parents=True,exist_ok=True);PLATE.mkdir(parents=True,exist_ok=True)
W,H=1920,1080; E='#F3F1EA'; WH='#FCFAF5'; INK='#181A18'; MUT='#60635E'; LINE='#C9C8BF'; ACC='#B3543C'; D='#171A18'
font_candidates=['/usr/share/fonts/truetype/lato/Lato-Regular.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
bold_candidates=['/usr/share/fonts/truetype/lato/Lato-Bold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
F=next(x for x in font_candidates if Path(x).exists());B=next(x for x in bold_candidates if Path(x).exists())
def font(s,b=False):return ImageFont.truetype(B if b else F,s)
def canvas(bg=E):return Image.new('RGB',(W,H),bg)
def photo(im,i,box,focus=(.5,.5)):
    x,y,w,h=map(int,box);q=Image.open(P/'dist'/'photos'/f'A{i:02d}.jpg').convert('RGB')
    z=max(w/q.width,h/q.height);nw,nh=round(q.width*z),round(q.height*z)
    q=q.resize((nw,nh),Image.Resampling.LANCZOS)
    dx=round((nw-w)*focus[0]);dy=round((nh-h)*focus[1])
    im.paste(q.crop((dx,dy,dx+w,dy+h)),(x,y))
def block(im,bg,box):ImageDraw.Draw(im).rectangle(box,fill=bg)
def line(im,x1,y1,x2,y2,col=LINE,width=2):ImageDraw.Draw(im).line((x1,y1,x2,y2),fill=col,width=width)
def txt(im,s,x,y,size=45,color=INK,b=False,spacing=13):
    ImageDraw.Draw(im).multiline_text((x,y),s,fill=color,font=font(size,b),spacing=spacing)
def label(im,s,x=89,y=54,color=INK):txt(im,s,x,y,21,color,True)
def rule(im,color=LINE):line(im,90,1010,1830,1010,color,2)
def save(i,im,plate,scenes): 
    im.save(FRAME/f'{i:02d}.jpg',quality=91,subsampling=0)
    plate.save(PLATE/f'{i:02d}_CLEAN.jpg',quality=92,subsampling=0)
    print('frame',i,flush=True)
def scene(i,title,time,ids,motion,method,vo,verification=''):
    return {'no':i,'title':title,'timecode':time,'photos':['A%02d'%v for v in ids],
            'motion':motion,'production_method':method,'voiceover':vo,'verification':verification,
            'frame':'frames/%02d.jpg'%i,'veo_photo_plate':'photo_plates/%02d_CLEAN.jpg'%i}
S=[]
# 01: Krea-like visual multiplicity, thirty-four actual images, one composition
a=canvas();cols=9;ids=list(range(1,35));cw=round(W/cols);rh=round(H/4)
for j,n in enumerate(ids):
    x=(j%cols)*cw;y=(j//cols)*rh
    photo(a,n,(x,y,cw-5,rh-5))
plate=a.copy()
block(a,WH,(380,347,1530,732))
label(a,'IGOR   /   EVERY OUTCOME BEGINS SOMEWHERE',463,393)
txt(a,'Possibilities.',458,456,125,INK,True)
line(a,461,641,1446,641)
txt(a,'The world offers infinite options. What fits?',465,671,31)
save(1,a,plate,S)
S.append(scene(1,'The abundance of choice','00:00–00:06',ids,
    'Begin 100% cropped inside one source photograph. Pull back through a dense matrix of 34 actual images, ending on an editorial typographic panel. The exact image positions are supplied in the plate.',
    'COMPOSITING / 2.5D IMAGE WALL','There is no shortage of possibilities.'))
# 02: collapse to three photographs, no fake AI
a=canvas(WH);photo(a,7,(0,0,1020,H));photo(a,13,(1028,0,892,331));photo(a,10,(1028,338,892,742),(.5,.23));plate=a.copy()
block(a,WH,(62,720,987,987));txt(a,'But which',105,747,84,b=True);txt(a,'feels right?',105,842,84,b=True);save(2,a,plate,S)
S.append(scene(2,'From more to meaningful','00:06–00:12',[7,13,10],
    'The 34-image wall collapses to three choices. On the downbeat, the Tokyo photo locks to the left edge and the other two fall into precise vertical crops.',
    'COMPOSITING','But finding what truly fits—that is harder.'))
# 03: brand typography with physical fabric texture
a=canvas(WH);photo(a,3,(800,0,1120,H));photo(a,33,(1543,0,377,H));block(a,WH,(0,0,812,H));plate=a.copy()
label(a,'INTRODUCING  /  YOUR CULTURAL AGENT');txt(a,'Igor.',97,271,173,b=True);txt(a,'Your agent with taste.',103,552,53)
line(a,101,686,708,686);label(a,'OUTCOMEOS',103,725,ACC);txt(a,'One conversation. Connected results.',104,773,28)
save(3,a,plate,S)
S.append(scene(3,'Meet Igor','00:12–00:17',[3,33],
    'The exact real translucent curtain moves across the lens. The image resolves into warm paper and precise typographic brand architecture. No glowing particles.',
    'VEO on the source curtain image; vector typography overlaid','Meet Igor. Your agent with taste.'))
# 04: user intent, isolated simple input
a=canvas(WH);photo(a,19,(1156,0,182,H));photo(a,11,(1347,0,573,H));plate=a.copy()
label(a,'IGOR  /  ONE CONVERSATION');txt(a,'One intention.',92,230,94,b=True);txt(a,'No maze of tools.',97,353,55,color=MUT)
block(a,'#FFFFFF',(96,535,1064,755));line(a,96,535,1064,535);line(a,96,755,1064,755)
txt(a,'Help me plan a thoughtful surprise',141,572,33);txt(a,'for someone who loves cinema and jazz.',141,625,33)
txt(a,'DISCOVER  /  EVALUATE  /  PLAN  /  COMPOSE',102,829,21,MUT,True)
save(4,a,plate,S)
S.append(scene(4,'A single request','00:17–00:25',[11,19],
    'A cursor enters a single input; no menu or multi-agent router appears. Real vinyl and books hold the emotional context.',
    'ACTUAL IGOR UI ANIMATION','Tell Igor what you want to make happen.','Replace conceptual input with actual screen recording.'))
# 05: cross-category taste, three physical images
a=canvas(WH);photo(a,13,(58,67,543,750));photo(a,10,(612,67,543,750),(.5,.24));photo(a,20,(1166,67,693,750),(.5,.62));plate=a.copy()
label(a,'FILM',73,838);label(a,'MUSIC',626,838);label(a,'BOOKS',1180,838)
line(a,73,920,1850,920);txt(a,'Culture connects what people love.',75,935,46,b=True)
save(5,a,plate,S)
S.append(scene(5,'Cultural intelligence','00:25–00:32',[13,10,20],
    'Projector lens rotates into the vinyl groove, then passes into the circular grain of an open book. Three hard-edged photo windows remain geometrically stable.',
    'MOTION DESIGN + genuine Qloo evidence','It understands the connections across culture.','Only assert Qloo relationships supported by actual API responses.'))
# 06: gift / rationale hero
a=canvas(WH);photo(a,20,(0,0,916,H));photo(a,17,(1544,763,310,245));block(a,WH,(930,0,W,H));plate=a.copy()
label(a,'OUTCOME 01  /  DECIDE',1010,133,ACC);txt(a,'A thoughtful',1002,249,75,b=True);txt(a,'gift.',1002,336,75,b=True)
line(a,1008,486,1830,486);label(a,'WHY IT FITS',1011,533)
txt(a,'A considered shortlist',1009,595,34);txt(a,'informed by shared',1009,646,34);txt(a,'film and music tastes.',1009,697,34)
save(6,a,plate,S)
S.append(scene(6,'A decision with a reason','00:32–00:40',[20,17],
    'A book page wipes across frame; the chosen gift and readable “why” panel appear. No invented preference scores.',
    'SOURCE PHOTO + ACTUAL QLOO-GROUNDED UI','Not just an option. A considered choice—with a reason.','Recommendation is illustrative until checked against real Qloo output.'))
# 07: turn recommendation into experience
a=canvas(D);photo(a,6,(0,0,W,775));photo(a,21,(0,782,474,298));photo(a,10,(482,782,474,298));photo(a,14,(964,782,474,298));photo(a,15,(1446,782,474,298));plate=a.copy()
block(a,WH,(70,77,1470,249));txt(a,'An evening to remember.',119,114,65,b=True)
save(7,a,plate,S)
S.append(scene(7,'The experience','00:40–00:48',[6,21,10,14,15],
    'Photographic tiles sequence dinner, jazz, cinema, and food; the original rainy Tokyo street remains the consistent geographic plate.',
    'VEO only for subtly moving original street; photo compositing for tiles','And a night worth sharing.','Photos are illustrative, not booked venues.'))
# 08: collaboration without fictional personas
a=canvas(WH);photo(a,24,(820,0,1100,H));block(a,WH,(0,0,825,H));plate=a.copy()
label(a,'OUTCOME 02  /  COLLABORATE',97,106,ACC)
txt(a,'A plan',95,294,88,b=True);txt(a,'for both',95,398,88,b=True);txt(a,'of you.',95,502,88,b=True)
line(a,99,666,714,666);txt(a,'Shared taste. Shared constraints.',99,714,33)
save(8,a,plate,S)
S.append(scene(8,'Include the people who matter','00:48–00:55',[24],
    'Match-cut the dinner photo from the prior scene into a real group moment. Human expressions remain untouched.',
    'VEO restrained image-to-video on real photo','Bring someone else in. Igor remembers what matters to both.','Stock subjects do not represent Igor users.'))
# 09: draft plan not invented venue names
a=canvas(WH);photo(a,7,(1495,530,360,480));plate=a.copy()
label(a,'OUTCOME 03  /  PLAN',93,65,ACC);txt(a,'A plan, not',91,179,88,b=True);txt(a,'a list of links.',91,292,88,b=True)
label(a,'DRAFT EVENING  /  READY TO REFINE',96,452,MUT)
for j,(n,t) in enumerate([(15,'Dinner'),(10,'Live music'),(14,'A film')]):
    y=502+j*169;photo(a,n,(100,y,204,145))
    txt(a,f'0{j+1}',345,y+9,20,MUT,True);txt(a,t,347,y+53,46,b=True);line(a,345,y+139,1380,y+139)
save(9,a,plate,S)
S.append(scene(9,'An actionable plan','00:55–01:03',[15,10,14,7],
    'Recommendations snap into an ordered Adaptive Canvas. Input geometry is identical to the earlier prompt, establishing a continuous workspace.',
    'REAL PRODUCT UI + SOURCE PHOTOS','A plan you can actually explore and refine.','Venue availability, route metrics and times must be verified.'))
# 10: composed invitation
a=canvas(WH);photo(a,26,(1026,0,894,H));block(a,WH,(0,0,1037,H));plate=a.copy()
label(a,'OUTCOME 04  /  COMPOSE',98,88,ACC);txt(a,'Something',95,211,90,b=True);txt(a,'you can send.',95,323,90,b=True)
block(a,'#FFFFFF',(94,540,931,909));txt(a,'A little surprise.',146,593,61,b=True)
txt(a,'Dinner. Music. A film.',149,715,31);txt(a,'Details to confirm together.',151,777,25,MUT)
line(a,146,861,861,861);save(10,a,plate,S)
S.append(scene(10,'An invitation—not just advice','01:03–01:11',[26],
    'The itinerary folds into a printed-looking invitation; real blank stationery grounds the transition.',
    'ACTUAL COMPOSE TOOL OUTPUT + PHOTOGRAPH','And an invitation ready to edit and share.','Label unsent draft; do not claim the user shared it.'))
# 11: creator / event brief
a=canvas(WH);photo(a,27,(0,0,1182,H));photo(a,28,(1190,0,730,465));block(a,WH,(1190,472,730,608));plate=a.copy()
label(a,'OUTCOME 05  /  CREATE',1258,528,ACC);txt(a,'For a creator.',1257,591,62,b=True)
line(a,1261,715,1831,715);txt(a,'Audience insight',1263,749,30);txt(a,'Creative direction',1263,799,30);txt(a,'Usable brief',1263,849,30)
save(11,a,plate,S)
S.append(scene(11,'From taste to creative work','01:11–01:19',[27,28],
    'White invitation flips into a real-life creator moodboard wall. The camera tracks across pinned physical references.',
    'VEO subtle source-photo push + REAL CREATIVE OUTPUT','For a creator, a concept becomes a working brief.','Do not claim unbuilt creative tools are functional.'))
# 12: concierge / professional
a=canvas(WH);photo(a,29,(0,0,1031,H));photo(a,30,(1039,0,881,454));photo(a,16,(1039,462,419,618))
block(a,WH,(1466,462,454,618));plate=a.copy()
label(a,'OUTCOME 06',1502,539,ACC);txt(a,'For a',1500,598,54,b=True);txt(a,'guest.',1500,659,65,b=True)
line(a,1505,765,1835,765);txt(a,'A considered',1506,798,29);txt(a,'experience proposal.',1506,851,26)
save(12,a,plate,S)
S.append(scene(12,'The same agent, a professional outcome','01:19–01:27',[29,30,16],
    'A rigid architecture-line transition carries the viewer from the creative studio to a real hotel environment.',
    'VEO on real hotel plate + CLIENT-READY UI','For a concierge, a considered proposal built around a guest.','Professional-output feature is a proposed demo until implemented.'))
# 13: connected corrections
a=canvas(WH);photo(a,31,(1245,0,675,H));plate=a.copy()
label(a,'OUTCOMEOS  /  REVISION',98,64,ACC);txt(a,'One change.',92,199,88,b=True)
txt(a,'Many outcomes',92,301,88,b=True);txt(a,'updated.',92,400,88,b=True)
block(a,'#FFFFFF',(98,558,1105,647));txt(a,'“Actually, the budget changed.”',131,579,36)
for j,v in enumerate(['Gift options reconsidered','Experience revised','Invitation draft adjusted']):
    y=719+j*81;txt(a,f'{j+1:02}',103,y,22,ACC,True);txt(a,v,176,y-7,30)
save(13,a,plate,S)
S.append(scene(13,'The signature cross-outcome correction','01:27–01:37',[31],
    'One user correction causes only affected outputs to reflow; unaffected outcomes remain stable. No generic AI graph.',
    'RECORD REAL IGOR BACKEND + UI STATE DIFF','One change. Every affected outcome stays in sync.','Must show actual end-to-end cross-workflow state update before publishing.'))
# 14: architectural reveal of connected outputs
a=canvas(WH)
for n,b in [(17,(0,0,474,518)),(21,(481,0,474,518)),(25,(962,0,474,518)),(27,(1443,0,477,518)),(29,(0,525,616,555)),(6,(623,525,565,555))]:
    photo(a,n,b)
block(a,WH,(1197,526,723,554));plate=a.copy()
txt(a,'Not six apps.',1253,628,58,b=True);txt(a,'One OutcomeOS.',1253,715,53,b=True)
line(a,1254,830,1818,830);txt(a,'One intention. Connected outcomes.',1253,859,26)
save(14,a,plate,S)
S.append(scene(14,'OutcomeOS reveals itself','01:37–01:47',[17,21,25,27,29,6],
    'Pull the camera out from one saved artifact. Six real-world photography-backed outcomes dock into the same editorial workspace, one continuous shot.',
    'COMPOSITOR + SCREEN CAPTURE; no Veo UI hallucination','It is not six different apps. It is one connected system.'))
# 15: message with material contrast
a=canvas(D);photo(a,34,(0,0,W,345));plate=a.copy()
txt(a,'Beautiful is not enough.',112,468,87,WH,True)
txt(a,'It has to work.',112,594,87,WH,True)
line(a,109,772,1810,772,'#777B74')
txt(a,'REAL INTENT    /    EXPLAINABLE CHOICES    /    USABLE OUTCOMES',113,814,27,'#F4F1E8',True)
save(15,a,plate,S)
S.append(scene(15,'Proof is the product','01:47–01:54',[34],
    'A real gold-silk macro collapses into a flat monochrome technical proof moment. Music drops for one line.',
    'COMPOSITING + ACTUAL QA RECEIPTS','A choice you understand. An outcome you can use.','Insert real API request/response receipts, not invented Qloo scores.'))
# 16: sophisticated restrained endcard
a=canvas(WH);photo(a,34,(1010,0,910,H));block(a,WH,(0,0,1024,H));plate=a.copy()
txt(a,'Igor.',103,296,166,b=True);txt(a,'Your agent with taste.',111,541,49)
line(a,112,708,913,708);label(a,'OUTCOMEOS',110,753,ACC);txt(a,'Powered by Qloo',109,799,32)
save(16,a,plate,S)
S.append(scene(16,'The end signature','01:54–02:00',[34],
    'Final brand lockup aligns to the previous image’s fabric edge. Sound design finishes with one tactile accent, not a cinematic boom.',
    'VECTOR TYPE / EXPORTED BRAND ASSETS','Igor. Your agent with taste. Powered by Qloo.','Use official Qloo marks only subject to permitted usage.'))

for k in range(4):
    im=canvas(WH);d=ImageDraw.Draw(im)
    for j in range(4):
        i=4*k+j+1;shot=Image.open(FRAME/f'{i:02d}.jpg').resize((923,519))
        x=20+(j%2)*960;y=10+(j//2)*539
        im.paste(shot,(x,y))
        d.rectangle((x,y+490,x+923,y+519),fill=WH)
        d.text((x+12,y+493),f'{i:02d} · {S[i-1]["timecode"]} · {S[i-1]["title"]}',fill=INK,font=font(23,True))
    im.save(OUT/f'OVERVIEW_{k+1:02d}.jpg',quality=90)
(OUT/'SHOT_LIST.json').write_text(json.dumps({'title':'Igor / OutcomeOS photographic motion storyboard','seconds':120,'source_count':34,'shot_count':len(S),'shots':S},indent=2))
with (OUT/'DIRECTORS_HANDOFF.md').open('w') as f:
    f.write('# IGOR / OutcomeOS — Real-photography motion storyboard\n\n')
    f.write('**16 scenes · 120 seconds · original high-resolution 34-photo source pack.** This is an editorial storyboard, not the final film.\n\n')
    f.write('## Production rules\n\n- Preserve original photo fidelity: all images are actual Pexels source files, not AI re-creations.\n- Use the photo-only plates for image-to-video; keep type and product UI as separate composited layers.\n- Krea-style image-wall abundance for the opening; calm interface motion for decisions and outcomes.\n- Do not portray stock imagery as actual customers or Qloo-generated recommendations.\n- Approval gate: verify any Qloo rationale and cross-workflow update with live backend receipts.\n- Check photo/model/property/trademark rights before promotional release.\n\n')
    for s in S:
        f.write(f'## {s["no"]:02} — {s["title"]} ({s["timecode"]})\n\n')
        f.write(f'**Photos:** {", ".join(s["photos"])}\n\n')
        f.write(f'**VO:** {s["voiceover"]}\n\n')
        f.write(f'**Motion:** {s["motion"]}\n\n')
        f.write(f'**Production:** {s["production_method"]}\n\n')
        if s['verification']:f.write(f'**Evidence gate:** {s["verification"]}\n\n')
        f.write('---\n')
css="""body{margin:0;background:#edeae3;color:#171917;font:16px/1.65 Arial,sans-serif}header{padding:80px max(calc((100vw - 1400px)/2),5vw) 60px;border-bottom:1px solid #b8b5ac}h1{font-size:clamp(50px,8vw,126px);line-height:.92;letter-spacing:-.08em;margin:22px 0}p{margin:0}.intro{max-width:730px}main{width:min(1400px,91vw);margin:auto}article{padding:65px 0;border-bottom:1px solid #aaa}h2{font-size:50px;letter-spacing:-.06em;line-height:1.1;margin:3px 0 25px}.num{font-size:13px;letter-spacing:.14em;color:#a65139;font-weight:bold}img{display:block;width:100%;box-shadow:0 18px 45px #0002}aside{display:grid;grid-template-columns:1fr 1fr 1fr;gap:35px;margin-top:28px}aside p{font-size:15px}aside b{display:block;color:#a65139;letter-spacing:.09em;font-size:12px}a{color:inherit}footer{padding:60px 5vw;color:#555}@media(max-width:700px){aside{display:block}aside p{margin-bottom:18px}h2{font-size:33px}}"""
page=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IGOR — OutcomeOS / Photographic Storyboard</title>',f'<style>{css}</style><header><div class="num">IGOR  /  OUTCOMEOS  /  DIRECTORS VISUAL BOARD</div><h1>One intention.<br>Many outcomes.</h1><p class="intro">34 real photographs. 16 connected motion shots. One coherent story across discovery, culturally informed choice, collaboration, creation and revised outcomes. Open any frame individually, or download its text-free plate.</p></header><main>']
for s in S:
    n=s['no'];page.append(f'<article><div class="num">SCENE {n:02d} / {s["timecode"]}</div><h2>{s["title"]}</h2><img loading="lazy" src="frames/{n:02d}.jpg"><aside><p><b>VOICEOVER</b>{s["voiceover"]}</p><p><b>CAMERA & TRANSITION</b>{s["motion"]}</p><p><b>PIPELINE</b>{s["production_method"]}</p></aside><p style="padding-top:17px;font-size:14px"><a href="frames/{n:02d}.jpg">Frame</a> &nbsp; · &nbsp; <a href="photo_plates/{n:02d}_CLEAN.jpg">Clean photo plate</a> &nbsp; · &nbsp; SOURCE: {", ".join(s["photos"])}</p></article>')
page.append('</main><footer>Illustrative storyframes. Validate live Qloo/API behavior and photographic third-party rights before release.</footer></html>')
(OUT/'STORYBOARD.html').write_text('\n'.join(page))
print('DELIVERABLE: 34-source 16-scene storyboard, plates, sheets, HTML, manifest',flush=True)
