"""Synthetic unpeopled media fixtures, not performance-quality evidence."""
from pathlib import Path
import math
import struct
import wave
from PIL import Image
import execution_contract as c


def inputs(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    Image.new('RGB',(160,90),(16,16,16)).save(root/'field.png')
    Image.new('RGBA',(16,16),(220,40,30,255)).save(root/'form.png')
    with wave.open(str(root/'signal.wav'),'wb') as out:
        out.setparams((1,2,48000,0,'NONE','not compressed'))
        out.writeframes(b''.join(struct.pack('<h',round(9000*math.sin(2*math.pi*440*i/48000))) for i in range(24000)))
    assets=[{'id':'field','path':'field.png','kind':'image','source_clock':None},
            {'id':'form','path':'form.png','kind':'image','source_clock':None},
            {'id':'signal','path':'signal.wav','kind':'audio','source_clock':'signal-source'}]
    for asset in assets:
        asset.update(sha256=c.digest(c.read(root/asset['path'])),limitations=['Synthetic material, no acted expression or semantic sound claim.'])
    def visual(layer,width,height,x,y):
        return {'layer':layer,'width':width,'height':height,'fit':'stretch','x':x,'y':y,'opacity':1}
    plan={'purpose':'Test declared edit timing, explicit movement, layering and audio placement.',
      'clocks':[{'id':'assembly','kind':'edit','unit':'seconds','rate':None},
                {'id':'movement','kind':'performance','unit':'frames','rate':{'numerator':24,'denominator':1}},
                {'id':'signal-source','kind':'source','unit':'seconds','rate':None}],
      'assets':assets,
      'cues':[{'id':'traverse','span':{'clock':'movement','start':0,'end':48},'subjects':['form'],'action':'Cross the fixed field at the declared linear pace.','relations':[]}],
      'constraints':[],
      'placements':[
        {'id':'fixed','asset':'field','source':None,'edit':{'clock':'assembly','start':0,'end':2},'rate':1,'video':visual(0,160,90,[0,0],[0,0]),'audio':None},
        {'id':'moving','asset':'form','source':None,'edit':{'clock':'assembly','start':0,'end':2},'rate':1,'video':visual(1,16,16,[0,120],[30,30]),'audio':None},
        {'id':'sound','asset':'signal','source':{'clock':'signal-source','start':0,'end':.5},'edit':{'clock':'assembly','start':.5,'end':1},'rate':1,'video':None,'audio':{'gain':1}}],
      'story_links':[],
      'cue_links':[{'cue':'traverse','placements':['moving'],'relation':'depicted','limitations':['Linear proxy motion does not represent acted movement.']}],
      'boundaries':[],
      'output':{'clock':'assembly','duration':2,'width':160,'height':90,'fps':{'numerator':24,'denominator':1},'background':'#101010'},
      'limitations':['Technical fixture only. It does not validate acting, meaning of sound or audience response.']}
    (root/'sequence.json').write_bytes(c.encoded(plan))
    return plan
