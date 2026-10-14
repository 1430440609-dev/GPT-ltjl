import math, subprocess, time, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机')
OUT=ROOT/'成品'/'包机_草剪_顺序缓出_内容静音版.mp4'
TMP=ROOT/'.asr_tmp'
PAUSED_AUDIO=TMP/'包机配音_内容插入静音.wav'
MIXED_AUDIO=TMP/'包机配音_内容2配乐混合.wav'
FINAL_AUDIO=TMP/'包机最终混音.wav'
AMBIENT_AUDIO=ROOT/'内容素材'/'包机短视频氛围配乐.mp3'
FFMPEG=Path(r'C:\Users\34652\AppData\Local\Temp\chat-record-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe')
W,H,FPS=1440,1080,60
SOURCE_DUR=63.007
BG=(31,32,34)
MOVE=0.46
SAMPLE_RATE=44100

# The cues are in voiceover time and follow the message order in the eight source screenshots.
cues=[
 (0.00,0,552,2),(2.10,0,726,3),(3.02,0,1290,2),(4.76,0,1464,3),(6.58,0,1638,2),(8.58,0,1944,3),
 (9.80,1,1203,2),(9.801,1,1449,3),(10.42,1,1449,3),(11.98,1,1622,2),(14.14,1,1796,3),(16.24,1,1970,2),
 (16.82,2,786,3),(18.10,2,959,2),(19.74,2,1197,3),(23.14,2,1810,2),(23.141,2,1982,3),(24.60,2,2156,2),(25.42,2,2156,3),
 (25.96,3,1093,3),(26.70,3,1330,2),(28.86,3,1678,3),(30.68,3,1852,2),(32.70,3,2158,3),
 (33.98,4,932,2),(35.02,4,932,3),(35.76,4,1625,2),
 (37.86,5,412,3),(39.08,5,412,2),(40.40,5,586,3),(41.98,5,760,2),(43.34,5,934,3),(45.02,5,1887,2),
 (46.32,5,1900,3),(46.98,5,1900,2),(49.50,5,2137,3),(50.70,5,2137,2),(52.02,5,2137,3),
 (53.40,5,2307,2),(54.78,6,1424,3),(55.90,6,1598,2),(57.24,6,1598,3),(57.90,6,1772,2),
 (59.70,7,1037,3),(60.90,7,1211,2),(62.18,7,2307,3)]

# Each main screenshot cover has a 0.5s eased reveal + 0.3s hold. Still inserts
# likewise use 0.7s eased entry + 2.0s full display. Video 2 plays at 2x.
VIDEO_DUR=20.67/2
INSERTS=[
 {'at':9.80,'cover':.80,'media':2.70,'kind':'still1'},
 {'at':23.14,'cover':.80,'media':VIDEO_DUR,'kind':'video2'},
 {'at':45.02,'cover':.80,'media':2.70,'kind':'still3'},
]
for item in INSERTS:
 item['duration']=item['cover']+item['media']
OUT_DUR=SOURCE_DUR+sum(x['duration'] for x in INSERTS)
N=round(OUT_DUR*FPS)

SCALE=W/1125
# These are the vertical scroll offsets where consecutive source screenshots
# overlap. Stitch their shared chat area into one continuous conversation image.
# Pixel-matched vertical scroll distances between the original screenshots.
# Aligning the shared chat rows prevents a visible jump when the viewport hands
# off from one untouched source screenshot to the next.
SOURCE_OFFSETS=[0,1204,2564,3802,5202,6588,7650,8560]
PAGE_OFFSETS=[round(x*SCALE) for x in SOURCE_OFFSETS]
source_pages=[]
for i in range(8):
 im=Image.open(ROOT/'主素材'/f'{i+1}.PNG').convert('RGB')
 im=im.resize((W,round(im.height*SCALE)),Image.Resampling.LANCZOS)
 source_pages.append(np.asarray(im,dtype=np.uint8))
pages=source_pages  # preserve every source screenshot pixel; camera motion only changes the viewport

