from PIL import Image, ImageDraw
import os, glob
root=r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机'
files=glob.glob(root+r'\主素材\*.PNG')+glob.glob(root+r'\内容素材\*.JPG')
out=Image.new('RGB',(1200,((len(files)+3)//4)*520),'#333')
d=ImageDraw.Draw(out)
for i,f in enumerate(files):
 im=Image.open(f).convert('RGB'); im.thumbnail((285,475)); x=(i%4)*300+(300-im.width)//2; y=(i//4)*520+30; out.paste(im,(x,y)); d.text(((i%4)*300+8,(i//4)*520+8),os.path.basename(f),fill='white')
out.save(root+r'\成品\contact.jpg')
