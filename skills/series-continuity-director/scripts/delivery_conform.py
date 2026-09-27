#!/usr/bin/env python3
"""Check actual finished media and required sidecars against a delivery profile."""
from __future__ import annotations
import argparse,json
from fractions import Fraction
from pathlib import Path
from typing import Any
import execution_contract as c
import media_evidence
from protocol_contract import validate_against_schema
from operation_log import operation
ROOT=Path(__file__).resolve().parents[1]

def _fraction(text: str|None)->Fraction|None:
    if not text or text in {'0/0','N/A'}: return None
    try:
        a,b=text.split('/',1);return Fraction(int(a),int(b))
    except Exception:return None

def check(root:Path, plan:Any)->dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/media-delivery-profile.schema.json');errors=validate_against_schema(plan,schema)
    if errors: raise ValueError('delivery profile: '+'; '.join(errors))
    source=c.local(root,plan['source']['path']);raw=c.read(source)
    if c.digest(raw)!=plan['source']['sha256']:raise ValueError('delivery source changed')
    media=media_evidence.inspect(source,raw);findings=[];video=next((x for x in media.get('streams',[]) if x.get('codec_type')=='video'),None);audio=[x for x in media.get('streams',[]) if x.get('codec_type')=='audio']
    vp=plan['video']
    if vp['width'] is not None and (video is None or video.get('width')!=vp['width']):findings.append({'code':'DELIVERY_WIDTH_MISMATCH'})
    if vp['height'] is not None and (video is None or video.get('height')!=vp['height']):findings.append({'code':'DELIVERY_HEIGHT_MISMATCH'})
    if vp['codec'] is not None and (video is None or video.get('codec_name')!=vp['codec']):findings.append({'code':'DELIVERY_VIDEO_CODEC_MISMATCH'})
    if vp['pixel_format'] is not None and (video is None or video.get('pix_fmt')!=vp['pixel_format']):findings.append({'code':'DELIVERY_PIXEL_FORMAT_MISMATCH'})
    expected_fps=Fraction(vp['fps']['numerator'],vp['fps']['denominator']) if vp['fps'] else None
    actual_fps=_fraction(video.get('avg_frame_rate')) if video else None
    if expected_fps is not None and actual_fps!=expected_fps:findings.append({'code':'DELIVERY_FPS_MISMATCH','expected':str(expected_fps),'actual':str(actual_fps) if actual_fps else None})
    duration=media.get('duration');dp=plan['duration']
    if dp['minimum'] is not None and (duration is None or duration+1e-9<dp['minimum']):findings.append({'code':'DELIVERY_DURATION_SHORT'})
    if dp['maximum'] is not None and (duration is None or duration-1e-9>dp['maximum']):findings.append({'code':'DELIVERY_DURATION_LONG'})
    if dp['exact_frames'] is not None and (video is None or int(video.get('nb_frames',-1))!=dp['exact_frames']):findings.append({'code':'DELIVERY_FRAME_COUNT_MISMATCH'})
    ap=plan['audio']
    if ap['required'] and not audio:findings.append({'code':'DELIVERY_AUDIO_MISSING'})
    if not ap['required'] and audio:findings.append({'code':'DELIVERY_UNEXPECTED_AUDIO'})
    if audio:
        a=audio[0]
        if ap['codec'] is not None and a.get('codec_name')!=ap['codec']:findings.append({'code':'DELIVERY_AUDIO_CODEC_MISMATCH'})
        if ap['sample_rate'] is not None and int(a.get('sample_rate',0))!=ap['sample_rate']:findings.append({'code':'DELIVERY_SAMPLE_RATE_MISMATCH'})
        if ap['channels'] is not None and a.get('channels')!=ap['channels']:findings.append({'code':'DELIVERY_CHANNEL_MISMATCH'})
    sidecars=[]
    for item in plan['sidecars']:
        p=c.local(root,item['path']);sr=c.read(p);ok=c.digest(sr)==item['sha256'];sidecars.append({'path':item['path'],'sha256':c.digest(sr),'ok':ok})
        if not ok:findings.append({'code':'DELIVERY_SIDECAR_CHANGED','path':item['path']})
    return {'status':'pass' if not findings else 'fail','media':media,'sidecars':sidecars,'findings':findings,'limitations':plan['limitations']}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['check']);p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',required=True);a=p.parse_args();root=a.root.absolute()
    try:
        with operation('delivery_conform.check',root=root,arguments=vars(a)) as log:
            result=check(root,c.load(c.local(root,a.plan)));log.event('delivery_checked',status=result['status'],findings=len(result['findings']))
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 1
    except c.EXPECTED_ERRORS as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