# Treat the chat as one continuous long screenshot. Keep the opening phone
# header from page 1, but use only the chat body (y=300..2160) from every page;
# the fixed WeChat composer occupies the excluded bottom strip in all sources.
SAFE_CHAT_END=round(2160*SCALE)
SAFE_CHAT_START=round(300*SCALE)
GLOBAL_END=PAGE_OFFSETS[-1]+SAFE_CHAT_END
chat_strip=np.empty((GLOBAL_END,W,3),dtype=np.uint8)
chat_strip[:]=source_pages[0][0,0]
for pi,arr in enumerate(source_pages):
 local_start=0 if pi==0 else SAFE_CHAT_START
 local_end=min(SAFE_CHAT_END,arr.shape[0])
 dst_start=PAGE_OFFSETS[pi]+local_start
 dst_end=PAGE_OFFSETS[pi]+local_end
 chat_strip[dst_start:dst_end]=arr[local_start:local_end]

def page_y(pi,y):
 return round(y*SCALE)

def frame_at(global_top):
 # The stitched strip omits every composer/input row, so camera movement and
 # screenshot handoffs remain continuous without painting over chat content.
 top=int(round(global_top))
 if top<0:
  frame=np.empty((H,W,3),dtype=np.uint8); frame[:]=chat_strip[0,0]
  pad=min(H,-top); frame[pad:]=chat_strip[:H-pad]
  return Image.fromarray(frame)
 top=min(top,max(0,GLOBAL_END-H))
 return Image.fromarray(chat_strip[top:top+H].copy())

def ease(v,p):
 v=max(0,min(1,v)); return 1-(1-v)**p

scroll=[]
for t,pi,y,p in cues:
 # y marks the current bubble. Leave room for the whole bubble near the lower frame edge.
 target=max(-H+1,min(GLOBAL_END-H,
                     PAGE_OFFSETS[pi]+page_y(pi,y)-(H-60)))
 # Hold on the RR送机 line and its complete embedded video thumbnail until the insert.
 # At the RR送机 line, keep the whole embedded flight-video preview in view;
 # do not scroll down to the following two replies before the external insert.
 if abs(t-19.74)<1e-6 or abs(t-23.14)<1e-6: target=PAGE_OFFSETS[pi]+1240
 scroll.append((t,pi,target,p))

def cue_at(t):
 return next(c for c in scroll if abs(c[0]-t)<1e-6)

def crop_page(pi,off):
 arr=pages[pi]; off=max(-H+1,min(arr.shape[0]-H,int(round(off))))
 if off>=0: return Image.fromarray(arr[off:off+H].copy())
 top=-off; frame=np.empty((H,W,3),dtype=np.uint8); frame[:]=arr[0,0]
 frame[top:]=arr[:H-top]
 return Image.fromarray(frame)

def vertical_wipe(a,b,q):
 cut=H-round(H*ease(q,2))
 out=a.copy()
 if cut<H: out.paste(b.crop((0,cut,W,H)),(0,cut))
 return out

def camera(src_t,settled=False):
 k=0
 for j in range(1,len(scroll)):
  if scroll[j][0]<=src_t: k=j
  else: break
 cur=scroll[k]
 # The third insert's cover already scrolls into this hotel frame. Hold it when
 # narration resumes so the same scroll does not replay after the insert.
 if abs(cur[0]-45.02)<1e-6: return frame_at(cur[2])
 if settled or k==0: return frame_at(cur[2])
 prev=scroll[k-1]
 q=ease((src_t-cur[0])/MOVE,cur[3])
 return frame_at(prev[2]+(cur[2]-prev[2])*q)

def cover_frame(index,elapsed):
 # Reveal the corresponding embedded main-screenshot image first, then hold it fully visible.
 start_t=[8.58,19.74,43.34][index]
 target_pi=[1,2,5][index]
 target_y=[520,1290,1090][index]
 start_page=cue_at(start_t)[1]
 start=cue_at(start_t)[2]
 target=PAGE_OFFSETS[target_pi]+(1240 if index==1 else page_y(target_pi,target_y))
 if index==2: target=cue_at(45.02)[2]
 q=ease(elapsed/MOVE,3)
 return frame_at(target if elapsed>=MOVE else start+(target-start)*q)

