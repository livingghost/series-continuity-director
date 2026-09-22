#!/usr/bin/env python3
"""Run attributed schema import through the public CLI using synthetic local evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import execution_contract as c


def execute(args):
    result=subprocess.run([sys.executable,*args],capture_output=True,text=True,timeout=60)
    if result.returncode:raise ValueError(result.stdout+result.stderr)
    return json.loads(result.stdout)


def build():
    with tempfile.TemporaryDirectory(prefix='synthetic-model-evidence-') as directory:
        root=Path(directory)
        import production_test_support as fixture
        target={'service':'synthetic','model_identifier':'synthetic:one','operation':'generate'}
        spec={'target':'fixture','service':target['service'],'model':target['model_identifier'],'operation':target['operation']}
        profile,_,_=fixture.model_inputs(root,spec,{'operations':{'generate':{}}})
        (root/'profile.json').write_bytes(c.encoded(profile));before=c.read(root/'profile.json')
        schema={'type':'object','properties':{'seed':{'type':'integer'}}}
        raw=b'{ "schema" : '+json.dumps(schema).encode()+b' }\n'
        (root/'response.json').write_bytes(raw)
        acquisition={'artifact_type':'schema-acquisition','target':target,
            'source':{'kind':'document','identifier':'Synthetic service document','locator':'schema'},
            'acquired_at':'2000-01-01T00:00:00Z','response':{'path':'response.json','sha256':c.digest(raw)},
            'status':{'document_status':'schema-provided'}}
        (root/'acquisition.json').write_bytes(c.encoded(acquisition))
        result=execute([str(ROOT/'scripts/observe_schema.py'),'schema','--root',str(root),'--profile','profile.json',
            '--service','synthetic','--model','synthetic:one','--operation','generate','--out-dir','observed',
            '--acquisition','acquisition.json','--pointer','/schema'])
        catalog=c.load(root/result['catalog']['path']);contract=c.load(root/catalog['schema_snapshot']['path'])
        report={'synthetic':True,'target':result['target'],'public_profile_unchanged':c.read(root/'profile.json')==before,
            'acquired_response_unchanged':c.read(root/'observed/response.json')==raw,
            'schema_content_matches':contract['schema']==schema,
            'reference_schema_count':len(catalog['reference_schemas']),
            'trial_observation_count':len(catalog['parameter_observations']),
            'external_effect':result['external_effect'],'budget_effect':result['budget_effect']}
        if not all(report[k] for k in ('public_profile_unchanged','acquired_response_unchanged','schema_content_matches')):
            raise ValueError('Published evidence differs from the selected synthetic source.')
        return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();path=Path(__file__).with_name('report.json');raw=c.encoded(build())
    if args.check:
        if not path.is_file() or c.read(path)!=raw:raise ValueError('Rebuild the synthetic model evidence report.')
    else:path.write_bytes(raw)
    print(raw.decode(),end='');return 0

if __name__=='__main__':raise SystemExit(main())
