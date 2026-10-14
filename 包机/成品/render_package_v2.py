import math, subprocess, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机')
OUT=ROOT/'成品'/'包机_草剪_重制版.mp4'
FFMPEG=Path(r'C:\Users\34652\AppData\Local\Temp\chat-record-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe')
W,H,FPS=1440,1080,60
DUR=63.007
N=round(DUR*FPS)
BG=(31,32,34)

# Rectangles are in the original 1125x2436 screenshots. These three matched inserts
# are deliberately left visible in their main screenshots so the transition can zoom from them.
matched={'flight':(1,(470,790,930,1215)), 'cover':(2,(610,1245,930,1810)), 'hotel':(5,(490,1115,935,1545))}
# Other attachments are hidden in the page scroll and shown once as complete cutaways.
attachments={
 'emoji1':(0,(610,790,915,1095)),
 'partial_flight':(0,(470,1990,930,2190)),
 'emoji2':(3,(190,1380,335,1510)),
 'partial_cover':(3,(610,0,930,300)),
 'meme':(4,(530,1110,935,1455)),
 'partial_hotel':(6,(485,0,935,475)),
 'receipt':(7,(200,1390,575,1960)),
}
source_pages=[Image.open(ROOT/'主素材'/f'{i+1}.PNG').convert('RGB') for i in range(8)]
pages=[]
for idx,im0 in enumerate(source_pages):
    im=im0.copy()
    for name,(pi,box) in attachments.items():
        if pi==idx:
            ImageDraw.Draw(im).rectangle(box,fill=im.getpixel((10,1000)))
    im=im.resize((W,round(im.height*W/im.width)),Image.Resampling.LANCZOS)
    pages.append(np.asarray(im,dtype=np.uint8))

# Full-frame stills from the main chat, shown once with the requested 0.5s entrance + 0.3s hold.
main_stills={name:source_pages[pi].crop(box).convert('RGB') for name,(pi,box) in attachments.items() if name in ('emoji1','emoji2','meme','receipt')}

# Speech anchors from the newly supplied 63.007s narration, matched to screenshot bubbles.
# (time, page-index, source-y, ease exponent); y is bubble bottom except for matched-image focus cues.
cues=[
 (0.00,0,552,2),(2.10,0,726,3),(3.02,0,1290,2),(4.76,0,1464,3),(6.58,0,1638,2),(8.58,0,1944,3),
 # After “包在我身上”, center screenshot 2's flight image before zooming into content 1.
 (9.80,1,1308,2),(10.42,1,1449,3),(11.98,1,1623,2),(14.14,1,1797,3),(16.24,1,1971,2),
 (16.82,2,786,3),(18.10,2,960,2),(19.74,2,1197,3),
 # After the RR / hotel-arrival line, center the main screenshot's video cover.
 (23.14,2,1833,2),
 (25.96,3,1093,3),(26.70,3,1330,2),(28.86,3,1678,3),(30.68,3,1852,2),(32.70,3,2158,3),
 (33.98,4,932,2),(35.02,4,932,3),(35.76,4,1625,2),
 (37.86,5,1799,3),(39.08,5,1973,2),(40.40,5,2147,3),(43.34,5,935,2),
 # After “没问题，包在我身上”, focus the hotel image from the main screenshot before content 3.
 (45.02,5,1635,3),(46.32,5,1901,2),(46.98,5,1901,3),(49.50,5,1901,2),(50.70,5,1901,3),(52.02,5,2138,2),
 (53.40,6,1251,3),(54.78,6,1425,2),(55.90,6,1599,3),(57.24,6,1599,2),(57.90,6,1773,3),
 (59.70,7,1038,2),(60.90,7,1212,3),(62.18,7,2130,2),
]
scroll=[]
for t,pi,y,p in cues:
    page_h=pages[pi].shape[0]
    target=max(0,min(page_h-H,round(y*(W/1125)-930)))
    scroll.append((t,pi,target,p))

