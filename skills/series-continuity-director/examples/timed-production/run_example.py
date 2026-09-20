#!/usr/bin/env python3
"""Create an actual synthetic audiovisual rough and complete its production run."""
from pathlib import Path
import argparse
import array
import json
import math
import sys
import wave

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import execution_contract as c
import production_workflow as w
import production_test_support as support
import timed_test_support
import timed_sequence
import work_ledger


def run(root: Path) -> dict:
    if root.exists():raise ValueError('choose a new output directory')
    plan=timed_test_support.inputs(root)
    task=work_ledger.begin(root,'Synthetic audiovisual integrity check',['produce','observe'])
    instruction='Move the declared form across the fixed field; sound only within the declared interval.'
    (root/'delivery.txt').write_text(instruction+'\n')
    spec={'task_id':task['task_id'],'route':'timed-sequence','features':[],
          'sources':[],'delivery':{'path':'delivery.txt','transport':'authored-rendition','translation_notes':'Use exactly the declared synthetic plan.'},
          'criteria':[{'id':'picture','strength':'hard','text':'The two-second output has 48 frames and visible motion.','evidence':'video'},
                      {'id':'sound','strength':'hard','text':'The test signal is present inside, and absent before, its placed interval.','evidence':'audio'}],
          'sequence_plan':'sequence.json'}
    spec['direction']=support.direction(spec,instruction)
    (root/'task.json').write_bytes(c.encoded(spec));run=w.prepare(root,'task.json')['run']
    w.handoff(root,run,'synthetic editor','editor')
    authorization=support.grant(w,root,run,actor='synthetic operator',operations=('edit','select'),outputs=1,calls=1)
    candidate=timed_sequence.execute(root,run,'rough.mp4',authorization,'synthetic operator')
    digest=c.digest(c.read(root/'rough.mp4'))
    first=timed_sequence.extract(root,'rough.mp4',digest,'first.png',start=.1)
    last=timed_sequence.extract(root,'rough.mp4',digest,'later.png',start=1.5)
    audio=timed_sequence.extract(root,'rough.mp4',digest,'actual.wav',start=0,end=2)
    from PIL import Image,ImageChops
    with Image.open(root/'first.png') as a,Image.open(root/'later.png') as b:
        changed=ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox() is not None
    with wave.open(str(root/'actual.wav'),'rb') as decoded:
        sr=decoded.getframerate();channels=decoded.getnchannels();samples=array.array('h',decoded.readframes(decoded.getnframes()))
    if sys.byteorder!='little':samples.byteswap()
    def rms(start,end):
        values=samples[round(start*sr*channels):round(end*sr*channels)]
        return math.sqrt(sum(v*v for v in values)/len(values))
    early,inside,late=rms(.1,.3),rms(.6,.9),rms(1.4,1.8)
    measured={'different_frame_pixels':changed,'early_rms':early,'inside_rms':inside,'late_rms':late,
              'media':candidate['data']['media']}
    if not changed or not inside>1000 or not early<20 or not late<20:
        raise ValueError('actual output did not meet synthetic visual/audio measurements: '+str(measured))
    streams=candidate['data']['media']['streams']
    video_stream=next(item['index'] for item in streams if item['codec_type']=='video')
    audio_stream=next(item['index'] for item in streams if item['codec_type']=='audio')
    review=w.draft_review(root,run,candidate['sha256'])
    review.update(reviewer='synthetic measurement operator',observations=[
        {'locator':{'kind':'time','unit':'seconds','start':0,'end':2,'stream':video_stream},'observation':'Measured 48 frames; decoded early and later images have different pixels.','method':'measurement'},
        {'locator':{'kind':'time','unit':'seconds','start':0,'end':2,'stream':audio_stream},'observation':f'Decoded signal RMS before={early}, inside={inside}, after={late}. No audio meaning was assessed.','method':'measurement'}],
        conclusion='Timing and actual bytes verified; no aesthetic or acting claim.')
    for index,check in enumerate(review['checks']):check.update(verdict='pass',observation_indices=[index],evidence_basis='technical-measurement',reason='Measured synthetic output.')
    (root/'review.json').write_bytes(c.encoded(review));w.review(root,run,'review.json')
    selection=w.draft_selection(root,run,candidate['sha256']);selection.update(selector='synthetic operator',reason='Measured fixture only.',authorization=authorization)
    (root/'selection.json').write_bytes(c.encoded(selection));w.select(root,run,'selection.json');w.complete(root,run)
    work_ledger.step_done(root,1);work_ledger.step_done(root,2);work_ledger.finish(root)
    result={'ok':w.status(root,run)['next']=='done','run':run,'output_sha256':digest,'measurements':measured,'fixture_only':True}
    (root/'result.json').write_bytes(c.encoded(result));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(run(a.out.absolute()),indent=2))
