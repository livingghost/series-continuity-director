#!/usr/bin/env python3
"""Synthetic end-to-end CLI fixture. No generated fiction or human approval."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(SKILL/'scripts'))
import production_test_support as support


def run(out: Path) -> dict:
    if out.exists(): raise ValueError('choose a new output directory')
    out.parent.mkdir(parents=True,exist_ok=True)
    log=[]
    def command(script: str, *args: str, parse: bool = True, cwd: Path | None = None):
        argv=[sys.executable,'-B',str(SKILL/'scripts'/script),*map(str,args)]
        p=subprocess.run(argv,cwd=cwd or out,capture_output=True,text=True, encoding='utf-8',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        log.append({'argv':argv,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        if out.is_dir(): (out/'commands.json').write_text(json.dumps(log,indent=2)+'\n',encoding='utf-8',newline='\n')
        if p.returncode: raise ValueError(p.stdout+p.stderr)
        return json.loads(p.stdout) if parse else p.stdout
    # The work ledger records into a project, so the fixture starts as one.
    command('init_project.py','--out',out,'--series-id','FIXTURE-ROOM','--title','Synthetic room fixture',
            '--medium','prose',parse=False,cwd=out.parent)
    def write(name,value): (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    command('work_ledger.py','--project',out,'begin','--goal','Synthetic unpeopled room fixture','--step','prepare','--step','deliver',parse=False)
    task_id=json.loads((out/'work/current.json').read_text(encoding='utf-8'))['task_id']
    (out/'world.md').write_text('A room contains one lamp. No characters are specified.\n',encoding='utf-8',newline='\n')
    (out/'delivery.txt').write_text('Describe the declared room in one sentence.\n',encoding='utf-8',newline='\n')
    spec={'task_id':task_id,'route':'development','features':[],
          'sources':[{'id':'world','path':'world.md','role':'world','disposition':'applied','locator':'whole','reason':'Synthetic fixture premise.'}],
          'delivery':{'path':'delivery.txt','transport':'authored-rendition','translation_notes':'Minimal declared-world fixture.'},
          'criteria':[{'id':'world','strength':'hard','text':'One lamp, no added characters.','evidence':'text'}], 'sequence_plan':None}
    spec['direction']=support.direction(spec,(out/'delivery.txt').read_text(encoding='utf-8').strip())
    from reading_fixtures import task_reading
    task_reading(out,spec)
    write('task.json',spec)
    result=command('production_workflow.py','prepare','--root',out,'--task','task.json'); rid=result['run']
    def workflow(op,*args): return command('production_workflow.py',op,'--root',out,'--run',rid,*args)
    workflow('handoff','--recipient','synthetic fixture','--method','manual')
    (out/'output.txt').write_text('One lamp stands in the room.\n',encoding='utf-8',newline='\n')
    candidate=workflow('capture','--artifact','output.txt','--note','Handwritten synthetic fixture, not model output.')
    review=workflow('draft-review','--candidate',candidate['sha256'],'--out','review.json')
    review.update(reviewer='synthetic-test-reviewer',observations=[{'locator':{'kind':'lines','start':1,'end':1},'observation':'The fixture names one lamp and no character.','method':'text-inspection'}],conclusion='Synthetic positive fixture, not user approval.')
    review['checks'][0].update(verdict='pass',observation_indices=[0],evidence_basis='technical-measurement',reason='Literal fixture inspection.')
    write('review.json',review); workflow('review','--file','review.json')
    grant=workflow('draft-authorization','--out','grant.json')
    (out/'authority.txt').write_text('SYNTHETIC TEST AUTHORITY; NOT A HUMAN APPROVAL.\n',encoding='utf-8',newline='\n')
    grant.update(principal='synthetic test',actor='synthetic-test-selector',purpose='Exercise a delivery-only selection.',permissions=[{'operation':'select','scopes':['task'],'max_calls':1,'max_outputs':0,'max_cost':'0','currency':'none','request_scope':None,'submission_validation_modes':[]}],evidence={'path':'authority.txt','locator':'whole'})
    write('grant.json',grant);authority=workflow('authorize','--file','grant.json')
    selection=workflow('draft-selection','--candidate',candidate['sha256'],'--out','selection.json')
    selection.update(selector='synthetic-test-selector',reason='Exercise the delivery-only path.',authorization=authority['sha256'])
    write('selection.json',selection); workflow('select','--file','selection.json')
    workflow('complete')
    for i in [1,2]: command('work_ledger.py','--project',out,'step',i,parse=False)
    command('work_ledger.py','--project',out,'finish',parse=False)
    resumed=workflow('resume'); workflow('impact')
    final={'ok':resumed['ok'] and resumed['next']=='done','run':rid,'commands':len(log),'output':str(out/'output.txt'),'fixture_only':True}
    write('result.json',final); return final


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    print(json.dumps(run(a.out.absolute()),indent=2))
if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    main()
