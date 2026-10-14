from PIL import Image,ImageDraw
from pathlib import Path
root=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机\成品')
files=sorted(root.glob('check_*.jpg'))
out=Image.new('RGB',(1200,((len(files)+2)//3)*290),'#333');d=ImageDraw.Draw(out)
for i,f in enumerate(files):
 im=Image.open(f);im.thumbnail((390,260));x=(i%3)*400+(400-im.width)//2;y=(i//3)*290+25;out.paste(im,(x,y));d.text(((i%3)*400+8,(i//3)*290+5),f.name,fill='white')
out.save(root/'preview_checks.jpg')
