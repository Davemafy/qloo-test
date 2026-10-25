#!/usr/bin/env python3
"""IGOR OutcomeOS signature sequence — photographic keyframe art direction.

Uses unchanged pixels from licensed-source photo library (photo IDs A17, A18, A21,
A22, A25, A26). Creates three matched, 1920x1080 movie keyframes, plus three
type-free plates for motion/Veo. Does not manufacture product screenshots.
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import json
import os

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"dist"/"photos"
OUT=ROOT/"production"/"signature"
OUT.mkdir(parents=True,exist_ok=True)
W,H=1920,1080
PAPER=(245,242,234)
INK=(24,30,28)
MUTED=(106,107,100)
COPPER=(163,67,45)
WHITE=(252,250,243)

def font_path(family,style):
    roots=[
      "/usr/share/fonts/truetype/lato",
      "/usr/share/fonts/truetype/liberation2",
      "/usr/share/fonts/truetype/dejavu"
    ]
    names={
      ("serif","regular"):["LiberationSerif-Regular.ttf","DejaVuSerif.ttf"],
      ("serif","bold"):["LiberationSerif-Bold.ttf","DejaVuSerif-Bold.ttf"],
      ("sans","regular"):["Lato-Regular.ttf","LiberationSans-Regular.ttf","DejaVuSans.ttf"],
      ("sans","bold"):["Lato-Bold.ttf","LiberationSans-Bold.ttf","DejaVuSans-Bold.ttf"],
      ("sans","light"):["Lato-Light.ttf","LiberationSans-Regular.ttf","DejaVuSans.ttf"]
    }[(family,style)]
    for name in names:
        for root in roots:
            p=Path(root)/name
            if p.exists():return str(p)
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def font(sz,family="sans",style="regular"):
    return ImageFont.truetype(font_path(family,style),sz)

def crop_photo(photo, size, center=(.5,.5)):
    im=Image.open(SRC/f"{photo}.jpg").convert("RGB")
    im=ImageOps.exif_transpose(im)
    return ImageOps.fit(im,size,method=Image.Resampling.LANCZOS,centering=center)

def grade(im,photo):
    # Gentle, identical film-finishing pass for stock sources of unequal color.
    im=ImageEnhance.Contrast(im).enhance(0.98)
    im=ImageEnhance.Color(im).enhance(0.91)
    wash=Image.new("RGB",im.size,(239,226,206))
    return Image.blend(im,wash,0.055)

def spaced(d, text, xy, face, fill, spacing=3):
    x,y=xy
    for ch in text:
        d.text((x,y),ch,font=face,fill=fill)
        x+=d.textlength(ch,font=face)+spacing

def compose(ids, state, frame_num, clean=False):
    im=Image.new("RGB",(W,H),PAPER)
    d=ImageDraw.Draw(im)
    for y in range(0,H,6):
        # Subtle non-repeating horizontal paper texture; no gradients/neon.
        line=(244 if y%24==0 else 245,241 if y%18==0 else 242,233 if y%24==0 else 234)
        d.line((0,y,W,y),fill=line,width=1)
    xpoints=[74,674,1274]
    width,height=572,516
    t=333
    for i,(x,id) in enumerate(zip(xpoints,ids)):
        photo=grade(crop_photo(id,(width,height)),id)
        im.paste(photo,(x,t))
    # Paper-based photographic geometry (same for all states).
    d=ImageDraw.Draw(im)
    d.line((74,95,1846,95),fill=(201,196,182),width=2)
    d.line((74,1010,1846,1010),fill=(201,196,182),width=2)
    d.line((74,887,1846,887),fill=(201,196,182),width=2)

    if clean:
        path=OUT/f"{frame_num:02d}_{state}_PLATE.jpg"
        im.save(path,"JPEG",quality=95,subsampling=0)
        return

    spaced(d,"IGOR.",(74,45),font(35,"sans","bold"),INK,spacing=1)
    spaced(d,"OUTCOMEOS  /  ONE INTENTION",(1240,53),font(19,"sans","bold"),MUTED,spacing=3)

    if state=="before":
        d.text((74,126),"One intention.",font=font(112,"serif","regular"),fill=INK)
        d.text((79,265),"A thoughtful celebration for someone who loves cinema and jazz.",
               font=font(27,"sans","regular"),fill=MUTED)
    elif state=="change":
        d.text((74,126),"Then one thing changes.",font=font(100,"serif","regular"),fill=INK)
        d.text((79,268),"The goal stays the same. The constraints don't.",
               font=font(26,"sans","regular"),fill=MUTED)
    else:
        d.text((74,126),"One change. Three outcomes.",font=font(88,"serif","regular"),fill=INK)
        d.text((79,268),"Each affected piece is considered again. Nothing gets lost.",
               font=font(26,"sans","regular"),fill=MUTED)

    labels_before=[
        ("01  /  GIFT","A considered choice."),
        ("02  /  EVENING","Something to look forward to."),
        ("03  /  INVITATION","Something to send.")
    ]
    labels_after=[
        ("01  /  GIFT","Reconsidered."),
        ("02  /  EVENING","Replanned."),
        ("03  /  INVITATION","Rewritten.")
    ]
    labs=labels_after if state=="after" else labels_before
    for x,(label,sub) in zip(xpoints,labs):
        spaced(d,label,(x,903),font(17,"sans","bold"),COPPER,spacing=2)
        d.text((x,937),sub,font=font(26,"sans","regular"),fill=INK)

    if state=="change":
        # One physical-print overlay, not a synthetic floating chatbot card.
        ov=Image.new("RGBA",(W,H),(0,0,0,0))
        dd=ImageDraw.Draw(ov)
        dd.rectangle((74,480,1846,720),fill=(30,33,30,240))
        dd.rectangle((74,480,87,720),fill=COPPER+(255,))
        dd.text((130,514),"“Actually, keep it under $150.”",
                font=font(76,"serif","regular"),fill=WHITE)
        spaced(dd,"A SINGLE CORRECTION  /  THREE AFFECTED RESULTS",
               (135,642),font(20,"sans","bold"),(225,218,203),spacing=2)
        im=Image.alpha_composite(im.convert("RGBA"),ov).convert("RGB")
        d=ImageDraw.Draw(im)

    if state=="after":
        spaced(d,"REVISED   /   03 OF 03",(74,1035),font(19,"sans","bold"),COPPER,spacing=2)
        d.text((1358,1030),"One conversation. Connected results.",
               font=font(20,"sans","regular"),fill=MUTED)
    else:
        spaced(d,"THE ORIGINAL BRIEF",(74,1035),font(18,"sans","bold"),MUTED,spacing=2)
        d.text((1490,1030),"Your agent with taste.",
               font=font(20,"sans","regular"),fill=MUTED)
    im.save(OUT/f"{frame_num:02d}_{state}_STORYFRAME.jpg","JPEG",quality=95,subsampling=0)

def main():
    before=["A17","A21","A25"]
    after=["A18","A22","A26"]
    states=[
      ("before", before,1),
      ("change",before,2),
      ("after",after,3)
    ]
    for state,ids,n in states:
        compose(ids,state,n,clean=True)
        compose(ids,state,n,clean=False)
    # One contact strip; individual full-HD frames remain the primary deliverable.
    board=Image.new("RGB",(1536,3*310+42),PAPER)
    d=ImageDraw.Draw(board)
    for i,(state,_,n) in enumerate(states):
        frame=Image.open(OUT/f"{n:02d}_{state}_STORYFRAME.jpg")
        preview=ImageOps.contain(frame,(1500,843//3))
        board.paste(preview,(18,18+i*310))
        d.text((19,300+i*310),f"0{n}   {['THE ORIGINAL BRIEF','THE CORRECTION','THE CONNECTED REVISION'][i]}",
               font=font(21,"sans","bold"),fill=INK)
    board.save(OUT/"SEQUENCE_OVERVIEW.jpg",quality=92)

    handoff={
      "title":"IGOR / One intention. Three outcomes.",
      "duration_seconds":8,
      "fps":24,
      "visual_language":"real source photography, physical rectangular framing, uncoated print stock, upright editorial typography, muted copper accent, no glowing interface",
      "frames":[{"time":"00:00–00:02.5","image":"01_before_STORYFRAME.jpg","plate":"01_before_PLATE.jpg","action":"Hold the connected set of outcomes. A near-imperceptible photographic push."},
                {"time":"00:02.5–00:04.5","image":"02_change_STORYFRAME.jpg","plate":"02_change_PLATE.jpg","action":"A new constraint enters on a physically flat dark matte. Hold for reading."},
                {"time":"00:04.5–00:08","image":"03_after_STORYFRAME.jpg","plate":"03_after_PLATE.jpg","action":"Three photographic panels change one after another using precise editorial wipe masks. Hold the revised outcome labels."}],
      "editorial_rule":"Keyframe geometry must not move. Typography and photo swaps must be made in 2D postproduction for fidelity; Veo may animate texture only.",
      "truth_in_advertising":"This sequence is a CONCEPT until genuine Igor execution and Qloo provenance prove the displayed revision. Do not claim live updates or bookings without testing.",
      "sources":{"gift_original":"A17","gift_revised":"A18","evening_original":"A21","evening_revised":"A22","invite_original":"A25","invite_revised":"A26"},
      "sound":"Single initial paper foley tick, low musical pulse, three quiet staggered tactile clicks as output panels update. Avoid dramatic whooshes."
    }
    (OUT/"DIRECTOR_HANDOFF.json").write_text(json.dumps(handoff,indent=2))
    (OUT/"README.md").write_text(
      "# IGOR / OutcomeOS signature motion moment\n\n"
      "Three connected frames from 6 actual sourced photographs. No generated UI.\n\n"
      "1. Place 01_before_STORYFRAME.jpg at 0:00.\n"
      "2. Introduce 02_change_STORYFRAME.jpg at 2.5 seconds, using type compositing.\n"
      "3. Wipe the 3 photos one by one into 03_after_STORYFRAME.jpg, holding to 8 seconds.\n\n"
      "Clean plates for camera texture generation are supplied separately. "
      "Veo should **not** be asked to rewrite type or swap three specific images. "
      "For accurate product behavior, insert real Igor UI footage in this edit.\n\n"
      "Creative proof only; do not imply these stock images are verified Qloo outputs or completed bookings.\n"
    )
    print("Generated 3 approved-design-direction storyframes + 3 source-image plates + contact strip")

if __name__=="__main__":main()
