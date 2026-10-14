from PIL import Image
from pathlib import Path
import numpy as np
root=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机\主素材')
cues={0:[552,726,1290,1464,1638,1944],1:[1308,1449,1623,1797,1971],2:[786,960,1197,1833],3:[1093,1330,1678,1852,2158],4:[932,1625],5:[1799,1973,2147,935,1635,1901,2138],6:[1251,1425,1599,1773],7:[1038,1212,2130]}
def groups(mask):
 ys=np.where(mask)[0]; out=[]
 if not len(ys):return out
 a=b=int(ys[0])
 for y in map(int,ys[1:]):
  if y-b<=18:b=y
  else:
   if b-a>25:out.append((a,b))
   a=b=y
 if b-a>25:out.append((a,b))
 return out
for i in range(8):
 a=np.array(Image.open(root/f'{i+1}.PNG').convert('RGB')); h,w,_=a.shape
 x1,x2=150,w-100
 c=a[:,x1:x2]
 white=(c[:,:,0]>248)&(c[:,:,1]>248)&(c[:,:,2]>248)
 green=(c[:,:,1].astype(int)-c[:,:,0].astype(int)>25)&(c[:,:,1].astype(int)-c[:,:,2].astype(int)>10)&(c[:,:,1]>150)
 rows=np.sum(white,axis=1)>250
 rows2=np.sum(green,axis=1)>100
 g=groups(rows)|groups(rows2) if False else sorted(groups(rows)+groups(rows2))
 merged=[]
 for x in g:
  if merged and x[0]-merged[-1][1]<50:merged[-1]=(merged[-1][0],max(merged[-1][1],x[1]))
  else:merged.append(x)
 print('\nPAGE',i+1,'height',h,'segments',merged)
 for cue in cues[i]:
  # convert cue reference x 1125 coordinates to raw screenshot y
  yy=cue*w/1125
  near=min(merged,key=lambda z:abs((z[0]+z[1])/2-yy)) if merged else None
  print(cue,'=>',round(yy),near)
