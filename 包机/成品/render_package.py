import os, sys, math, subprocess, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机')
OUT=ROOT/'成品'/'包机_草剪.mp4'
FFMPEG=Path(r'C:\Users\34652\AppData\Local\Temp\chat-record-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe')
W,H,FPS=1440,1080,60
DUR=42.318
N=round(DUR*FPS)
BG=(31,32,34)

# Crop source attachments from the screenshots, and cover those areas in the scrolling chat pages.
# All coordinates refer to the original 1125x2436 source screenshots.
attachments={
 'emoji1':(0,(610,790,915,1095)),
 'flight':(1,(470,790,930,1215)),
 'cover':(2,(610,1245,930,1810)),
 'emoji2':(3,(190,1380,335,1510)),
 'meme':(4,(530,1110,935,1455)),
 'hotelshot':(5,(490,1115,935,1545)),
 'receipt':(7,(200,1390,575,1960)),
}
pages=[]
for idx in range(8):
    p=ROOT/'主素材'/f'{idx+1}.PNG'
    im=Image.open(p).convert('RGB')
    # Main screenshot image attachments must not appear as partial fragments while scrolling.
    for name,(page,box) in attachments.items():
        if page==idx:
            fill=im.getpixel((10,1000))
            ImageDraw.Draw(im).rectangle(box,fill=fill)
    nh=round(im.height*W/im.width)
    im=im.resize((W,nh),Image.Resampling.LANCZOS)
    pages.append(np.asarray(im,dtype=np.uint8))

# Convert original screenshot crop to full-picture stills.
source_pages=[]
for idx in range(8): source_pages.append(Image.open(ROOT/'主素材'/f'{idx+1}.PNG').convert('RGB'))
stills={}
for name,(page,box) in attachments.items():
    stills[name]=source_pages[page].crop(box).convert('RGB')

# Camera cues: (time, page index, source y, ease exponent). Speech timings come from the narration.
cues=[
(0.00,0,552,2),(1.30,0,726,3),(2.08,0,1290,2),(3.12,0,1464,3),(4.44,0,1638,2),(5.68,0,1944,3),
(6.58,1,1449,2),(8.08,1,1623,3),(9.46,1,1797,2),(10.56,1,1971,3),
(11.32,2,786,2),(11.78,2,960,3),(13.04,2,1197,2),(15.48,2,1983,3),(16.28,2,2157,2),
(17.38,3,1093,3),(17.76,3,1330,2),(19.30,3,1678,3),(20.64,3,1852,2),(21.72,3,2158,3),
(22.70,4,932,2),(23.90,4,1625,3),(25.28,4,1799,2),(25.96,4,1973,3),(26.98,4,2147,2),
(27.88,5,761,3),(28.94,5,935,2),(29.98,5,1901,3),(31.72,5,1901,2),(33.70,5,2138,3),
(35.64,6,1251,2),(36.42,6,1425,3),(37.40,6,1599,2),(38.68,6,1773,3),
(39.88,7,1038,2),(40.64,7,1212,3),(41.28,7,2130,2),
]
# Clamp and map source scroll position so the current bubble remains low in the frame.
scroll=[]
for t,pi,y,powr in cues:
    page_h=pages[pi].shape[0]
    target=max(0,min(page_h-H,round(y*(W/1125)-930)))
    scroll.append((t,pi,target,powr))

def ease(v,p):
    v=max(0,min(1,v)); return 1-(1-v)**p

def camera(t):
    k=0
    for j in range(1,len(scroll)):
        if scroll[j][0]<=t: k=j
        else: break
    cur=scroll[k]
    # A short eased move immediately before each spoken bubble.
    if k+1<len(scroll):
        nxt=scroll[k+1]
        start=max(cur[0],nxt[0]-0.46)
        if t>=start:
            v=ease((t-start)/max(0.001,nxt[0]-start),nxt[3])
            if nxt[1]==cur[1]: return cur[1],round(cur[2]+(nxt[2]-cur[2])*v)
    return cur[1],cur[2]

def page_frame(t):
    pi,sy=camera(t)
    arr=pages[pi]
    y=max(0,min(arr.shape[0]-H,sy))
    frame=arr[y:y+H,:,:].copy()
    # Crossfade screenshot changes over 0.18s to avoid a hard page flash.
    if pi>0:
        switch=next((c[0] for c in cues if c[1]==pi and c[0]>0),None)
        if switch is not None and switch<=t<switch+0.18:
            previdx=max((i for i,c in enumerate(cues) if c[0]<switch),default=0)
            pprev,yprev=camera(max(0,switch-0.01))
            if pprev==pi: pprev=max(0,pi-1); yprev=scroll[max(0,previdx)][2]
            prev=pages[pprev][max(0,min(pages[pprev].shape[0]-H,yprev)):max(0,min(pages[pprev].shape[0]-H,yprev))+H]
            a=(t-switch)/0.18
            frame=np.clip(prev.astype(np.float32)*(1-a)+frame.astype(np.float32)*a,0,255).astype(np.uint8)
    return Image.fromarray(frame)

