from PIL import Image,ImageDraw
from pathlib import Path
r=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机\成品')
fs=sorted(r.glob('v2_*.jpg'),key=lambda x:int(x.stem.split('_')[1])); out=Image.new('RGB',(1200,((len(fs)+3)//4)*270),'#333'); d=ImageDraw.Draw(out)
for i,f in enumerate(fs):
 im=Image.open(f); im.thumbnail((290,225));x=(i%4)*300+(300-im.width)//2;y=(i//4)*270+30;out.paste(im,(x,y));d.text(((i%4)*300+8,(i//4)*270+5),f.name,fill='white')
out.save(r/'preview_v2.jpg')
