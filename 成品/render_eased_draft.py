from PIL import Image, ImageFilter, ImageEnhance
import os, sys, math, subprocess
sys.path.insert(0, r'C:\Users\34652\AppData\Local\Temp\chat-record-video-tools')
import imageio_ffmpeg
base = r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑'
out = os.path.join(base, '成品', '聊天记录草剪_缓出关键帧版.mp4')
W,H,FPS = 960,720,30
ff = imageio_ffmpeg.get_ffmpeg_exe()
# Consecutive unique portions of each chat screenshot; overlapping dialogue is trimmed at the handoff.
parts=[('主素材/1.PNG',0),('主素材/2.PNG',745),('主素材/3.PNG',778),('主素材/4.PNG',837),('主素材/5.PNG',523),('主素材/6.PNG',970),('主素材/7.PNG',580),('主素材/8.PNG',620),('主素材/9.PNG',556)]
end_y=1812
pieces=[]
for rel,y0 in parts:
    im=Image.open(os.path.join(base,'素材',rel)).convert('RGB')
    # Preserve the actual chat panel and remove phone chrome at the bottom.
    im=im.resize((946,2048),Image.Resampling.LANCZOS)
    im=im.crop((0,y0,946,end_y)).resize((W,round((end_y-y0)*W/946)),Image.Resampling.LANCZOS)
    pieces.append(im)
starts=[]; acc=0
for p in pieces: starts.append(acc); acc+=p.height
canvas=Image.new('RGB',(W,acc),(235,235,235)); acc=0
for p in pieces: canvas.paste(p,(0,acc)); acc+=p.height
max_y=max(0,canvas.height-H)
# Quadratic and cubic ease-out presets alternate by ordered dialogue section.
# y(t)=1-(1-t)^n: fast entry into the next conversation region, smooth deceleration at the keyframe stop.
markers={0.0:'start'}
for i,s in enumerate(starts[1:],1): markers[min(float(max_y),float(s))]=f'section_{i+1}'
# Brief illustrative cutaways at related beats, while keeping the chat sequence moving forward.
insert_specs=[(max(0,starts[1]-280),'而外素材/而外素材4.PNG',1.7),(max(0,starts[4]-120),'而外素材/而外素材2.jpg',1.6),(min(max_y,starts[7]+730),'而外素材/而外素材3.PNG',1.7),(min(max_y,starts[8]+450),'而外素材/而外素材1.PNG',1.7)]
for j,(y,rel,dur) in enumerate(insert_specs): markers[float(min(max_y,y))]=('insert',rel,dur,j)
ordered=sorted((y,v) for y,v in markers.items() if y<=max_y)
# De-duplicate co-located markers, preferring an insert so each insert is shown.
seq=[]
for y,v in ordered:
    if seq and abs(y-seq[-1][0])<1:
        if isinstance(v,tuple): seq[-1]=(y,v)
    else: seq.append((y,v))
# Ensure the full conversation reaches its end.
if not seq or seq[-1][0]<max_y: seq.append((float(max_y),'end'))
cmd=[ff,'-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','15','-pix_fmt','yuv420p','-movflags','+faststart',out]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
frame_count=0

def emit(im):
    global frame_count
    p.stdin.write(im.tobytes()); frame_count+=1

def hold(im,seconds):
    for _ in range(max(1,round(seconds*FPS))): emit(im)

def eased_move(y0,y1,section_idx):
    dist=y1-y0
    if dist<=0.5: return
    dur=dist/110.0
    n=max(1,round(dur*FPS))
    power=2 if section_idx%2 else 3
    for f in range(n):
        t=(f+1)/n
        e=1-(1-t)**power
        y=round(y0+dist*e)
        emit(canvas.crop((0,min(max_y,y),W,min(max_y,y)+H)))

def make_insert(rel,seconds):
    src=Image.open(os.path.join(base,'素材',rel)).convert('RGB')
    # blurred, darkened cover background plus full image fitted inside 4:3 canvas
    scale=max(W/src.width,H/src.height)
    bg=src.resize((round(src.width*scale),round(src.height*scale)),Image.Resampling.LANCZOS)
    l=(bg.width-W)//2; t=(bg.height-H)//2
    bg=bg.crop((l,t,l+W,t+H)).filter(ImageFilter.GaussianBlur(28))
    bg=ImageEnhance.Brightness(bg).enhance(.52)
    fit=min(W/src.width,H/src.height)
    fw,fh=round(src.width*fit),round(src.height*fit)
    fitim=src.resize((fw,fh),Image.Resampling.LANCZOS)
    for f in range(round(seconds*FPS)):
        # gentle cubic ease-out Ken Burns, framed within 4:3
        t=(f+1)/max(1,round(seconds*FPS)); z=1.0+0.045*(1-(1-t)**3)
        fwz,fhz=round(fw*z),round(fh*z)
        zimg=fitim.resize((fwz,fhz),Image.Resampling.LANCZOS)
        fr=bg.copy(); fr.paste(zimg,((W-fwz)//2,(H-fhz)//2))
        emit(fr)

hold(canvas.crop((0,0,W,H)),0.8)
cur=0.0; section_idx=1
for y,v in seq[1:]:
    y=float(y)
    if y>cur:
        eased_move(cur,y,section_idx); cur=y
        if not isinstance(v,tuple): hold(canvas.crop((0,min(max_y,round(cur)),W,min(max_y,round(cur))+H)),0.22)
    if isinstance(v,tuple) and v[0]=='insert':
        _,rel,dur,j=v; make_insert(rel,dur)
    section_idx+=1
hold(canvas.crop((0,max_y,W,max_y+H)),1.2)
p.stdin.close()
err=p.stderr.read().decode('utf-8','replace')
code=p.wait()
if code: raise RuntimeError(f'ffmpeg exited {code}: {err[-5000:]}')
print(f'Wrote {out}; {frame_count} frames; {frame_count/FPS:.2f}s; 960x720; silent; alternating quadratic/cubic ease-out.')