def ease(v,p=3):
    v=max(0,min(1,v)); return 1-(1-v)**p

def camera(t):
    k=0
    for j in range(1,len(scroll)):
        if scroll[j][0]<=t: k=j
        else: break
    cur=scroll[k]
    if k+1<len(scroll):
        nxt=scroll[k+1]
        start=max(cur[0],nxt[0]-0.46)
        if t>=start and nxt[1]==cur[1]:
            v=ease((t-start)/max(0.001,nxt[0]-start),nxt[3])
            return cur[1],round(cur[2]+(nxt[2]-cur[2])*v)
    return cur[1],cur[2]

def page_frame(t):
    pi,sy=camera(t); arr=pages[pi]
    y=max(0,min(arr.shape[0]-H,sy)); frame=arr[y:y+H].copy()
    return Image.fromarray(frame)

def zoom_frame(page_idx,box,z):
    # Zoom the main screenshot around its embedded image; at z=1 it matches a centered page view.
    arr=pages[page_idx]
    x0,y0,x1,y1=box
    cx=((x0+x1)/2)*(W/1125); cy=((y0+y1)/2)*(W/1125)
    crop_w=W/z; crop_h=H/z
    left=cx-crop_w/2; top=cy-crop_h/2
    l=max(0,int(math.floor(left))); t=max(0,int(math.floor(top)))
    r=min(arr.shape[1],int(math.ceil(left+crop_w))); b=min(arr.shape[0],int(math.ceil(top+crop_h)))
    crop=Image.fromarray(arr[t:b,l:r])
    # Pad edge if a focus crop reaches beyond the page screenshot.
    canvas=Image.new('RGB',(max(1,round(crop_w)),max(1,round(crop_h))),BG)
    canvas.paste(crop,(max(0,round(l-left)),max(0,round(t-top))))
    return canvas.resize((W,H),Image.Resampling.LANCZOS)

def zoom_amount(box,progress):
    x0,y0,x1,y1=box
    iw=(x1-x0)*(W/1125); ih=(y1-y0)*(W/1125)
    zmax=min(W/iw,H/ih)
    return 1+(zmax-1)*ease(progress,3)

