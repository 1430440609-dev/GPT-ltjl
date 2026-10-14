from PIL import Image, ImageFilter, ImageEnhance
import numpy as np, os, subprocess, sys, math
sys.path.insert(0,r'C:\Users\34652\AppData\Local\Temp\chat-record-video-tools')
import imageio_ffmpeg
base=r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑'; out=os.path.join(base,'成品','聊天记录草剪_逐句底部缓出版.mp4')
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
pad_top=40
padded=Image.new('RGB',(W,canvas.height+pad_top),(235,235,235)); padded.paste(canvas,(0,pad_top)); canvas=padded
starts=[s+pad_top for s in starts]
# Main source 7 contains this attachment across dark and bright bands. Hide its in-chat
# instance during scrolling and show the original crop once as a complete main-source image.
main7_src=Image.open(os.path.join(base,'素材','主素材','7.PNG')).convert('RGB')
sx,sy=main7_src.width/946,main7_src.height/2048
main7_photo=main7_src.crop((round(164*sx),round(583*sy),round(518*sx),round(1054*sy)))
main7_top=starts[6]+round((583-580)*W/946)
main7_bottom=starts[6]+round((1054-580)*W/946)
main7_left=round(164*W/946); main7_right=round(518*W/946)
canvas.paste((235,235,235),(main7_left,main7_top,main7_right,main7_bottom))
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
  dwell=max(0.55,0.20+chars/11.2)  # approx 4 Chinese chars/s at normal pace, played at 2.8x
  text_events.append({'y':(by1+by2)/2,'box':box,'kind':kind,'dwell':dwell,'chars':chars})
# Detect complete photo/meme attachments. Saturated parts inside one photo can be
# split into several row-runs, so join vertically adjacent bands with matching width.
visual_boxes=[]
for a,b in runs(sat,34,38,10):
 box=bbox_for(sat,a,b); bx1,by1,bx2,by2=box
 if bx2-bx1<70 or by2-by1<25: continue
 overlaps=False
 for e in text_events:
  tx1,ty1,tx2,ty2=e['box']; inter=max(0,min(by2,ty2)-max(by1,ty1)); smaller=min(by2-by1,ty2-ty1)
  if inter>max(20,smaller*.28): overlaps=True; break
 if not overlaps: visual_boxes.append(box)
visual_boxes.sort(key=lambda b:b[1])
merged_boxes=[]
for box in visual_boxes:
 bx1,by1,bx2,by2=box
 if merged_boxes:
  ox1,oy1,ox2,oy2=merged_boxes[-1]
  xover=max(0,min(bx2,ox2)-max(bx1,ox1)); ratio=xover/max(1,min(bx2-bx1,ox2-ox1))
  if (by1-oy2<=110 or (7100<=oy1<7350 and 7450<=by1<7700)) and ratio>=0.55:
   merged_boxes[-1]=(min(bx1,ox1),oy1,max(bx2,ox2),max(by2,oy2)); continue
 merged_boxes.append(box)
visual_events=[]
for box in merged_boxes:
 bx1,by1,bx2,by2=box
 # Stop with the attachment's lower edge at the bottom so the complete source image is visible.
 meme=(by1<1500) or (2800<=by1<3500) or (by1>=10000)
 visual_events.append({'y':float(by2),'box':box,'kind':'embedded_visual','enter':0.5,'dwell':0.3})
events=text_events+visual_events
events.append({'y':float(main7_bottom),'box':None,'kind':'insert','image':main7_photo,'main_image':True,'enter':0.5,'dwell':0.3})
# Add the previously approved short illustrative/meme inserts at their related conversation beats.
insert_specs=[(min(canvas.height-H,starts[7]+110),'而外素材/而外素材2.jpg'),(min(canvas.height-H,starts[7]+730),'而外素材/而外素材3.PNG'),(min(canvas.height-H,starts[8]+450),'而外素材/而外素材1.PNG')]
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

def move(y0,y1,idx,duration=None):
 d=y1-y0
 if abs(d)<1:return
 # Keep ordinary dialogue travel calm; visual events slide fully into view within their specified time.
 dur=max(.01,duration) if duration is not None else max(.32,abs(d)/190)
 n=max(1,round(dur*FPS)); power=2 if idx%2 else 3
 for f in range(n):
  t=(f+1)/n; e=1-(1-t)**power; emit(frame_at(y0+d*e))

def insert_frame(event,sec):
 src=event.get('image')
 if src is None: src=Image.open(os.path.join(base,'素材',event['rel'])).convert('RGB')
 # Keep the full source image inside the 4:3 frame without cropping.
 bg=Image.new('RGB',(W,H),(32,32,32))
 fit=min(W/src.width,H/src.height); fw,fh=round(src.width*fit),round(src.height*fit)
 fg=src.resize((fw,fh),Image.Resampling.LANCZOS)
 if event.get('main_image'):
  n=max(1,round(event['enter']*FPS))
  for f in range(n):
   t=(f+1)/n; eased=1-(1-t)**3; slide=round((1-eased)*96)
   fr=bg.copy(); fr.paste(fg,((W-fw)//2,(H-fh)//2+slide)); emit(fr)
  stable=bg.copy(); stable.paste(fg,((W-fw)//2,(H-fh)//2)); hold(stable,sec)
 else:
  bg.paste(fg,((W-fw)//2,(H-fh)//2)); hold(bg,sec)

cur=0.0; hold(frame_at(0),.55)
for idx,e in enumerate(events,1):
 if e['kind']=='insert': target=max(0,min(max_y,e['y']-H+4))
 else:
  x1b,y1b,x2b,y2b=e['box']; raw_target=y2b-H+4
  # The opening source already shows the greeting above the first full sentence.
  # Keep it as context; begin sentence-by-sentence holds when the current line can sit near the lower edge.
  if raw_target<0 and y2b<H-80: continue
  target=max(0,min(max_y,raw_target))
 move(cur,target,idx,e.get('enter')); cur=target
 if e['kind']=='insert': insert_frame(e,e['dwell'])
 elif e['kind']=='embedded_visual': hold(frame_at(cur),e['dwell'])
 else: hold(frame_at(cur),e['dwell'])
hold(frame_at(max_y),.8)
p.stdin.close(); err=p.stderr.read().decode('utf-8','replace'); code=p.wait()
if code: raise RuntimeError(f'ffmpeg exited {code}: {err[-4000:]}')
print(f'Wrote {out}; {frame_count} frames; {frame_count/FPS:.2f}s; 960x720; silent; sentence-by-sentence quadratic/cubic ease-out.')


