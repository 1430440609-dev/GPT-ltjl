from PIL import Image, ImageFilter, ImageEnhance
import numpy as np, os, subprocess, sys, math
sys.path.insert(0,r'C:\Users\34652\AppData\Local\Temp\chat-record-video-tools')
import imageio_ffmpeg
base=r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑'; out=os.path.join(base,'成品','聊天记录草剪_逐句缓出节奏版.mp4')
W,H,FPS=960,720,30; ff=imageio_ffmpeg.get_ffmpeg_exe()
parts=[('主素材/1.PNG',0),('主素材/2.PNG',745),('主素材/3.PNG',778),('主素材/4.PNG',837),('主素材/5.PNG',523),('主素材/6.PNG',970),('主素材/7.PNG',580),('主素材/8.PNG',620),('主素材/9.PNG',556)]
ims=[]
for rel,y0 in parts:
 im=Image.open(os.path.join(base,'素材',rel)).convert('RGB').resize((946,2048),Image.Resampling.LANCZOS)
 im=im.crop((0,y0,946,1812)).resize((W,round((1812-y0)*W/946)),Image.Resampling.LANCZOS); ims.append(im)
starts=[]; off=0
for im in ims: starts.append(off); off+=im.height
canvas=Image.new('RGB',(W,off),(235,235,235)); off=0
for im in ims: canvas.paste(im,(0,off)); off+=im.height
arr=np.asarray(canvas); x1,x2=130,820; q=arr[:,x1:x2,:].astype(np.int16)
# Detect filled chat bubbles by their green/white fill and attached photos by saturated pixels.
green=(q[:,:,1]>165)&(q[:,:,1]-q[:,:,0]>25)&(q[:,:,1]-q[:,:,2]>40)
white=(q[:,:,0]>245)&(q[:,:,1]>245)&(q[:,:,2]>245)
sat=((q.max(2)-q.min(2))>42)&(q.max(2)<247)

def runs(mask, threshold, min_len, merge_gap=8):
 counts=mask.sum(1); active=counts>threshold; ix=np.flatnonzero(np.diff(np.r_[False,active,False].astype(np.int8)))
 raw=[(int(ix[k]),int(ix[k+1])) for k in range(0,len(ix),2) if ix[k+1]-ix[k]>=min_len]
 merged=[]
 for a,b in raw:
  if merged and a-merged[-1][1]<=merge_gap: merged[-1]=(merged[-1][0],b)
  else: merged.append((a,b))
 return merged

def bbox_for(mask,a,b):
 yy,xx=np.where(mask[a:b]);
 if len(xx)==0:return (x1,a,x2,b)
 return (x1+int(xx.min()),a+int(yy.min()),x1+int(xx.max())+1,a+int(yy.max())+1)
text_events=[]
for kind,mask,thr in [('green',green,18),('white',white,24)]:
 for a,b in runs(mask,thr,45,9):
  box=bbox_for(mask,a,b); bx1,by1,bx2,by2=box
  # A largely colorful region is a photo/meme, even if its background includes white.
  sm=sat[max(0,a):min(len(sat),b),max(0,bx1-x1):min(sat.shape[1],bx2-x1)]
  colored_rows=int((sm.sum(1)>14).sum()) if sm.size else 0
  if kind=='white' and colored_rows>max(28,(b-a)*0.34):
   continue
  bw=max(1,bx2-bx1); bh=max(1,by2-by1); lines=max(1,round((bh-50)/55))
  chars=max(2,math.ceil(max(35,bw-72)/42)*lines)
  dwell=min(5.5,max(1.5,1.15+chars/4.3))
  text_events.append({'y':(by1+by2)/2,'box':box,'kind':kind,'dwell':dwell,'chars':chars})
# Detect distinct photo/meme rectangles; discard color runs already contained in a detected text bubble.
visual_events=[]
for a,b in runs(sat,34,38,10):
 box=bbox_for(sat,a,b); bx1,by1,bx2,by2=box
 # avoid specks, avatars, and tiny colorful UI fragments
 if bx2-bx1<70 or by2-by1<45: continue
 overlaps=False
 for e in text_events:
  tx1,ty1,tx2,ty2=e['box']; inter=max(0,min(by2,ty2)-max(by1,ty1)); smaller=min(by2-by1,ty2-ty1)
  if inter>max(20,smaller*.28): overlaps=True; break
 if not overlaps: visual_events.append({'y':(by1+by2)/2,'box':box,'kind':'embedded_visual','dwell':0.7})
