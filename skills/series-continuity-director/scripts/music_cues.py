#!/usr/bin/env python3
"""Measure conservative music-cue candidates without turning them into edits."""
from __future__ import annotations
import argparse,json,math,shutil,struct,subprocess
from pathlib import Path
from statistics import median
import execution_contract as c
import media_evidence
from operation_log import operation
from io_budget import environment_seconds

SAMPLE_RATE=8000
FRAME=160  # 20 ms

def analyze(root:Path,source:str,sha256:str,stream_index:int)->dict:
    c.sha(sha256);path=c.local(root,source);raw=c.read(path)
    if c.digest(raw)!=sha256:raise ValueError('music source content changed')
    media=media_evidence.inspect(path,raw);streams=[s for s in media.get('streams',[]) if s.get('codec_type')=='audio' and s.get('index')==stream_index]
    if len(streams)!=1:raise ValueError('selected music stream is unavailable')
    exe=shutil.which('ffmpeg')
    if not exe:raise ValueError('ffmpeg is required for music cue analysis')
    cmd=[exe,'-hide_banner','-loglevel','error','-nostdin','-i',str(path),'-map',f'0:{stream_index}','-vn','-ac','1','-ar',str(SAMPLE_RATE),'-f','s16le','-acodec','pcm_s16le','-']
    run=subprocess.run(cmd,capture_output=True,timeout=environment_seconds('PRODUCTION_MEDIA_TIMEOUT_SECONDS'),check=False)
    if run.returncode:raise ValueError('music decode failed: '+run.stderr.decode('utf-8','replace'))
    samples=struct.unpack('<'+'h'*(len(run.stdout)//2),run.stdout[:len(run.stdout)//2*2]) if run.stdout else ()
    energy=[]
    for i in range(0,len(samples)-FRAME+1,FRAME):
        chunk=samples[i:i+FRAME];rms=math.sqrt(sum(x*x for x in chunk)/len(chunk))/32768.0;energy.append(rms)
    if len(energy)<3:
        return {'source':{'path':source,'sha256':sha256,'stream_index':stream_index},'analysis':{'sample_rate':SAMPLE_RATE,'frame_samples':FRAME},'candidates':[],'tempo_candidate_bpm':None,'limitations':['audio is too short for cue analysis']}
    diffs=[0.0]+[max(0.0,energy[i]-energy[i-1]) for i in range(1,len(energy))]
    sorted_d=sorted(diffs);threshold=sorted_d[int(0.9*(len(sorted_d)-1))] if sorted_d else 0
    peaks=[]
    for i in range(1,len(diffs)-1):
        if diffs[i]>=threshold and diffs[i]>diffs[i-1] and diffs[i]>=diffs[i+1] and diffs[i]>0:
            t=i*FRAME/SAMPLE_RATE
            if not peaks or t-peaks[-1][0]>=0.12:peaks.append((t,diffs[i]))
    intervals=[peaks[i][0]-peaks[i-1][0] for i in range(1,len(peaks)) if 0.25<=peaks[i][0]-peaks[i-1][0]<=2.0]
    bpm=60/median(intervals) if len(intervals)>=3 else None
    candidates=[{'id':f'onset-{i+1:03d}','time_seconds':round(t,6),'kind':'onset','strength':round(v,8)} for i,(t,v) in enumerate(peaks)]
    return {'source':{'path':source,'sha256':sha256,'stream_index':stream_index},'analysis':{'sample_rate':SAMPLE_RATE,'frame_samples':FRAME,'method':'positive RMS-energy change peaks'},'candidates':candidates,'tempo_candidate_bpm':round(bpm,4) if bpm else None,
            'limitations':['cue candidates are measurements, not editing instructions','tempo is omitted when stable onset intervals are insufficient']}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['analyze']);p.add_argument('--root',type=Path,required=True);p.add_argument('--source',required=True);p.add_argument('--sha256',required=True);p.add_argument('--stream-index',type=int,required=True);p.add_argument('--out',required=True);a=p.parse_args();root=a.root.absolute()
    try:
        with operation('music_cues.analyze',root=root,arguments=vars(a)) as log:
            result=analyze(root,a.source,a.sha256,a.stream_index);target=c.local(root,a.out,exists=False);c.atomic(target,c.encoded(result));log.artifact(role='music-cue-analysis',path=target,sha256=c.digest(c.read(target)));log.event('music_analyzed',candidates=len(result['candidates']))
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except c.EXPECTED_ERRORS+(subprocess.TimeoutExpired,) as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
