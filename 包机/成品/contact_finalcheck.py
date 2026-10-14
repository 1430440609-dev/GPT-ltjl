from PIL import Image,ImageDraw
from pathlib import Path
root=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机\成品')
files=sorted(root.glob('finalcheck_*.jpg'),key=lambda p:float(p.stem.replace('finalcheck_','').replace('_','.')))
w,h=360,290
out=Image.new('RGB',(w*3,h*((len(files)+2)//3)),(35,35,35)); d=ImageDraw.Draw(out)
for i,p in enumerate(files):
 im=Image.open(p).convert('RGB'); im.thumbnail((w-8,h-35)); x=(i%3)*w; y=(i//3)*h; out.paste(im,(x+4,y+28)); d.text((x+5,y+7),p.stem.replace('finalcheck_',''),fill='white')
out.save(root/'contact_finalcheck.jpg')
