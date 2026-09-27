#!/usr/bin/env python3
"""Compile and verify exact caption cues against a pinned finished master."""
from __future__ import annotations
import argparse, json, re, shutil, subprocess, tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any
import execution_contract as c
import media_evidence
from protocol_contract import validate_against_schema
from operation_log import operation
from io_budget import environment_seconds

ROOT=Path(__file__).resolve().parents[1]


def _time(v: Any, clock: dict[str,Any]) -> Fraction:
    q=Fraction(str(v))
    if clock['unit']=='seconds': return q
    if clock['rate'] is None: raise ValueError('frame caption clock requires an explicit rational rate')
    if q.denominator!=1: raise ValueError('caption frame coordinates must be integers')
    return q/Fraction(clock['rate']['numerator'],clock['rate']['denominator'])


def _srt_time(value: Fraction) -> str:
    if value<0: raise ValueError('caption time cannot be negative')
    ms=int(value*1000+Fraction(1,2)); h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def validate(root: Path, plan: Any) -> dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/caption-track.schema.json');errors=validate_against_schema(plan,schema)
    if errors: raise ValueError('caption track: '+'; '.join(errors))
    source=c.local(root,plan['source_master']['path']); raw=c.read(source)
    if c.digest(raw)!=plan['source_master']['sha256']: raise ValueError('caption source master changed')
    media=media_evidence.inspect(source,raw); duration=media.get('duration')
    clock=plan['clock']; ids=set(); previous=None; cues=[]; findings=[]
    for cue in plan['cues']:
        if cue['id'] in ids: raise ValueError('duplicate caption cue id')
        ids.add(cue['id']); start=_time(cue['start'],clock);end=_time(cue['end'],clock)
        if not 0<=start<end: findings.append({'cue':cue['id'],'code':'CAPTION_TIMING_INVALID'})
        if duration is not None and end>Fraction(str(duration))+Fraction(1,1000): findings.append({'cue':cue['id'],'code':'CUE_CUT_OFF'})
        if previous is not None and start<previous: findings.append({'cue':cue['id'],'code':'CAPTION_OVERLAP'})
        previous=max(previous or end,end)
        if cue['word_timing'] is not None:
            for word in cue['word_timing']:
                ws=_time(word['start'],clock);we=_time(word['end'],clock)
                if not start<=ws<we<=end: findings.append({'cue':cue['id'],'code':'WORD_TIMING_OUTSIDE_CUE','text':word['text']})
        cues.append((cue,start,end))
    return {'status':'pass' if not findings else 'fail','source_sha256':plan['source_master']['sha256'],'source_media':media,'findings':findings,'cue_count':len(cues),'limitations':plan['limitations']}


def compile_sidecar(root: Path, plan: Any, out: Path, fmt: str) -> dict[str,Any]:
    report=validate(root,plan)
    if report['status']!='pass': raise ValueError('caption plan does not pass validation')
    if fmt not in {'srt','vtt'}: raise ValueError('caption sidecar format must be srt or vtt')
    if out.exists(): raise ValueError('caption output already exists')
    clock=plan['clock']; lines=[]
    if fmt=='vtt': lines=['WEBVTT','']
    for index,cue in enumerate(plan['cues'],1):
        start=_time(cue['start'],clock);end=_time(cue['end'],clock)
        if fmt=='srt':
            lines.extend([str(index),f'{_srt_time(start)} --> {_srt_time(end)}',cue['text'],''])
        else:
            def vt(t:Fraction)->str: return _srt_time(t).replace(',', '.')
            lines.extend([cue['id'],f'{vt(start)} --> {vt(end)}',cue['text'],''])
    raw=('\n'.join(lines).rstrip()+'\n').encode('utf-8'); c.atomic(out,raw)
    return {'status':'pass','format':fmt,'path':out.relative_to(root).as_posix(),'sha256':c.digest(raw),'cue_count':len(plan['cues']),'source_sha256':plan['source_master']['sha256']}


def burn_in(root: Path, plan: Any, out: Path) -> dict[str,Any]:
    report=validate(root,plan)
    if report['status']!='pass': raise ValueError('caption plan does not pass validation')
    if 'burn-in' not in plan['delivery_modes']: raise ValueError('caption plan does not authorize burn-in delivery')
    if out.exists(): raise ValueError('caption output already exists')
    exe=shutil.which('ffmpeg')
    if not exe: raise ValueError('ffmpeg is required for caption burn-in')
    source=c.local(root,plan['source_master']['path'])
    with tempfile.TemporaryDirectory(prefix='caption-burn-') as td:
        srt=Path(td)/'captions.srt'; compile_sidecar(root,plan,srt,'srt')
        tmp=Path(td)/'out.mp4'
        # Use a temporary subtitle file rather than interpolating caption text into a shell command.
        style=[];st=plan['style']
        if st['size'] is not None: style.append(f'FontSize={st["size"]}')
        if st['margin_y']: style.append(f'MarginV={st["margin_y"]}')
        vf=f"subtitles={srt.as_posix()}"
        if style: vf += ':force_style=' + ','.join(style)
        cmd=[exe,'-hide_banner','-loglevel','error','-nostdin','-i',str(source),'-vf',vf,'-map','0:v:0','-map','0:a?','-c:v','libx264','-crf','18','-preset','veryfast','-c:a','copy','-y',str(tmp)]
        run=subprocess.run(cmd,capture_output=True,timeout=environment_seconds('PRODUCTION_MEDIA_TIMEOUT_SECONDS'),check=False)
        if run.returncode: raise ValueError('caption burn-in failed: '+run.stderr.decode('utf-8','replace'))
        raw=c.read(tmp); actual=media_evidence.inspect(tmp,raw); c.atomic(out,raw)
    return {'status':'pass','path':out.relative_to(root).as_posix(),'sha256':c.digest(raw),'media':actual,'source_sha256':plan['source_master']['sha256'],'cue_count':len(plan['cues'])}


def main()->int:
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('check');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True)
    q=sub.add_parser('compile');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True);q.add_argument('--format',choices=['srt','vtt'],required=True);q.add_argument('--out',required=True)
    q=sub.add_parser('burn-in');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True);q.add_argument('--out',required=True)
    a=p.parse_args();root=a.root.absolute()
    try:
        with operation('caption_track.'+a.command,root=root,arguments=vars(a)) as log:
            plan=c.load(c.local(root,a.plan))
            if a.command=='check': result=validate(root,plan)
            elif a.command=='compile': result=compile_sidecar(root,plan,c.local(root,a.out,exists=False),a.format)
            else: result=burn_in(root,plan,c.local(root,a.out,exists=False))
            log.event('caption_operation_completed',status=result['status'],cue_count=result.get('cue_count'))
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 1
    except c.EXPECTED_ERRORS+(subprocess.TimeoutExpired,) as exc:
        print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
