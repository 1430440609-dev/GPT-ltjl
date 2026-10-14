import math,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机')
OUT=ROOT/'成品'/'包机_草剪_主素材原画面版.mp4'
FFMPEG=Path(r'C:\Users\34652\AppData\Local\Temp\chat-record-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe')
W,H,FPS=1440,1080,60; DUR=63.007; N=round(DUR*FPS); BG=(31,32,34)
# Read each source screenshot untouched. The only operation on the main material is the viewport pan
# needed to show the long phone screenshots in a 4:3 video frame.
pages=[]
for i in range(8):
    im=Image.open(ROOT/'主素材'/f'{i+1}.PNG').convert('RGB')
    im=im.resize((W,round(im.height*W/im.width)),Image.Resampling.LANCZOS)
    pages.append(np.asarray(im,dtype=np.uint8))
# New narration word timings from the replacement MP3; quadratic/cubic ease-out alternates per stop.
cues=[
 (0.00,0,552,2),(2.10,0,726,3),(3.02,0,1290,2),(4.76,0,1464,3),(6.58,0,1638,2),(8.58,0,1944,3),
 (9.80,1,1308,2),(10.42,1,1449,3),(11.98,1,1623,2),(14.14,1,1797,3),(16.24,1,1971,2),
 (16.82,2,786,3),(18.10,2,960,2),(19.74,2,1197,3),(23.14,2,1833,2),
 (25.96,3,1093,3),(26.70,3,1330,2),(28.86,3,1678,3),(30.68,3,1852,2),(32.70,3,2158,3),
 (33.98,4,932,2),(35.02,4,932,3),(35.76,4,1625,2),
 (37.86,5,1799,3),(39.08,5,1973,2),(40.40,5,2147,3),(43.34,5,935,2),(45.02,5,1635,3),
 (46.32,5,1901,2),(46.98,5,1901,3),(49.50,5,1901,2),(50.70,5,1901,3),(52.02,5,2138,2),
 (53.40,6,1251,3),(54.78,6,1425,2),(55.90,6,1599,3),(57.24,6,1599,2),(57.90,6,1773,3),
 (59.70,7,1038,2),(60.90,7,1212,3),(62.18,7,2130,2)]
scroll=[]
for t,pi,y,p in cues:
    # Keep a small bottom margin after the active bubble so the next bubble stays below frame.
    target=max(0,min(pages[pi].shape[0]-H,round(y*(W/1125)-(H-50))))
    scroll.append((t,pi,target,p))
def ease(v,p):
    v=max(0,min(1,v)); return 1-(1-v)**p
def camera(sec):
    k=0
    for j in range(1,len(scroll)):
        if scroll[j][0]<=sec: k=j
        else: break
    cur=scroll[k]
    if k+1<len(scroll):
        nxt=scroll[k+1]; start=max(cur[0],nxt[0]-0.46)
        if sec>=start and nxt[1]==cur[1]:
            q=ease((sec-start)/max(0.001,nxt[0]-start),nxt[3])
            return cur[1],round(cur[2]+(nxt[2]-cur[2])*q)
    return cur[1],cur[2]
def page_frame(sec):
    pi,y=camera(sec); arr=pages[pi]; y=max(0,min(arr.shape[0]-H,y))
    return Image.fromarray(arr[y:y+H].copy())
def contain(im):
    im=im.convert('RGB'); factor=min((W-100)/im.width,(H-80)/im.height)
    im=im.resize((round(im.width*factor),round(im.height*factor)),Image.Resampling.LANCZOS)
    frame=Image.new('RGB',(W,H),BG); frame.paste(im,((W-im.width)//2,(H-im.height)//2)); return frame
def emphasize_price(im,which):
    # Keep the full content image visible; use a brief outline to draw the eye to its price area.
    frame=contain(im); d=ImageDraw.Draw(frame); iw,ih=im.size
    s=min((W-100)/iw,(H-80)/ih); ox=(W-iw*s)/2; oy=(H-ih*s)/2
    if which=='flight': rect=(int(ox+iw*.75*s),int(oy+ih*.49*s),int(ox+iw*.995*s),int(oy+ih*.96*s))
    else: rect=(int(ox+iw*.28*s),int(oy+ih*.88*s),int(ox+iw*.92*s),int(oy+ih*.995*s))
    d.rounded_rectangle(rect,radius=22,outline=(255,191,56),width=8); return frame
img1=Image.open(ROOT/'内容素材'/'内容素材1.JPG').convert('RGB')
img3=Image.open(ROOT/'内容素材'/'内容素材3.JPG').convert('RGB')
# Based on 内容素材出现时机.txt: show the related main screenshot first (0.3s),
# then show each still for 0.7s. The full video starts after its screenshot cover is visible.
STILL1=(10.10,10.80,emphasize_price(img1,'flight'))
STILL3=(45.32,46.02,emphasize_price(img3,'hotel'))
VIDEO_START=23.44; VIDEO_END=VIDEO_START+20.67/2
video_proc=None
def launch_video():
    global video_proc
    vf='setpts=PTS/2,fps=60,scale=1440:1080:force_original_aspect_ratio=decrease,pad=1440:1080:(ow-iw)/2:(oh-ih)/2:color=0x1f2022'
    args=[str(FFMPEG),'-v','error','-i',str(ROOT/'内容素材'/'内容素材2.MP4'),'-vf',vf,'-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    video_proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=10**7)
args=[str(FFMPEG),'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(ROOT/'配音'/'包机配音.MP3'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','15','-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','192k','-t',f'{DUR:.3f}','-movflags','+faststart',str(OUT)]
enc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,bufsize=10**7)
t0=time.time(); last_video=None
for i in range(N):
    sec=i/FPS; frame=page_frame(sec)
    # Only the external content folder is inserted. Main screenshots and stickers stay untouched.
    if STILL1[0]<=sec<STILL1[1]: frame=STILL1[2]
    elif VIDEO_START<=sec<VIDEO_END:
        if video_proc is None: launch_video()
        raw=video_proc.stdout.read(W*H*3)
        if len(raw)==W*H*3: last_video=Image.frombytes('RGB',(W,H),raw); frame=last_video
        elif last_video is not None: frame=last_video
    elif STILL3[0]<=sec<STILL3[1]: frame=STILL3[2]
    enc.stdin.write(frame.tobytes())
    if (i+1)%600==0: print(f'{i+1}/{N} frames ({(i+1)/FPS:.1f}s)',flush=True)
enc.stdin.close(); err=enc.stderr.read().decode('utf-8','replace'); ret=enc.wait()
if video_proc is not None:
    try: video_proc.stdout.close()
    except Exception: pass
    video_proc.wait(timeout=10)
if ret!=0: raise RuntimeError(f'ffmpeg encode failed {ret}: {err[-4000:]}')
print(f'RENDER_OK {OUT} bytes={OUT.stat().st_size} elapsed={time.time()-t0:.1f}s frames={N}')