def contain(im):
 im=im.convert('RGB'); s=min((W-100)/im.width,(H-80)/im.height)
 im=im.resize((round(im.width*s),round(im.height*s)),Image.Resampling.LANCZOS)
 f=Image.new('RGB',(W,H),BG); f.paste(im,((W-im.width)//2,(H-im.height)//2)); return f

def price_frame(im,which):
 f=contain(im); d=ImageDraw.Draw(f); iw,ih=im.size
 s=min((W-100)/iw,(H-80)/ih); ox=(W-iw*s)/2; oy=(H-ih*s)/2
 if which=='flight': r=(int(ox+iw*.75*s),int(oy+ih*.49*s),int(ox+iw*.995*s),int(oy+ih*.96*s))
 else: r=(int(ox+iw*.28*s),int(oy+ih*.88*s),int(ox+iw*.92*s),int(oy+ih*.995*s))
 d.rounded_rectangle(r,radius=22,outline=(255,191,56),width=8)
 return f

still1=price_frame(Image.open(ROOT/'内容素材'/'内容素材1.JPG'),'flight')
still3=price_frame(Image.open(ROOT/'内容素材'/'内容素材3.JPG'),'hotel')

def zoom_in(frame,elapsed):
 q=ease(elapsed/.70,3); scale=.92+.08*q
 nw,nh=round(W*scale),round(H*scale)
 im=frame.resize((nw,nh),Image.Resampling.LANCZOS)
 out=Image.new('RGB',(W,H),BG); out.paste(im,((W-nw)//2,(H-nh)//2)); return out

def build_paused_audio():
 src=ROOT/'配音'/'包机配音.MP3'
 cmd=[str(FFMPEG),'-v','error','-i',str(src),'-f','s16le','-acodec','pcm_s16le','-ac','2','-ar',str(SAMPLE_RATE),'pipe:1']
 raw=subprocess.run(cmd,stdout=subprocess.PIPE,check=True).stdout
 frame_bytes=4
 chunks=[]; cursor=0
 for item in INSERTS:
  p=round(item['at']*SAMPLE_RATE)*frame_bytes
  chunks.append(raw[cursor:p]); cursor=p
  silence=round(item['duration']*SAMPLE_RATE)
  chunks.append(bytes(silence*frame_bytes))
 chunks.append(raw[cursor:])
 pcm=b''.join(chunks)
 with wave.open(str(PAUSED_AUDIO),'wb') as wf:
  wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE); wf.writeframes(pcm)

build_paused_audio()

# Crossfade the supplied 内容素材2 music against the quiet generated full-video bed.
video2_transition_start=INSERTS[1]['at']+INSERTS[0]['duration']
video2_out_start=video2_transition_start+INSERTS[1]['cover']
video2_out_end=video2_out_start+VIDEO_DUR
music_delay_ms=round(video2_out_start*1000)
local_music_fade=0.8
mix_filter=(f"[1:a]atrim=duration={VIDEO_DUR:.6f},asetpts=PTS-STARTPTS,"
            f"volume=0.55,afade=t=in:st=0:d={local_music_fade:.3f},"
            f"afade=t=out:st={VIDEO_DUR-local_music_fade:.3f}:d={local_music_fade:.3f},"
            f"adelay={music_delay_ms}|{music_delay_ms}[bgm];"
            "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]")
mix_cmd=[str(FFMPEG),'-y','-v','error','-i',str(PAUSED_AUDIO),
         '-i',str(ROOT/'内容素材'/'内容素材2背景音乐.MP3'),
         '-filter_complex',mix_filter,'-map','[aout]','-c:a','pcm_s16le',str(MIXED_AUDIO)]
subprocess.run(mix_cmd,check=True)

# The generated music bed stays quiet across the full video. It dips during
# the 内容素材2 transition, then rises as the dedicated track fades out.
if not AMBIENT_AUDIO.exists():
 raise FileNotFoundError(f'Place the generated full-video bed at: {AMBIENT_AUDIO}')
base_bed=0.24; ducked_bed=0.0432
ramp_in_start=video2_transition_start; ramp_in_end=video2_out_start
ramp_out_start=video2_out_end; ramp_out_end=video2_out_end+INSERTS[1]['cover']
volume_expr=(f"if(lt(t,{ramp_in_start:.6f}),{base_bed:.6f},"
            f"if(lt(t,{ramp_in_end:.6f}),{base_bed:.6f}-({base_bed-ducked_bed:.6f})*(t-{ramp_in_start:.6f})/{INSERTS[1]['cover']:.6f},"
            f"if(lt(t,{ramp_out_start:.6f}),{ducked_bed:.6f},"
            f"if(lt(t,{ramp_out_end:.6f}),{ducked_bed:.6f}+({base_bed-ducked_bed:.6f})*(t-{ramp_out_start:.6f})/{INSERTS[1]['cover']:.6f},{base_bed:.6f}))))")
final_filter=(f"[1:a]atrim=duration={OUT_DUR:.6f},asetpts=PTS-STARTPTS,"
              f"afade=t=in:st=0:d=1.2,afade=t=out:st={OUT_DUR-1.2:.6f}:d=1.2,"
              f"volume='{volume_expr}':eval=frame[bed];"
              "[0:a][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]")
final_cmd=[str(FFMPEG),'-y','-v','error','-i',str(MIXED_AUDIO),'-stream_loop','-1',
           '-i',str(AMBIENT_AUDIO),'-filter_complex',final_filter,'-map','[aout]',
           '-c:a','pcm_s16le',str(FINAL_AUDIO)]
subprocess.run(final_cmd,check=True)
out_inserts=[]; cum=0.0
for i,item in enumerate(INSERTS):
 out_start=item['at']+cum
 out_inserts.append((out_start,out_start+item['cover'],out_start+item['duration'],i,item))
 cum+=item['duration']

def timeline(sec):
 prior=0.0
 for start,cover_end,end,index,item in out_inserts:
  if start<=sec<end:
   if sec<cover_end: return ('cover',index,item['at'],sec-start)
   return (item['kind'],index,item['at'],sec-cover_end)
  if end<=sec<end+1.5/FPS: return ('resume',index,item['at'],None)
  if sec>=end: prior+=item['duration']
  else: break
 return ('main',None,sec-prior,None)

vid_proc=None
def start_video2():
 global vid_proc
 vf='setpts=PTS/2,fps=60,scale=1440:1080:force_original_aspect_ratio=decrease,pad=1440:1080:(ow-iw)/2:(oh-ih)/2:color=0x1f2022'
 args=[str(FFMPEG),'-v','error','-i',str(ROOT/'内容素材'/'内容素材2.MP4'),'-vf',vf,'-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
 vid_proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=10**7)

args=[str(FFMPEG),'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(FINAL_AUDIO),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','15','-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','192k','-t',f'{OUT_DUR:.3f}','-movflags','+faststart',str(OUT)]
enc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,bufsize=10**7)
t0=time.time(); last_video=None
for i in range(N):
 sec=i/FPS; kind,index,src_t,elapsed=timeline(sec)
 if kind=='main': frame=camera(src_t)
 elif kind=='resume': frame=camera(src_t,settled=True)
 elif kind=='cover': frame=cover_frame(index,elapsed)
 elif kind=='still1': frame=zoom_in(still1,elapsed)
 elif kind=='still3': frame=zoom_in(still3,elapsed)
 elif kind=='video2':
  if vid_proc is None: start_video2()
  raw=vid_proc.stdout.read(W*H*3)
  if len(raw)==W*H*3: last_video=Image.frombytes('RGB',(W,H),raw); frame=last_video
  elif last_video is not None: frame=last_video
  else: frame=Image.new('RGB',(W,H),BG)
 enc.stdin.write(frame.tobytes())
 if (i+1)%600==0: print(f'{i+1}/{N} frames ({(i+1)/FPS:.1f}s)',flush=True)
enc.stdin.close(); err=enc.stderr.read().decode('utf-8','replace'); ret=enc.wait()
if vid_proc is not None:
 try: vid_proc.stdout.close()
 except Exception: pass
 vid_proc.wait(timeout=10)
if ret!=0: raise RuntimeError(f'ffmpeg encode failed {ret}: {err[-4000:]}')
print(f'RENDER_OK {OUT} bytes={OUT.stat().st_size} duration={OUT_DUR:.3f}s elapsed={time.time()-t0:.1f}s frames={N}')






