#!/usr/bin/env python3
"""Build storyframes directly from 34 original downloaded source photos.
There are no image-model-generated props or invented screens.
All typography is editorial vector text, separate from clean footage plates.
"""
import json, math
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageEnhance
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'dist/photos'
OUT=ROOT/'production/storyboards'
FR=OUT/'frames'; PL=OUT/'plates'; FR.mkdir(parents=True,exist_ok=True); PL.mkdir(parents=True,exist_ok=True)
W,H=1920,1080
BASE='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
LIGHT='#F5F2EA';INK='#17201D';WHITE='#FFFFFF'
def f(size,bold=False):
    return ImageFont.truetype(BOLD if bold else BASE,size)
def src(id):
    return Image.open(SRC/(id+'.jpg')).convert('RGB')
def fit(im,size,centering=(.5,.5)):
    return ImageOps.fit(im,size,method=Image.Resampling.LANCZOS,centering=centering)
def put(canvas,id,box,center=(.5,.5)):
    x,y,w,h=box
    im=fit(src(id),(w,h),center)
    canvas.paste(im,(x,y))
def text(im,s,x,y,size=70,color=INK,bold=False,space=15):
    ImageDraw.Draw(im).multiline_text((x,y),s,fill=color,font=f(size,bold),spacing=space)
def small(im,s,x,y,color=INK):
    text(im,s.upper(),x,y,22,color,True)
def rect(im,xy,fill):
    ImageDraw.Draw(im).rectangle(xy,fill=fill)
def overlay(im,alpha=170,side='left'):
    c=im.convert('RGBA')
    o=Image.new('RGBA',(W,H))
    d=ImageDraw.Draw(o)
    for x in range(0,W,4):
        t=(1-x/W) if side=='left' else (x/W)
        a=int(alpha*pow(t,1.5))
        d.rectangle((x,0,x+4,H),fill=(8,18,18,a))
    return Image.alpha_composite(c,o).convert('RGB')
def new(color=LIGHT):
    return Image.new('RGB',(W,H),color)
timeline=[]
def finish(n,title,seconds,assets,plate,art,production,motion):
    plate.save(PL/f'{n:02d}_clean.jpg',quality=92,subsampling=0)
    art.save(FR/f'{n:02d}_storyframe.jpg',quality=92,subsampling=0)
    timeline.append(dict(shot=n,title=title,timecode=seconds,source_assets=assets,production=production,motion=motion,frame=f'frames/{n:02d}_storyframe.jpg',clean=f'plates/{n:02d}_clean.jpg'))
# 01 — one wall, all 34 photographs, not model-generated imagery
ids=['A%02d'%i for i in range(1,35)]
c=new('#131B1A')
for i,id in enumerate(ids):
    col=i%9;row=i//9
    x=24+col*209;y=24+row*259
    put(c,id,(x,y,201,250))
art=overlay(c,150)
text(art,'A world of possibilities.',118,720,91,WHITE,True)
small(art,'THE BIGGER THE WORLD, THE HARDER THE CHOICE',125,925,WHITE)
finish(1,'The world', '00:00–00:07',ids,c,art,'2D motion','Photography enters in staggered film-strip beats, not UI cards')
# 02
c=new();put(c,'A02',(0,0,W,H));a=overlay(c,200)
text(a,'More choices.\nNot always better ones.',118,310,101,WHITE,True)
finish(2,'The problem','00:07–00:14',['A01','A02'],c,a,'Veo','Slow photoreal push through actual forest light, no added objects')
# 03
c=new();put(c,'A05',(0,0,835,H),(.5,.5));put(c,'A03',(850,0,1070,H),(.5,.53))
a=c.copy();rect(a,(0,0,835,H),LIGHT);put(a,'A05',(850,0,1070,H),(.53,.55))
small(a,'AN IDEA',120,180)
text(a,'What if your agent\nunderstood your taste?',120,290,76,INK,True)
finish(3,'An idea','00:14–00:20',['A03','A05'],c,a,'2D motion','Split physical curtains; typographic entrance via window edge')
# 04
c=new();put(c,'A04',(1218,0,702,H));a=c.copy()
text(a,'Igor',115,265,183,INK,True)
text(a,'One conversation.\nMany outcomes.',123,560,62,INK)
small(a,'YOUR AGENT WITH TASTE',124,885)
finish(4,'Introducing Igor','00:20–00:26',['A04'],c,a,'2D brand motion','Curtain light slides out; Igor wordmark enters on locked typographic grid')
# 05
c=new();put(c,'A19',(1160,0,760,540),(.5,.5));put(c,'A11',(1160,554,760,526))
a=c.copy()
small(a,'ONE CLEAR REQUEST',105,170)
text(a,'Find a thoughtful\ngift for someone\nwho loves cinema\nand jazz.',105,308,70,INK,True,10)
finish(5,'The request','00:26–00:34',['A11','A19'],c,a,'REAL UI','Replace art text with exact live Igor prompt in post. No generated chat bubbles')
# 06
c=new('#151C1A')
for id,rect in [('A13',(715,85,350,300)),('A10',(1080,85,330,460)),('A07',(1425,85,410,460)),('A11',(715,400,350,540)),('A15',(1080,560,330,380)),('A20',(1425,560,410,380))]:
    put(c,id,rect)
