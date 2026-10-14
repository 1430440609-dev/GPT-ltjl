from PIL import Image
from pathlib import Path
root=Path(r'D:\ljl55\Documents\ChatGPT\聊天记录剪辑\包机')
W,H=1440,1080
for i in [1,2]:
 im=Image.open(root/'主素材'/f'{i+1}.PNG').convert('RGB'); im=im.resize((W,round(im.height*W/im.width)))
 im.save(root/'成品'/f'debug_page{i}.jpg')
# expected page-3 crop at the 16.82 cue with updated lower target
im=Image.open(root/'成品'/'debug_page2.jpg')
y=round(959*(W/1125)-(H-60)); y=max(0,y-200)
im.crop((0,y,W,y+H)).save(root/'成品'/'debug_target_16_82.jpg')
print('target',y)
