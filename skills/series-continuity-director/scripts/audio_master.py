#!/usr/bin/env python3
"""Verify declared audio-master preservation against actual streams and lineage."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from typing import Any
import execution_contract as c
import media_evidence
from protocol_contract import validate_against_schema
from operation_log import operation
from io_budget import environment_seconds

ROOT=Path(__file__).resolve().parents[1]


def _stream(media: dict[str,Any], index: int) -> dict[str,Any]:
    matches=[s for s in media.get('streams',[]) if s.get('index')==index and s.get('codec_type')=='audio']
    if len(matches)!=1: raise ValueError(f'audio stream {index} is unavailable')
    return matches[0]


def _ffmpeg_hash(path: Path, index: int, *, decoded: bool) -> str:
    exe=shutil.which('ffmpeg')
    if not exe: raise ValueError('ffmpeg is required for audio preservation checks')
    if decoded:
        cmd=[exe,'-hide_banner','-loglevel','error','-nostdin','-i',str(path),'-map',f'0:{index}','-vn','-acodec','pcm_s32le','-f','s32le','-']
    else:
        cmd=[exe,'-hide_banner','-loglevel','error','-nostdin','-i',str(path),'-map',f'0:{index}','-c','copy','-f','hash','-hash','sha256','-']
    run=subprocess.run(cmd,capture_output=True,check=False,timeout=environment_seconds('PRODUCTION_MEDIA_TIMEOUT_SECONDS'))
    if run.returncode: raise ValueError('audio evidence extraction failed: '+run.stderr.decode('utf-8','replace'))
    if decoded: return hashlib.sha256(run.stdout).hexdigest()
    text=run.stdout.decode('utf-8','replace').strip()
    if '=' not in text: raise ValueError('audio packet hash was not produced')
    return text.rsplit('=',1)[-1].strip().lower()


def check(root: Path, plan: Any) -> dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/audio-master.schema.json')
    errors=validate_against_schema(plan,schema)
    if errors: raise ValueError('audio master: '+'; '.join(errors))
    source=c.local(root,plan['source']['path']); out=c.local(root,plan['output']['path'])
    sr=c.read(source);oraw=c.read(out)
    if c.digest(sr)!=plan['source']['sha256']: raise ValueError('audio source content differs from its declared hash')
    if c.digest(oraw)!=plan['output']['sha256']: raise ValueError('audio output content differs from its declared hash')
    sm=media_evidence.inspect(source,sr); om=media_evidence.inspect(out,oraw)
    ss=_stream(sm,plan['source']['stream_index']); os=_stream(om,plan['output']['stream_index'])
    policy=plan['preservation']; findings=[]; measurements={
        'source_stream':ss,'output_stream':os,
        'source_file_sha256':plan['source']['sha256'],'output_file_sha256':plan['output']['sha256']
    }
    operations=[x['operation'] for x in plan['processing_graph']]
    undeclared=sorted(set(operations)-set(plan['allowed_operations']))
    if undeclared: findings.append({'code':'AUDIO_OPERATION_NOT_ALLOWED','operations':undeclared})
    if policy=='encoded-stream-preserve':
        if set(operations)-{'remux'}: findings.append({'code':'AUDIO_PRESERVATION_UNSUPPORTED','detail':'encoded preservation permits remux only'})
        measurements['source_encoded_essence_sha256']=_ffmpeg_hash(source,plan['source']['stream_index'],decoded=False)
        measurements['output_encoded_essence_sha256']=_ffmpeg_hash(out,plan['output']['stream_index'],decoded=False)
        if measurements['source_encoded_essence_sha256']!=measurements['output_encoded_essence_sha256']:
            findings.append({'code':'AUDIO_CONTENT_MISMATCH','detail':'encoded essence differs'})
    elif policy=='decoded-samples-preserve':
        measurements['source_decoded_samples_sha256']=_ffmpeg_hash(source,plan['source']['stream_index'],decoded=True)
        measurements['output_decoded_samples_sha256']=_ffmpeg_hash(out,plan['output']['stream_index'],decoded=True)
        if measurements['source_decoded_samples_sha256']!=measurements['output_decoded_samples_sha256']:
            findings.append({'code':'AUDIO_CONTENT_MISMATCH','detail':'decoded sample sequence differs'})
    elif policy=='single-encode-from-master':
        lossy=[x for x in plan['processing_graph'] if x['lossy_encode']]
        if len(lossy)!=1 or 'encode' not in operations:
            findings.append({'code':'ENCODE_LINEAGE_UNVERIFIED','detail':'controlled processing graph must contain exactly one lossy encode'})
        measurements['controlled_lossy_encode_count']=len(lossy)
        measurements['external_history']='unknown before the declared source artifact'
    elif policy=='approved-mix':
        if 'mix' not in operations:
            findings.append({'code':'AUDIO_PRESERVATION_UNSUPPORTED','detail':'approved-mix requires an explicit mix node'})
        measurements['source_decoded_samples_sha256']=_ffmpeg_hash(source,plan['source']['stream_index'],decoded=True)
        measurements['output_decoded_samples_sha256']=_ffmpeg_hash(out,plan['output']['stream_index'],decoded=True)
    status='pass' if not findings else 'fail'
    return {'status':status,'preservation':policy,'measurements':measurements,'findings':findings,'limitations':plan['limitations'],
            'scope':'Checks declared files and the SCD-controlled processing graph; earlier external encode history is not inferred.'}


def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['check']);p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',required=True)
    a=p.parse_args();root=a.root.absolute()
    try:
        with operation('audio_master.check',root=root,arguments=vars(a)) as log:
            result=check(root,c.load(c.local(root,a.plan)));log.event('audio_master_checked',status=result['status'])
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 1
    except c.EXPECTED_ERRORS+(subprocess.TimeoutExpired,) as exc:
        print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