a=c.copy();small(a,'QLOO TASTE INTELLIGENCE',95,170,WHITE)
text(a,'What connects\nwhat we love?',95,317,86,WHITE,True)
small(a,'FILM   /   MUSIC   /   BOOKS   /   PLACES',95,885,WHITE)
finish(6,'Cultural judgment','00:34–00:42',['A07','A10','A11','A13','A15','A20'],c,a,'2D + REAL QLOO','Use real entity resolution and Qloo evidence, not fabricated affinity percentages')
# 07
c=new();put(c,'A17',(0,0,1020,H),(.5,.3))
a=c.copy();small(a,'OUTCOME 01   /   A THOUGHTFUL GIFT',1110,260)
text(a,'A choice\nwith a reason.',1108,370,78,INK,True)
text(a,'Not just another list.',1110,723,38,INK)
finish(7,'Gift outcome','00:42–00:49',['A17','A18'],c,a,'Veo + REAL UI','Macro move on photographed ribbon. Display actual rationale in compositing')
# 08
c=new();put(c,'A21',(0,0,960,H),(.5,.47));put(c,'A22',(975,0,945,H),(.5,.55))
a=overlay(c,170)
small(a,'OUTCOME 02   /   A NIGHT TOGETHER',103,190,WHITE)
text(a,'Not another suggestion.\nA shared experience.',97,715,76,WHITE,True)
finish(8,'Shared experience','00:49–00:56',['A21','A22'],c,a,'Veo','Subtle candle flame motion, practical camera drift; no invented bookings')
# 09
c=new();put(c,'A10',(0,0,900,H),(.5,.45));put(c,'A14',(914,0,1006,528));put(c,'A12',(914,542,1006,538))
a=overlay(c,120)
text(a,'Music. Film.\nThe right atmosphere.',105,768,68,WHITE,True)
finish(9,'Cultural atmosphere','00:56–01:03',['A10','A12','A14'],c,a,'Veo + edit','Cut from brass highlight to auditorium light, sync edits to sound')
# 10
c=new();put(c,'A07',(0,0,1030,H));put(c,'A08',(1046,0,874,H))
a=overlay(c,195)
small(a,'OUTCOME 03   /   PLACES',108,170,WHITE)
text(a,'From a feeling\nto somewhere real.',104,730,78,WHITE,True)
finish(10,'Places','01:03–01:10',['A06','A07','A08','A09'],c,a,'Veo + REAL MAP','Physically plausible rainy-street movement; live map UI overlaid in post')
# 11
c=new();put(c,'A25',(0,0,1000,H),(.5,.43));put(c,'A26',(1016,0,904,H))
a=c.copy();text(a,'The invitation\nis ready.',110,270,87,INK,True)
small(a,'OUTCOME 04  /  AN ACTUAL ARTIFACT',112,620)
finish(11,'Invitation','01:10–01:17',['A25','A26'],c,a,'REAL UI + tracking','Project actual invitation output on stationery. Do not fake sent messages')
# 12
c=new();put(c,'A23',(0,0,960,H));put(c,'A24',(976,0,944,H))
a=overlay(c,184)
small(a,'OUTCOME 05   /   SHARED PREFERENCES',112,183,WHITE)
text(a,'Make it work\nfor everyone.',111,746,86,WHITE,True)
finish(12,'Collaboration','01:17–01:24',['A23','A24'],c,a,'REAL UI + 2D','Context change flows into revisions while showing unchanged outputs remain unchanged')
# 13
c=new();put(c,'A27',(940,0,980,539));put(c,'A28',(940,554,980,526))
a=c.copy();small(a,'OUTCOME 06  /  CREATE',110,178)
text(a,'From inspiration\nto a real\ncreative brief.',109,305,71,INK,True)
finish(13,'Creative brief','01:24–01:32',['A27','A28'],c,a,'REAL UI','Composite genuine output or clearly label illustrative mock')
# 14
c=new();put(c,'A29',(0,0,930,H),(.5,.42));put(c,'A30',(944,0,976,H))
a=overlay(c,177);small(a,'OUTCOME 07  /  PROFESSIONAL',105,161,WHITE)
text(a,'For people.\nFor teams.\nFor guests.',105,640,85,WHITE,True)
finish(14,'Professional experiences','01:32–01:40',['A29','A30'],c,a,'Veo + verified UI','Smoothly track architectural verticals, do not imply booking integration')
# 15
c=new()
for i,id in enumerate(['A17','A22','A25','A27','A30']):
    put(c,id,(62+i*373,243,354,490))
