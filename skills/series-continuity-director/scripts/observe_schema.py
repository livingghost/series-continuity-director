#!/usr/bin/env python3
"""Publish original schema evidence or an existing trial into a local target catalog."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import execution_contract as c
from input_evidence import InputEvidence
import model_observation
import schema_observation
import target_protocol


def publish(args) -> dict:
    root=args.root.resolve(strict=True);reader=InputEvidence(root)
    profile_ref=reader.select(args.profile);profile=reader.json(profile_ref)
    report=target_protocol.validate_profile(profile)
    if not report['ok']:raise ValueError('target profile must pass its public contract')
    matches=[item for item in profile['offerings'] if item['service']==args.service and item['model_identifier']==args.model]
    if len(matches)!=1:raise ValueError('select one exact target offering')
    target={'service':args.service,'model_identifier':args.model,'operation':args.operation}
    prefix=args.out_dir;out=c.local(root,prefix,exists=False)
    if out.exists():raise FileExistsError('select a new local evidence destination')
    if args.command=='attach-probe':
        source=model_observation.capture(root,args.run)
        if model_observation._derive(source)['target']!=target:raise ValueError('trial names another target')
        files,result=model_observation.bundle(root,args.run,relative_prefix=prefix)
        catalog={'artifact_type':'local-model-evidence-catalog','target':target,'target_profile':profile_ref,
            'schema_snapshot':None,'schema_acquisition':None,'reference_schemas':[],
            'parameter_observations':[result]}
        files['catalog.json']=c.encoded(catalog)
        schema_observation.publish(root,prefix,files)
    else:
        relationship=None
        if args.command=='reference':relationship=dict(reader.select(args.relationship),locator=args.locator)
        files,result=schema_observation.assemble(root,target=target,acquisition=args.acquisition,
            pointer=args.pointer,prefix=prefix,kind=args.command,relationship=relationship,
            overlay=args.overlay if args.command=='schema' else None)
        catalog={'artifact_type':'local-model-evidence-catalog','target':target,'target_profile':profile_ref,
            'schema_snapshot':result['contract'] if args.command=='schema' else None,
            'schema_acquisition':result['evidence'] if args.command=='schema' else None,
            'reference_schemas':[result['contract']] if args.command=='reference' else [],'parameter_observations':[]}
        files['catalog.json']=c.encoded(catalog)
        schema_observation.publish(root,prefix,files)
    return {'ok':True,'target':target,'catalog':{'path':prefix+'/catalog.json','sha256':c.content_id(catalog)},
            'evidence':result,'external_effect':False,'budget_effect':'none'}


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__);subparsers=parser.add_subparsers(dest='command',required=True)
    for name in ('schema','reference','attach-probe'):
        sub=subparsers.add_parser(name);sub.add_argument('--root',type=Path,required=True)
        sub.add_argument('--profile',required=True,help='Project-relative public target profile; retained unchanged.')
        sub.add_argument('--service',required=True);sub.add_argument('--model',required=True);sub.add_argument('--operation',required=True)
        sub.add_argument('--out-dir',required=True,help='New project-relative local evidence directory.')
        if name=='attach-probe':sub.add_argument('--run',required=True)
        else:
            sub.add_argument('--acquisition',required=True);sub.add_argument('--pointer',default='')
            if name=='schema':sub.add_argument('--overlay')
            else:sub.add_argument('--relationship',required=True);sub.add_argument('--locator',required=True)
    args=parser.parse_args(argv)
    try:result=publish(args)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.error(str(exc))
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
