#!/usr/bin/env python3
"""Publish original schema evidence or an existing trial into a local target catalog.

`schema`, `reference` and `attach-probe` write a new evidence directory inside
the project and leave the selected target profile unchanged. With `--profiles
DIR`, `schema` also writes the project's own copy of that profile into DIR, its
offering pointing at the published schema, so `submission_gate.py --profiles
DIR` checks requests against it. The suite's shipped profiles change only with
`--suite-maintenance`, which a maintainer passes in a development checkout.
"""
from __future__ import annotations
import argparse
import copy
import json
import report_output
from pathlib import Path
import execution_contract as c
from input_evidence import InputEvidence
import model_observation
import schema_observation
import target_protocol


def profile_destination(root: Path, directory: Path, *, suite_maintenance: bool = False) -> Path:
    """The project's profile directory; the suite's own profiles need `suite_maintenance`."""
    target = (directory if directory.is_absolute() else root / directory).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError('write the project profile inside the project: ' + str(directory)) from None
    suite = target_protocol.ROOT.resolve()
    if (target == suite or suite in target.parents) and not suite_maintenance:
        raise ValueError('the suite keeps its shipped profiles; write the observed profile to a profile '
                         'directory of the project, such as target-profiles/, or pass --suite-maintenance '
                         'to update the shipped profiles in a development checkout')
    return target


def observed_profile(profile: dict, offering: dict, contract: dict, catalog: str, acquired_at: str) -> dict:
    """The profile with this offering pointing at the published schema."""
    value = copy.deepcopy(profile)
    for item in value['offerings']:
        if item['service'] == offering['service'] and item['model_identifier'] == offering['model_identifier']:
            item['schema_snapshot'] = contract['path']
            item['observed_at'] = acquired_at[:10]
            source = {'kind': 'surface-control', 'reference': 'observed schema evidence ' + catalog}
            if source not in item.setdefault('sources', []):
                item['sources'].append(source)
    value = target_protocol.finalize_profile(value)
    report = target_protocol.validate_profile(value)
    if not report['ok']:
        raise ValueError('the observed profile does not pass its contract: ' + '; '.join(report['errors']))
    return value


def publish(args) -> dict:
    root=args.root.resolve(strict=True);reader=InputEvidence(root)
    profile_ref=reader.select(args.profile);profile=reader.json(profile_ref)
    report=target_protocol.validate_profile(profile)
    if not report['ok']:raise ValueError('target profile must pass its public contract: '+'; '.join(report['errors']))
    matches=[item for item in profile['offerings'] if item['service']==args.service and item['model_identifier']==args.model]
    if len(matches)!=1:raise ValueError('select one exact target offering')
    profiles=getattr(args,'profiles',None)
    destination=None
    if profiles is not None:
        if args.command!='schema':raise ValueError('only an observed schema updates a project profile')
        destination=profile_destination(root,profiles,suite_maintenance=getattr(args,'suite_maintenance',False))
    target={'service':args.service,'model_identifier':args.model,'operation':args.operation}
    prefix=args.out_dir;out=c.local(root,prefix,exists=False)
    if out.exists():raise FileExistsError('select a new local evidence destination')
    written=None
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
        observed=None
        if destination is not None:
            acquired=c.decode(files['acquisition.json'])['acquired_at']
            observed=observed_profile(profile,matches[0],result['contract'],prefix+'/catalog.json',acquired)
        schema_observation.publish(root,prefix,files)
        if observed is not None:
            path=destination/(profile['target_id']+'.json')
            with c.lock(root):
                c.atomic(path,(json.dumps(observed,ensure_ascii=False,indent=2)+'\n').encode('utf-8'),replace=path.exists())
            written={'path':path.relative_to(root).as_posix(),'sha256':c.digest(path.read_bytes())}
    return {'ok':True,'target':target,'catalog':{'path':prefix+'/catalog.json','sha256':c.content_id(catalog)},
            'evidence':result,'profile':written,'external_effect':False,'budget_effect':'none'}


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0]);subparsers=parser.add_subparsers(dest='command',required=True)
    for name in ('schema','reference','attach-probe'):
        sub=subparsers.add_parser(name);sub.add_argument('--root',type=Path,required=True,help='The project root.')
        report_output.add_json_flag(sub)
        sub.add_argument('--profile',required=True,help='Project-relative public target profile; retained unchanged.')
        sub.add_argument('--service',required=True);sub.add_argument('--model',required=True);sub.add_argument('--operation',required=True)
        sub.add_argument('--out-dir',required=True,help='New project-relative local evidence directory.')
        if name=='attach-probe':sub.add_argument('--run',required=True)
        else:
            sub.add_argument('--acquisition',required=True);sub.add_argument('--pointer',default='')
            if name=='schema':
                sub.add_argument('--overlay')
                sub.add_argument('--profiles',type=Path,
                    help="The project's profile directory, such as target-profiles; receives the profile with this "
                         'offering pointing at the published schema.')
                sub.add_argument('--suite-maintenance',action='store_true',
                    help="Allow --profiles to name the suite's shipped profile directory; a maintainer step in "
                         'a development checkout.')
            else:sub.add_argument('--relationship',required=True);sub.add_argument('--locator',required=True)
    args=parser.parse_args(argv)
    report_output.use_json(args.json)
    try:result=publish(args)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.error(str(exc))
    report_output.emit(result);return 0


if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