events=text_events+visual_events
# Add the four previously approved short illustrative/meme inserts at their related conversation beats.
insert_specs=[(max(0,starts[1]-280),'而外素材/而外素材4.PNG'),(max(0,starts[4]-120),'而外素材/而外素材2.jpg'),(min(canvas.height-H,starts[7]+730),'而外素材/而外素材3.PNG'),(min(canvas.height-H,starts[8]+450),'而外素材/而外素材1.PNG')]
for y,rel in insert_specs: events.append({'y':float(y),'box':None,'kind':'insert','rel':rel,'dwell':0.7})
events.sort(key=lambda e:e['y'])
# Collapse near-identical detections while retaining the larger or text-based event.
clean=[]
for e in events:
 if clean and abs(e['y']-clean[-1]['y'])<32 and e['kind']!='insert' and clean[-1]['kind']!='insert':
  old=clean[-1]
  if e['kind']=='white' or (e['box'] and old['box'] and (e['box'][3]-e['box'][1])>(old['box'][3]-old['box'][1])): clean[-1]=e
 else: clean.append(e)
events=clean; max_y=max(0,canvas.height-H)
print('Recognized',len(text_events),'text bubbles,',len(visual_events),'embedded visual blocks, and',len(insert_specs),'cutaways; total stops',len(events),flush=True)
cmd=[ff,'-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','15','-pix_fmt','yuv420p','-movflags','+faststart',out]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE); frame_count=0

def emit(im):
 global frame_count
 p.stdin.write(im.tobytes()); frame_count+=1

def hold(im,sec):
 for _ in range(max(1,round(sec*FPS))): emit(im)

def frame_at(y):
 y=max(0,min(max_y,round(y))); return canvas.crop((0,y,W,y+H))

def move(y0,y1,idx):
 d=y1-y0
 if abs(d)<1:return
 # A calm but readable travel speed; alternate quadratic and cubic ease-out at each sentence stop.
 dur=max(.32,abs(d)/190); n=max(1,round(dur*FPS)); power=2 if idx%2 else 3
 for f in range(n):
  t=(f+1)/n; e=1-(1-t)**power; emit(frame_at(y0+d*e))

def insert_frame(rel,sec):
 src=Image.open(os.path.join(base,'素材',rel)).convert('RGB')
 cover=max(W/src.width,H/src.height); bg=src.resize((round(src.width*cover),round(src.height*cover)),Image.Resampling.LANCZOS)
 l=(bg.width-W)//2; top=(bg.height-H)//2; bg=bg.crop((l,top,l+W,top+H)).filter(ImageFilter.GaussianBlur(26)); bg=ImageEnhance.Brightness(bg).enhance(.5)
 fit=min(W/src.width,H/src.height); fw,fh=round(src.width*fit),round(src.height*fit); fg=src.resize((fw,fh),Image.Resampling.LANCZOS)
 n=max(1,round(sec*FPS))
 for f in range(n):
  t=(f+1)/n; z=1+.03*(1-(1-t)**3); zw,zh=round(fw*z),round(fh*z); zi=fg.resize((zw,zh),Image.Resampling.LANCZOS)
  fr=bg.copy(); fr.paste(zi,((W-zw)//2,(H-zh)//2)); emit(fr)

cur=0.0; hold(frame_at(0),.6)
for idx,e in enumerate(events,1):
 if e['kind']=='insert': target=max(0,min(max_y,e['y']-H/2))
 else:
  x1b,y1b,x2b,y2b=e['box']; target=max(0,min(max_y,(y1b+y2b)/2-H/2))
 move(cur,target,idx); cur=target
 if e['kind']=='insert': insert_frame(e['rel'],e['dwell'])
 elif e['kind']=='embedded_visual': hold(frame_at(cur),.7)
 else: hold(frame_at(cur),e['dwell'])
hold(frame_at(max_y),.8)
p.stdin.close(); err=p.stderr.read().decode('utf-8','replace'); code=p.wait()
if code: raise RuntimeError(f'ffmpeg exited {code}: {err[-4000:]}')
print(f'Wrote {out}; {frame_count} frames; {frame_count/FPS:.2f}s; 960x720; silent; sentence-by-sentence quadratic/cubic ease-out.')