a=c.copy();small(a,'THE OUTCOMEOS MOMENT',70,98)
text(a,'One change. Connected outcomes.',70,830,62,INK,True)
finish(15,'Outcome revision','01:40–01:49',['A17','A22','A25','A27','A30'],c,a,'REAL PRODUCT SCREEN','A budget revision updates affected outputs. Must be actually implemented')
# 16 image wall callback
c=new('#121B19')
for i,id in enumerate(ids):
    x=25+(i%9)*208;y=20+(i//9)*260
    put(c,id,(200,250))
a=overlay(c,206)
text(a,'One conversation.\nMany outcomes.',116,370,106,WHITE,True)
small(a,'IGOR   /   OUTCOMEOS   /   POWERED BY QLOO',120,900,WHITE)
finish(16,'OutcomeOS revealed','01:49–01:58',ids,c,a,'2D MOTION','Photo wall becomes one typographic identity, no decorative neural nets')
# 17 closing card
c=new(LIGHT);a=c.copy()
text(a,'Igor',112,278,210,INK,True)
text(a,'OutcomeOS',123,553,68,INK)
text(a,'Your agent with taste.',124,748,37,INK)
small(a,'POWERED BY QLOO',126,900)
finish(17,'Brand closure','01:58–02:04',[],c,a,'2D MOTION','Hold, sonic resolve, end')
# 4-up preview sheets, all text in raster styleframes from real image pixels
for offset in range(0,len(timeline),4):
    subset=timeline[offset:offset+4]
    sheet=Image.new('RGB',(2040,1320),'#E8E8E1')
    d=ImageDraw.Draw(sheet)
    for i,m in enumerate(subset):
        img=fit(Image.open(OUT/m['frame']),(958,535))
        x=40+(i%2)*1005;y=30+(i//2)*625
        sheet.paste(img,(x,y))
        d.text((x+5,y+549),f'{m["shot"]:02d}  {m["timecode"]}  {m["title"]}',fill=INK,font=f(23,True))
    sheet.save(OUT/f'overview_{offset//4+1:02d}.jpg',quality=90)
(OUT/'SHOT_LIST.json').write_text(json.dumps(timeline,indent=2))
with (OUT/'DIRECTORS_NOTES.md').open('w') as f1:
    f1.write('# IGOR OutcomeOS — photographic storyboard V2\n\nAll 34 source-photo IDs appear in the image-wall shots; other shots use actual photographic pixels. This is an editorial storyboard, not a claim of deployed product outcomes. Do not present stock-photo people or venues as Igor customers or Qloo selections. Photo origin/copyright information is in the source acquisition report.\n\n**Veo**: use the individual file from \`plates/\` for cinematic physical scenes, not image-wall or UI shots. \`frames/\` are the composited reference storyframes. For actual product demonstrations, screen-record the application and add Qloo provenance from real responses.\n\n')
    for x in timeline:
        f1.write(f'## {x["shot"]:02d}. {x["title"]} — {x["timecode"]}\nSources: {", ".join(x["source_assets"])}\nMethod: {x["production"]}\nMotion: {x["motion"]}\n\n')
print('DONE',len(timeline),'frames',len(ids),'source images')
