#!/usr/bin/env python3
"""Run documented CLI paths in new projects; no external generation or consent."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix='production-examples-') as temp:
        for example,filename in [('production-execution','run_example.py'),('timed-production','run_example.py'),('production-execution-repair','repair_example.py')]:
            folder='production-execution' if example=='production-execution-repair' else example
            p=subprocess.run([sys.executable,'-B',str(ROOT/'examples'/folder/filename),'--out',str(Path(temp)/example)],capture_output=True,text=True, encoding='utf-8',timeout=180,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            results.append({'example':example,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    ok=all(x['returncode']==0 for x in results);print(json.dumps({'ok':ok,'results':results},ensure_ascii=False,indent=2));return 0 if ok else 1
if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