def fit_image(im,max_box=(W-80,H-80),bg=BG):
    im=im.convert('RGB')
    scale=min(max_box[0]/im.width,max_box[1]/im.height)
    im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
    canvas=Image.new('RGB',(W,H),bg)
    canvas.paste(im,((W-im.width)//2,(H-im.height)//2))
    return canvas

def highlight_price(im, kind):
    canvas=fit_image(im,(W-110,H-70))
    d=ImageDraw.Draw(canvas)
    if kind=='flight':
        # Draw around both visible price entries without cropping the source.
        x0,y0,x1,y1=canvas.width//2-580,canvas.height//2-125,canvas.width//2+565,canvas.height//2+470
        # price column only, aligned to the right edge of the displayed source image.
        iw,ih=im.size; scale=min((W-110)/iw,(H-70)/ih); ox=(W-iw*scale)/2; oy=(H-ih*scale)/2
        x0=int(ox+iw*0.75*scale); x1=int(ox+iw*0.995*scale)
        y0=int(oy+ih*0.49*scale); y1=int(oy+ih*0.96*scale)
        d.rounded_rectangle((x0,y0,x1,y1),radius=24,outline=(255,191,56),width=8)
    elif kind=='hotel':
        iw,ih=im.size; scale=min((W-110)/iw,(H-70)/ih); ox=(W-iw*scale)/2; oy=(H-ih*scale)/2
        d.rounded_rectangle((int(ox+iw*.28*scale),int(oy+ih*.88*scale),int(ox+iw*.92*scale),int(oy+ih*.995*scale)),radius=20,outline=(255,191,56),width=8)
    return canvas

# Still overlay intervals: 0.5s slide in, then 0.3s hold. External stills hold 0.7s after a short slide.
main_overlays=[
 (2.08,0.8,'emoji1','main'),(5.68,0.8,'flight','main'),(15.48,0.8,'cover','main'),
 (19.30,0.8,'emoji2','main'),(26.62,0.8,'meme','main'),(29.98,0.8,'hotelshot','main'),
 (41.28,0.8,'receipt','main')]
external_stills=[
 (6.58,0.95,Image.open(ROOT/'内容素材'/'内容素材1.JPG').convert('RGB'),'flight'),
 (30.78,0.95,Image.open(ROOT/'内容素材'/'内容素材3.JPG').convert('RGB'),'hotel')]
# Content2 begins after the main chat's source video cover has fully entered and rested.
video_start=16.28
video_duration=20.67/2
video_end=video_start+video_duration
video_proc=None

def launch_video():
    global video_proc
    vf='setpts=PTS/2,fps=60,scale=1440:1080:force_original_aspect_ratio=decrease,pad=1440:1080:(ow-iw)/2:(oh-ih)/2:color=0x1f2022'
    cmd=[str(FFMPEG),'-v','error','-i',str(ROOT/'内容素材'/'内容素材2.MP4'),'-vf',vf,'-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    video_proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=10**7)

def still_layer(t,start,duration,img,kind):
    # the external images have a 0.25s entrance then remain completely visible for 0.7s
    if not (start<=t<start+duration): return None
    if kind in ('flight','hotel'):
        frame=highlight_price(img,kind)
    else:
        frame=fit_image(img,(W-90,H-90))
    slide=min(1,(t-start)/0.25)
    if slide<1:
        y=int((1-ease(slide,3))*H)
        base=Image.new('RGB',(W,H),BG); base.paste(frame,(0,y))
        return base
    return frame

def main_layer(t,start,duration,name):
    if not(start<=t<start+duration): return None
    img=stills[name]
    # keep small stickers visually proportional while giving full photographs a large readable presentation
    maxbox=(W-120,H-100) if name not in ('emoji1','emoji2') else (W//2,H//2)
    static=fit_image(img,maxbox)
    p=min(1,(t-start)/0.5)
    dx=int((1-ease(p,3))*W)
    base=Image.new('RGB',(W,H),BG); base.paste(static,(dx,0))
    return base

cmd=[str(FFMPEG),'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(ROOT/'配音'/'包机配音.MP3'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','15','-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','192k','-t',f'{DUR:.3f}','-movflags','+faststart',str(OUT)]
enc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,bufsize=10**7)
start_time=time.time()
for i in range(N):
    t=i/FPS
    if video_start<=t<video_end:
        if video_proc is None: launch_video()
        raw=video_proc.stdout.read(W*H*3)
        if len(raw)==W*H*3:
            frame=Image.frombytes('RGB',(W,H),raw)
        else:
            frame=Image.new('RGB',(W,H),BG)
    else:
        frame=page_frame(t)
        # Main-source extracted pictures each appear as one complete image.
        for st,dur,name,typ in main_overlays:
            layer=main_layer(t,st,dur,name)
            if layer is not None: frame=layer
        # External images are placed at the requested narration moments and retained for 0.7s.
        for st,dur,img,kind in external_stills:
            layer=still_layer(t,st,dur,img,kind)
            if layer is not None: frame=layer
    enc.stdin.write(frame.tobytes())
    if (i+1)%600==0:
        print(f'{i+1}/{N} frames ({(i+1)/FPS:.1f}s)',flush=True)
enc.stdin.close()
err=enc.stderr.read().decode('utf-8','replace')
ret=enc.wait()
if video_proc is not None:
    try: video_proc.stdout.close()
    except Exception: pass
    video_proc.wait(timeout=10)
if ret!=0: raise RuntimeError(f'ffmpeg encode failed {ret}: {err[-4000:]}')
print(f'RENDER_OK {OUT} bytes={OUT.stat().st_size} elapsed={time.time()-start_time:.1f}s frames={N}')

