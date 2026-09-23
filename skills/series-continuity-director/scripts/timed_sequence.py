#!/usr/bin/env python3
"""Validate separate story/performance/source/edit clocks and render real media.

The built-in renderer realizes declared trims, holds, retiming, layered motion
and audio mixing with FFmpeg. It does not infer acting or direct a work by
scoring it. Inspect and extraction are measurement primitives; only a bound
production execution yields an authorized candidate in a production run.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import io
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
import execution_contract as c
from io_budget import optional_seconds, environment_seconds
import media_evidence
from production_direction import strings

ROOT=Path(__file__).resolve().parents[1]
CLOCK_KINDS={'story','performance','source','edit'}


def rational(value: Any, name: str) -> Fraction:
    media_evidence.number(value,name)
    return Fraction(str(value))


def rate(value: Any) -> Fraction:
    c.exact(value,{'numerator','denominator'},'frame rate')
    if any(type(value[k]) is not int or value[k] <= 0 for k in value):
        raise ValueError('frame rate needs positive integer numerator and denominator')
    return Fraction(value['numerator'],value['denominator'])


def decimal(value: Fraction | float) -> str:
    return f'{float(value):.12f}'.rstrip('0').rstrip('.') or '0'


def clock_map(plan: dict[str,Any]) -> dict[str,dict[str,Any]]:
    if not isinstance(plan['clocks'],list): raise ValueError('clocks must be a list')
    clocks={}
    for clock in plan['clocks']:
        c.exact(clock,{'id','kind','unit','rate'},'clock')
        c.text(clock['id'],'clock id')
        if clock['id'] in clocks or clock['kind'] not in CLOCK_KINDS: raise ValueError('duplicate or unknown clock')
        if clock['kind']=='story':
            if clock['unit']!='ordinal' or clock['rate'] is not None: raise ValueError('story order is ordinal, never implicitly seconds')
        elif clock['unit']=='frames': rate(clock['rate'])
        elif clock['unit']!='seconds' or clock['rate'] is not None: raise ValueError('elapsed clocks use seconds or explicitly rated frames')
        clocks[clock['id']]=clock
    return clocks


def seconds(value: Any, clock: dict[str,Any]) -> Fraction:
    q=rational(value,'time coordinate')
    if clock['kind']=='story': raise ValueError('story order cannot be converted into elapsed time')
    if clock['unit']=='frames':
        if q.denominator!=1: raise ValueError('frame coordinates are integers')
        return q/rate(clock['rate'])
    return q


def span(value: Any, clocks: dict[str,dict[str,Any]], kind: str) -> tuple[Fraction,Fraction]:
    c.exact(value,{'clock','start','end'},'time interval')
    if value['clock'] not in clocks or clocks[value['clock']]['kind']!=kind:
        raise ValueError(f'interval must use a declared {kind} clock')
    clock=clocks[value['clock']]; start=seconds(value['start'],clock);end=seconds(value['end'],clock)
    if not 0 <= start < end: raise ValueError('time interval is nonnegative and half-open [start,end)')
    return start,end


def identified(rows: Any, label: str) -> dict[str,dict[str,Any]]:
    if not isinstance(rows,list): raise ValueError(label+' must be a list')
    result={}
    for row in rows:
        if not isinstance(row,dict): raise ValueError(label+' member must be an object')
        key=c.text(row.get('id'),label+' id')
        if key in result: raise ValueError('duplicate '+label+' id')
        result[key]=row
    return result


def validate_plan(root: Path, plan: Any) -> dict[str,Any]:
    from protocol_contract import validate_against_schema
    schema=c.load(ROOT/'schemas/authoring/timed-sequence.schema.json')
    errors=validate_against_schema(plan,schema)
    if errors: raise ValueError('sequence plan: '+'; '.join(errors))
    c.exact(plan,{'purpose','clocks','assets','cues','constraints','placements','story_links','cue_links','boundaries','output','limitations'},'sequence plan')
    c.text(plan['purpose'],'sequence purpose'); strings(plan['limitations'],'sequence limitations')
    clocks=clock_map(plan);assets=identified(plan['assets'],'asset');cues=identified(plan['cues'],'cue');placements=identified(plan['placements'],'placement')
    output=plan['output'];c.exact(output,{'clock','duration','width','height','fps','background'},'output')
    if output['clock'] not in clocks or clocks[output['clock']]['kind']!='edit': raise ValueError('output needs its own edit clock')
    duration=seconds(output['duration'],clocks[output['clock']]);fps=rate(output['fps'])
    if duration<=0 or (duration*fps).denominator!=1:
        raise ValueError('output needs a positive duration on its declared frame grid')
    if any(type(output[k]) is not int or output[k]<2 or output[k]%2 for k in ('width','height')):
        raise ValueError('the yuv420p MP4 renderer needs even positive dimensions')
    import re
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',output['background']): raise ValueError('background must be an explicit #RRGGBB value')
    metadata={};source_clocks=set()
    for asset in assets.values():
        c.exact(asset,{'id','path','sha256','kind','source_clock','limitations'},'asset')
        c.sha(asset['sha256']); strings(asset['limitations'],'asset limitations')
        path=c.local(root,asset['path']);raw=c.read(path)
        if c.digest(raw)!=asset['sha256']: raise ValueError('asset content differs from its declared hash: '+asset['id'])
        actual=media_evidence.inspect(path,raw)
        if asset['kind']!=actual['kind']: raise ValueError('asset kind is not supported by actual bytes: '+asset['id'])
        if asset['kind']=='image':
            if asset['source_clock'] is not None: raise ValueError('a still image has no source duration')
        else:
            cid=asset['source_clock']
            if cid not in clocks or clocks[cid]['kind']!='source': raise ValueError('timed asset needs a source clock')
            if cid in source_clocks: raise ValueError('each timed asset owns a distinct source clock')
            source_clocks.add(cid)
            if actual.get('duration') is None: raise ValueError('timed source duration could not be measured')
        metadata[asset['id']]=actual
    cue_spans={}
    for cue in cues.values():
        c.exact(cue,{'id','span','subjects','action','relations'},'performance cue')
        cue_spans[cue['id']]=span(cue['span'],clocks,'performance')
        strings(cue['subjects'],'cue subjects');c.text(cue['action'],'cue action')
        if not isinstance(cue['relations'],list): raise ValueError('cue relations must be a list')
        for relation in cue['relations']:
            c.exact(relation,{'subjects','relation','condition'},'cue relation')
            strings(relation['subjects'],'related subjects',nonempty=True)
            c.text(relation['relation'],'relation');c.text(relation['condition'],'relation condition')
    for constraint in plan['constraints']:
        c.exact(constraint,{'first','relation','second'},'cue constraint')
        first,second=constraint['first'],constraint['second']
        if first not in cues or second not in cues or first==second: raise ValueError('cue constraint refers to unknown or identical cues')
        if cues[first]['span']['clock']!=cues[second]['span']['clock']: raise ValueError('ordering across unrelated performance clocks is undefined')
        a,b=cue_spans[first];x,y=cue_spans[second]
        rules={'precedes':a<x,'finishes-before':b<=x,'overlaps':max(a,x)<min(b,y),'starts-with':a==x}
        if constraint['relation'] not in rules or not rules[constraint['relation']]: raise ValueError('declared cue timing constraint is not satisfied')
    placed={}
    for clip in placements.values():
        c.exact(clip,{'id','asset','source','edit','rate','video','audio'},'placement')
        if clip['asset'] not in assets: raise ValueError('placement names an unknown asset')
        asset=assets[clip['asset']];actual=metadata[asset['id']]
        start,end=span(clip['edit'],clocks,'edit')
        if clip['edit']['clock']!=output['clock'] or end>duration: raise ValueError('placement lies outside the output timeline')
        speed=rational(clip['rate'],'playback rate')
        if speed<=0: raise ValueError('playback rate must be positive; materialize reverse playback as an explicit source')
        source_start=Fraction(0);source_end=None
        if asset['kind']=='image':
            if clip['source'] is not None or speed!=1: raise ValueError('still image placement uses an explicit hold, not a fabricated source duration')
        else:
            source_start,source_end=span(clip['source'],clocks,'source')
            if clip['source']['clock']!=asset['source_clock']: raise ValueError('source interval belongs to another asset clock')
            if source_end>Fraction(str(actual['duration']))+Fraction(1,1000000): raise ValueError('source interval exceeds actual media')
            if abs((source_end-source_start)/speed-(end-start))>Fraction(1,1000000): raise ValueError('source, rate and edit durations disagree')
        video=clip['video'];audio=clip['audio']
        if video is None and audio is None: raise ValueError('placement realizes neither picture nor sound')
        if source_end is not None:
            for medium,used in (('video',video),('audio',audio)):
                if used is None:continue
                streams=[x for x in actual.get('streams',[]) if x['codec_type']==medium]
                try:
                    measured=Fraction(str(streams[0]['duration']))
                except (IndexError,KeyError,ValueError,ZeroDivisionError) as exc:
                    raise ValueError('selected source stream has no measured duration') from exc
                if source_end>measured:
                    raise ValueError('source interval exceeds the stream used by this placement')

        if video is not None:
            c.exact(video,{'layer','width','height','fit','x','y','opacity'},'visual placement')
            if asset['kind'] not in {'image','video'}: raise ValueError('visual placement requires picture content')
            if any(type(video[k]) is not int or video[k]<1 for k in ('width','height')): raise ValueError('invalid visual placement dimensions')
            if type(video['layer']) is not int or video['layer']<0 or video['fit'] not in {'contain','cover','stretch'}: raise ValueError('invalid compositing layer or fit')
            if any((v*fps).denominator!=1 for v in (start,end)): raise ValueError('visual edits must lie on the declared output frame grid')
            for key in ('x','y'):
                if not isinstance(video[key],list) or len(video[key])!=2: raise ValueError('position needs explicit start and end coordinates')
                for v in video[key]: rational(v,'position')
            if not 0<=rational(video['opacity'],'opacity')<=1: raise ValueError('opacity must be in [0,1]')
        if audio is not None:
            c.exact(audio,{'gain'},'audio placement')
            if not media_evidence.supports(actual,'audio'): raise ValueError('audio placement needs an actual audio stream')
            if rational(audio['gain'],'gain')<0: raise ValueError('gain cannot be negative')
        placed[clip['id']]={'start':float(start),'end':float(end),'source_start':float(source_start),
                           'source_end':None if source_end is None else float(source_end),'rate':float(speed)}
    linked=set()
    for link in plan['cue_links']:
        c.exact(link,{'cue','placements','relation','limitations'},'cue realization link')
        if link['cue'] not in cues: raise ValueError('unknown linked cue')
        if not set(strings(link['placements'],'linked placements',nonempty=link['relation']!='omitted'))<=set(placements): raise ValueError('unknown cue placement')
        if link['relation'] not in {'depicted','reference','omitted'}: raise ValueError('declare whether a cue is depicted, referenced or omitted')
        strings(link['limitations'],'cue realization limitations',nonempty=link['relation']=='omitted');linked.add(link['cue'])
    if linked!=set(cues): raise ValueError('account for every declared performance cue without pretending it was rendered')
    for link in plan['story_links']:
        c.exact(link,{'clock','position','cues','placements','relation'},'story mapping')
        if link['clock'] not in clocks or clocks[link['clock']]['kind']!='story': raise ValueError('story mapping needs an ordinal clock')
        rational(link['position'],'story position');c.text(link['relation'],'story mapping relation')
        if not set(strings(link['cues'],'story-linked cues'))<=set(cues) or not set(strings(link['placements'],'story-linked placements'))<=set(placements): raise ValueError('story mapping contains unknown references')
    for boundary in plan['boundaries']:
        c.exact(boundary,{'from','to','relation','reason','verification'},'editorial boundary')
        if boundary['from'] not in placements or boundary['to'] not in placements or boundary['from']==boundary['to']: raise ValueError('invalid editorial boundary')
        for key in ('relation','reason','verification'):c.text(boundary[key],'boundary '+key)
    return {'duration_seconds':float(duration),'output_frames':int(duration*fps),'fps':str(fps),
            'assets':metadata,'placements':placed,'cue_count':len(cues),'story_mapping_count':len(plan['story_links']),
            'planned_not_observed':True,'limitations':plan['limitations']}


def tempo(speed: float) -> list[str]:
    if abs(speed-1)<1e-12:return []
    values=[]
    while speed>2:values.append('atempo=2');speed/=2
    while speed<0.5:values.append('atempo=0.5');speed/=0.5
    values.append('atempo='+decimal(speed));return values


def render_files(root: Path, plan: dict[str,Any], output: Path, *, timeout: float | None = None) -> dict[str,Any]:
    report=validate_plan(root,plan); executable=shutil.which('ffmpeg')
    if not executable:raise ValueError('ffmpeg is required for time-bearing output')
    assets={x['id']:x for x in plan['assets']};fps=report['fps'];duration=report['duration_seconds'];o=plan['output']
    with tempfile.TemporaryDirectory(prefix='sequence-') as temporary:
        temp=Path(temporary);copies={}
        for index,asset in enumerate(plan['assets']):
            raw=c.read(c.local(root,asset['path']))
            if c.digest(raw)!=asset['sha256']:raise ValueError('source changed while preparing the render')
            target=temp/f'asset-{index}{Path(asset["path"]).suffix}'
            target.write_bytes(raw);copies[asset['id']]=target
        cmd=[executable,'-hide_banner','-loglevel','error','-nostdin','-filter_complex_threads','1']
        for clip in plan['placements']:
            if assets[clip['asset']]['kind']=='image':cmd+=['-loop','1','-framerate',fps]
            cmd+=['-i',str(copies[clip['asset']])]
        filters=[f"color=c=0x{o['background'][1:]}:s={o['width']}x{o['height']}:r={fps}:d={decimal(duration)},format=rgba[base0]"]
        pictures=[];audios=[]
        for index,clip in enumerate(plan['placements']):
            timing=report['placements'][clip['id']];start=timing['start'];end=timing['end'];length=end-start
            visual=clip['video'];audio=clip['audio'];ss=timing['source_start'];se=timing['source_end']
            if visual is not None:
                chain=(f'trim=duration={decimal(length)},setpts=PTS-STARTPTS' if se is None else
                       f'setpts=PTS-STARTPTS,trim=start={decimal(ss)}:end={decimal(se)},setpts=(PTS-STARTPTS)/{decimal(timing["rate"])}')
                chain+=f',fps={fps},setpts=PTS+{decimal(start)}/TB'
                w,h=visual['width'],visual['height'];fit=visual['fit']
                if fit=='contain':chain+=f',scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x00000000'
                elif fit=='cover':chain+=f',scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
                else:chain+=f',scale={w}:{h}'
                chain+=f',setsar=1,format=rgba,colorchannelmixer=aa={decimal(visual["opacity"])}'
                filters.append(f'[{index}:v:0]{chain}[pic{index}]');pictures.append((visual['layer'],index,visual,timing))
            if audio is not None:
                # Work in decoded sample coordinates. Some filters can emit unknown
                # timestamps; rebase to sample counts before padding and mixing.
                clip_samples=round(length*48000);total_samples=round(duration*48000)
                chain=['asetpts=N/SR/TB',f'atrim=start={decimal(ss)}:end={decimal(se)}',
                       'asetpts=N/SR/TB',*tempo(timing['rate']),f'volume={decimal(audio["gain"])}',
                       'aresample=48000','asettb=1/48000','asetpts=N/SR/TB',
                       f'apad=whole_len={clip_samples}',f'atrim=end_sample={clip_samples}',
                       f'adelay={round(start*48000)}S:all=1',f'apad=whole_len={total_samples}',
                       f'atrim=end_sample={total_samples}','asetpts=N/SR/TB']
                filters.append(f'[{index}:a:0]'+','.join(chain)+f'[aud{index}]');audios.append(index)
        base='base0'
        for n,(_,index,visual,timing) in enumerate(sorted(pictures,key=lambda x:(x[0],x[1])),1):
            start,end=timing['start'],timing['end'];length=end-start
            def position(values):return f'{decimal(values[0])}+({decimal(values[1]-values[0])})*clip((t-{decimal(start)})/{decimal(length)},0,1)'
            filters.append(f"[{base}][pic{index}]overlay=x='{position(visual['x'])}':y='{position(visual['y'])}':enable='gte(t,{decimal(start)})*lt(t,{decimal(end)})':eof_action=pass:repeatlast=0[base{n}]")
            base=f'base{n}'
        filters.append(f'[{base}]format=yuv420p[vout]')
        if audios:
            filters.append(''.join(f'[aud{i}]' for i in audios)+f'amix=inputs={len(audios)}:duration=longest:normalize=0,apad=whole_len={round(duration*48000)},atrim=end_sample={round(duration*48000)},asetpts=N/SR/TB[aout]')
        rendered=temp/'render.mp4';cmd+=['-filter_complex',';'.join(filters),'-map','[vout]']
        if audios:cmd+=['-map','[aout]','-c:a','aac','-ar','48000']
        cmd+=['-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-r',fps,'-t',decimal(duration),'-movflags','+faststart','-y',str(rendered)]
        result=subprocess.run(cmd,capture_output=True,timeout=optional_seconds(timeout, "media timeout") if timeout is not None else environment_seconds("PRODUCTION_MEDIA_TIMEOUT_SECONDS"),check=False)
        if result.returncode:raise ValueError('FFmpeg render failed: '+result.stderr.decode('utf-8','replace'))
        actual=media_evidence.probe(rendered)
        video=next(s for s in actual['streams'] if s['codec_type']=='video')
        if (video.get('width'),video.get('height'))!=(o['width'],o['height']):raise ValueError('rendered dimensions differ from declared output')
        if int(video.get('nb_frames',-1))!=report['output_frames']:raise ValueError('rendered frame count differs from declared time grid')
        if abs(float(video.get('duration',-1))-duration)>1/float(Fraction(fps))+1e-6:raise ValueError('rendered duration differs from the edit timeline')
        if bool(audios)!=media_evidence.supports(actual,'audio'):raise ValueError('rendered audio stream presence disagrees with the plan')
        for stream in actual['streams']:
            if abs(float(stream.get('start_time',0)))>1/48000+1e-6:
                raise ValueError('rendered stream timestamps do not begin at the declared edit origin')
            if stream['codec_type']=='audio' and abs(float(stream.get('duration',-1))-duration)>2/48000+1e-6:
                raise ValueError('rendered audio does not span the declared edit duration')
        output_raw=c.read(rendered)
        c.atomic(output,output_raw)
        return {'plan_sha256':c.content_id(plan),'source_assets':[{'id':a['id'],'path':a['path'],'sha256':a['sha256']} for a in plan['assets']],
                'output_sha256':c.digest(output_raw),'output_media':actual,'planned':report,
                'command':cmd,'filters':filters,'limitations':plan['limitations'],
                'scope':'Time and file realization only; acting, meaning, sound content and audience effect require actual review.'}


def execute(root: Path, run: str, output_path: str, authorization: str, actor: str, *, timeout: float | None = None) -> dict[str,Any]:
    import production_workflow as workflow
    import production_recovery as recovery
    _,prepared,_,rows=workflow.assert_current(root,run);path=prepared['task']['sequence_plan']
    if path is None:raise ValueError('this run has no sequence plan')
    workflow.find(rows,'handoff');raw=c.read(c.local(root,path));plan=c.decode(raw)
    output=c.local(root,output_path,exists=False)
    if output.suffix.lower()!='.mp4':raise ValueError('choose a new MP4 output')
    request_sha256=c.content_id({'plan_sha256':c.digest(raw),'output':output_path})
    prior=[r for r in rows if r['event']=='reservation' and r['data']['authorization']==authorization and r['data']['request_sha256']==request_sha256]
    if prior:
        if prior[-1]['data']['actor']!=actor:raise ValueError('reserved execution belongs to another actor')
        return recovery.recover(root,run,prior[-1]['sha256'])
    receipt_path=output_path+'.receipt.json'
    receipt=c.local(root,receipt_path,exists=False)
    if output.exists() or receipt.exists() or any(part.startswith('.') for part in Path(output_path).parts) or Path(output_path).parts[0]=='production':
        raise ValueError('choose new output paths outside existing artifacts and internal records')
    validate_plan(root,plan)
    reservation=workflow.reserve_action(root,run,authorization=authorization,actor=actor,operation='edit',scopes=['task'],
        request_sha256=request_sha256,outputs=1)
    if reservation['repeated']:
        return recovery.recover(root,run,reservation['record']['sha256'])
    # Compute into an isolated output; publish only after current inputs and
    # permission are rechecked. A failed computation retains its reservation.
    with tempfile.TemporaryDirectory(prefix='sequence-output-') as temporary:
        staged=Path(temporary)/'result.mp4'
        result=render_files(root,plan,staged,timeout=timeout)
        workflow.assert_current(root,run)
        if c.read(c.local(root,path))!=raw:raise ValueError('sequence plan changed during execution')
        result['reservation']=reservation['record']['sha256'];result['output_path']=output_path
        limitations=list(dict.fromkeys(plan['limitations']+[x for a in plan['assets'] for x in a['limitations']]))
        recovery.retain(root,run,reservation['record']['sha256'],
                        {output_path:c.read(staged),receipt_path:c.encoded(result)},output_path,
                        'Rendered declared time plan; artistic claims require observed review.',limitations)
    return recovery.recover(root,run,reservation['record']['sha256'])


def extract(root: Path, source: str, expected_sha256: str, output: str, *, start: float, end: float | None = None, timeout: float | None = None) -> dict[str,Any]:
    c.sha(expected_sha256);path=c.local(root,source);raw=c.read(path)
    if c.digest(raw)!=expected_sha256:raise ValueError('extraction source hash mismatch')
    actual=media_evidence.inspect(path,raw)
    medium='video' if end is None else 'audio'
    streams=[x for x in actual.get('streams',[]) if x['codec_type']==medium]
    try:duration=float(streams[0]['duration'])
    except (IndexError,KeyError,ValueError,TypeError) as exc:raise ValueError('extraction needs a measured duration for the selected stream') from exc
    start=float(rational(start,'extraction start'))
    if duration is None or not 0<=start<duration:raise ValueError('extraction start is outside the source')
    target=c.local(root,output,exists=False);sidecar=c.local(root,output+'.receipt.json',exists=False)
    if target.exists() or sidecar.exists():raise ValueError('extraction never overwrites output or evidence')
    exe=shutil.which('ffmpeg')
    if not exe:raise ValueError('ffmpeg is required for extraction')
    with tempfile.TemporaryDirectory(prefix='media-extract-') as temporary:
        temp=Path(temporary);snapshot=temp/('source'+path.suffix);snapshot.write_bytes(raw)
        out=temp/target.name
        cmd=[exe,'-hide_banner','-loglevel','error','-nostdin','-i',str(snapshot)]
        if end is None:
            if target.suffix.lower()!='.png' or actual['kind']!='video':raise ValueError('frame extraction needs video and a new PNG path')
            cmd+=['-vf',f"setpts=PTS-STARTPTS,select='gte(t,{decimal(start)})'",'-frames:v','1','-fps_mode','vfr',str(out)]
            selection='first decoded video frame at or after the requested presentation time'
        else:
            end=float(rational(end,'extraction end'))
            if not start<end<=duration or target.suffix.lower()!='.wav' or not media_evidence.supports(actual,'audio'):raise ValueError('audio extraction needs an in-range interval, actual audio and a new WAV path')
            cmd+=['-vn','-af',f'asetpts=N/SR/TB,atrim=start={decimal(start)}:end={decimal(end)},asetpts=N/SR/TB','-c:a','pcm_s16le',str(out)]
            selection='half-open audio interval [start,end), rounded by the decoder to sample boundaries'
        result=subprocess.run(cmd,capture_output=True,timeout=optional_seconds(timeout, "media timeout") if timeout is not None else environment_seconds("PRODUCTION_MEDIA_TIMEOUT_SECONDS"),check=False)
        if result.returncode or not out.is_file():raise ValueError('extraction failed: '+result.stderr.decode('utf-8','replace'))
        out_raw=c.read(out);metadata=media_evidence.inspect(out,out_raw)
        if end is not None:
            observed_duration=metadata.get('duration')
            audio_streams=[s for s in metadata.get('streams',[]) if s['codec_type']=='audio']
            sample_rate=float(audio_streams[0].get('sample_rate',48000)) if audio_streams else 48000
            if observed_duration is None or abs(observed_duration-(end-start))>2/sample_rate+1e-6:
                raise ValueError('extracted audio sample duration does not match the requested interval')
        if c.digest(c.read(path))!=expected_sha256:raise ValueError('extraction source changed')
        receipt={'source':source,'source_sha256':expected_sha256,'start_seconds':start,'end_seconds':end,
                 'selection':selection,'output':output,'output_sha256':c.digest(out_raw),'media':metadata,'command':cmd}
        c.atomic(target,out_raw);c.atomic(sidecar,c.encoded(receipt));return receipt


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    check=sub.add_parser('inspect');check.add_argument('--root',type=Path,required=True);check.add_argument('--plan',required=True)
    render=sub.add_parser('render');render.add_argument('--root',type=Path,required=True);render.add_argument('--run',required=True)
    render.add_argument('--out',required=True);render.add_argument('--authorization',required=True);render.add_argument('--actor',required=True)
    ex=sub.add_parser('extract');ex.add_argument('--root',type=Path,required=True);ex.add_argument('--source',required=True);ex.add_argument('--sha256',required=True)
    ex.add_argument('--start',type=float,required=True);ex.add_argument('--end',type=float);ex.add_argument('--out',required=True)
    render.add_argument('--timeout',type=float);ex.add_argument('--timeout',type=float)
    a=p.parse_args();root=a.root.absolute()
    try:
        if a.command=='inspect':result=validate_plan(root,c.load(c.local(root,a.plan)))
        elif a.command=='render':result=execute(root,a.run,a.out,a.authorization,a.actor,timeout=a.timeout)
        else:result=extract(root,a.source,a.sha256,a.out,start=a.start,end=a.end,timeout=a.timeout)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,UnicodeError,KeyError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}));return 1
if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
