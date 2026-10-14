from PIL import Image, ImageDraw
from pathlib import Path
root=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机\主素材')
imgs=[]
for p in sorted(root.glob('*.PNG')):
 im=Image.open(p); im.thumbnail((260,560)); imgs.append((p.name,im.copy()))
out=Image.new('RGB',(1040,1200),(40,40,40)); d=ImageDraw.Draw(out)
for i,(name,im) in enumerate(imgs):
 x=(i%4)*260; y=(i//4)*600; out.paste(im,(x,y+28)); d.text((x+5,y+5),name,fill='white')
out.save(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机\成品\source_contact.jpg')
