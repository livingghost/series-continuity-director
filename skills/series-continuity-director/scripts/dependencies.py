#!/usr/bin/env python3
"""Check the declared core or optional media runtime without installing anything."""
from pathlib import Path
import argparse
import importlib.metadata
import json
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
def check(scope):
    declared=json.loads((ROOT/'config/dependencies.json').read_text());issues=[];found={}
    found['python']='.'.join(map(str,sys.version_info[:3]))
    if tuple(sys.version_info[:2])<tuple(declared['python_minimum']):issues.append('Python does not meet the declared minimum')
    if scope=='media':
        for name,rule in declared['media']['distributions'].items():
            try:
                version=importlib.metadata.version(name);found[name]=version
                if not rule['minimum_major']<=int(version.split('.')[0])<rule['maximum_major_exclusive']:issues.append(name+' does not meet the declared media range')
            except importlib.metadata.PackageNotFoundError:issues.append(name+' is missing; install requirements-media.txt')
        for tool in declared['media']['executables']:
            exe=shutil.which(tool)
            if not exe:issues.append(tool+' is missing');continue
            proc=subprocess.run([exe,'-version'],capture_output=True,text=True,timeout=15)
            found[tool]=proc.stdout.splitlines()[0] if proc.stdout else ''
            if proc.returncode:issues.append(tool+' did not run')
    return {'ok':not issues,'scope':scope,'found':found,'errors':issues,'installed':False}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scope',choices=['core','media'],default='core');a=p.parse_args();report=check(a.scope);print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