def fit_canvas(im,max_box=(W-80,H-80)):
    im=im.convert('RGB'); scale=min(max_box[0]/im.width,max_box[1]/im.height)
    im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
    base=Image.new('RGB',(W,H),BG); base.paste(im,((W-im.width)//2,(H-im.height)//2)); return base

def highlighted(im,kind):
    canvas=fit_canvas(im,(W-110,H-70)); d=ImageDraw.Draw(canvas)
    iw,ih=im.size; scale=min((W-110)/iw,(H-70)/ih); ox=(W-iw*scale)/2; oy=(H-ih*scale)/2
    if kind=='flight':
        rect=(int(ox+iw*.75*scale),int(oy+ih*.49*scale),int(ox+iw*.995*scale),int(oy+ih*.96*scale))
    else:
        rect=(int(ox+iw*.28*scale),int(oy+ih*.88*scale),int(ox+iw*.92*scale),int(oy+ih*.995*scale))
    d.rounded_rectangle(rect,radius=22,outline=(255,191,56),width=8)
    return canvas

# Each matched sequence: zoom into visible main-screenshot media, show the corresponding insert for 0.7s,
# and (for stills) pull back to the same screenshot position.
flight_asset=Image.open(ROOT/'内容素材'/'内容素材1.JPG').convert('RGB')
hotel_asset=Image.open(ROOT/'内容素材'/'内容素材3.JPG').convert('RGB')
transitions=[
 {'kind':'still','page':1,'box':matched['flight'][1],'zoom_in':(10.00,10.32),'hold':(10.32,11.02),'zoom_out':(11.02,11.34),'asset':flight_asset,'highlight':'flight'},
 {'kind':'video','page':2,'box':matched['cover'][1],'zoom_in':(23.29,23.64),'hold':(23.64,33.975),'asset':None},
 {'kind':'still','page':5,'box':matched['hotel'][1],'zoom_in':(45.02,45.37),'hold':(45.37,46.07),'zoom_out':(46.07,46.42),'asset':hotel_asset,'highlight':'hotel'},
]

video_proc=None
video_last=None
VIDEO_START=23.64
VIDEO_END=23.64+20.67/2

def start_video():
    global video_proc
    vf='setpts=PTS/2,fps=60,scale=1440:1080:force_original_aspect_ratio=decrease,pad=1440:1080:(ow-iw)/2:(oh-ih)/2:color=0x1f2022'
    cmd=[str(FFMPEG),'-v','error','-i',str(ROOT/'内容素材'/'内容素材2.MP4'),'-vf',vf,'-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    video_proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=10**7)

def still_cutaway(t,start,name):
    if not(start<=t<start+0.8): return None
    maxbox=(W//2,H//2) if name in ('emoji1','emoji2') else (W-90,H-90)
    img=fit_canvas(main_stills[name],maxbox)
    p=min(1,(t-start)/0.5); dx=int((1-ease(p,3))*W)
    base=Image.new('RGB',(W,H),BG); base.paste(img,(dx,0)); return base

cmd=[str(FFMPEG),'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(ROOT/'配音'/'包机配音.MP3'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','15','-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','192k','-t',f'{DUR:.3f}','-movflags','+faststart',str(OUT)]
enc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,bufsize=10**7)
t0=time.time()
for i in range(N):
    sec=i/FPS
    frame=page_frame(sec)
    # Main source emoji / meme / transfer record stills.
    for st,name in [(3.02,'emoji1'),(28.86,'emoji2'),(35.76,'meme'),(62.18,'receipt')]:
        layer=still_cutaway(sec,st,name)
        if layer is not None: frame=layer
    # Matched image zoom transitions, then the full corresponding external content.
    for tr in transitions:
        zin0,zin1=tr['zoom_in']; h0,h1=tr['hold']
        zout=tr.get('zoom_out')
        if zin0<=sec<zin1:
            pr=(sec-zin0)/(zin1-zin0); frame=zoom_frame(tr['page'],tr['box'],zoom_amount(tr['box'],pr))
        elif h0<=sec<h1:
            if tr['kind']=='video':
                if video_proc is None: start_video()
                raw=video_proc.stdout.read(W*H*3)
                if len(raw)==W*H*3:
                    video_last=Image.frombytes('RGB',(W,H),raw)
                    frame=video_last
                elif video_last is not None: frame=video_last
            else:
                frame=highlighted(tr['asset'],tr['highlight'])
        elif zout and zout[0]<=sec<zout[1]:
            pr=1-(sec-zout[0])/(zout[1]-zout[0]); frame=zoom_frame(tr['page'],tr['box'],zoom_amount(tr['box'],pr))
    # Fade the completed 2x video into the next chat screen without shortening its playback.
    if VIDEO_END-0.24<=sec<VIDEO_END and video_last is not None:
        a=max(0,min(1,(sec-(VIDEO_END-0.24))/0.24))
        bg=page_frame(sec)
        frame=Image.blend(video_last,bg,a)
    enc.stdin.write(frame.tobytes())
    if (i+1)%600==0: print(f'{i+1}/{N} frames ({(i+1)/FPS:.1f}s)',flush=True)
enc.stdin.close(); err=enc.stderr.read().decode('utf-8','replace'); ret=enc.wait()
if video_proc is not None:
    try: video_proc.stdout.close()
    except Exception: pass
    video_proc.wait(timeout=10)
if ret!=0: raise RuntimeError(f'ffmpeg encode failed {ret}: {err[-4000:]}')
print(f'RENDER_OK {OUT} bytes={OUT.stat().st_size} elapsed={time.time()-t0:.1f}s frames={N} duration={DUR:.3f}')
