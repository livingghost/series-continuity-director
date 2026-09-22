#!/usr/bin/env python3
"""An actual reviewed passage -> scoped child -> observed completion, using test authority."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import execution_contract as c
import production_workflow as w
import production_revision as changes
import production_test_support as support
import work_ledger


def run(out: Path) -> dict:
    if out.exists():raise ValueError('choose a new output directory')
    out.mkdir(parents=True)
    def write(name,value):
        (out/name).write_bytes(value if isinstance(value,bytes) else value.encode() if isinstance(value,str) else c.encoded(value))
    opened=work_ledger.begin(out,'A synthetic scoped repair, not literary evaluation.',['deliver'])
    write('source.txt','A field of dots is held; no cast or chronology is specified.')
    write('delivery.txt','Describe the held field in one sentence.')
    task={'task_id':opened['task_id'],'route':'development','features':['reviewed-repair'],
        'sources':[{'id':'field','path':'source.txt','role':'world','disposition':'applied','locator':'whole','reason':'Explicit synthetic premise.'}],
        'delivery':{'path':'delivery.txt','transport':'authored-rendition','translation_notes':'Only the declared realization.'},
        'criteria':[{'id':'held','strength':'hard','text':'A field persists without added motion.','evidence':'text'}],'sequence_plan':None}
    task['direction']=support.direction(task,(out/'delivery.txt').read_text())
    from reading_fixtures import task_reading
    task_reading(out,task)
    write('task.json',task)
    parent=w.prepare(out,'task.json')['run'];w.handoff(out,parent,'synthetic operator','manual')
    write('initial.txt','The field moves.');initial=w.capture(out,parent,'initial.txt','A deliberately mismatching synthetic passage.')
    review=support.observed(w.draft_review(out,parent,initial['sha256']),'The literal passage adds motion.')
    review['checks'][0].update(verdict='fail',reason='The written verb conflicts with the declared held state.')
    review['repairs']=[{'decisions':['realization'],'observation_indices':[0],'operation':'Clarify the delivered wording.',
        'scope':'This passage only.','targets':['delivery'],'reason':'Keep the declared unchanging state.','expected_evidence':'Read the new passage.'}]
    write('review.json',review);review_record=w.review(out,parent,'review.json')
    authority=support.grant(w,out,parent,actor='synthetic operator',operations=('edit',),outputs=0,calls=1)
    revised=copy.deepcopy(task);revised['delivery']['path']='revised-delivery.txt'
    write('revised-delivery.txt','Describe the held field in one sentence. Explicitly retain its position without adding motion.');write('revised-task.json',revised)
    intent=changes.revision_intent(out,parent,'revised-task.json',initial['sha256'],0);write('repair-intent.json',intent)
    child=changes.revise(out,parent,'revised-task.json',initial['sha256'],0,authority,'synthetic operator')['run']
    if w.load_run(out,child)[3]:raise ValueError('child inherited records')
    w.handoff(out,child,'synthetic operator','manual');write('corrected.txt','The field remains in place.')
    candidate=w.capture(out,child,'corrected.txt','A revised synthetic passage, inspected as text.')
    reviewed=support.observed(w.draft_review(out,child,candidate['sha256']),'The literal passage says the field remains in place.')
    write('corrected-review.json',reviewed);w.review(out,child,'corrected-review.json')
    select_authority=support.grant(w,out,child,actor='synthetic operator',operations=('select',),calls=1)
    choice=w.draft_selection(out,child,candidate['sha256']);choice.update(selector='synthetic operator',reason='Select the observed synthetic passage.',authorization=select_authority)
    write('selection.json',choice);w.select(out,child,'selection.json');done=w.complete(out,child)
    work_ledger.step_done(out,1);work_ledger.finish(out)
    result={'ok':True,'parent':parent,'child':child,'review':review_record['sha256'],'targets':intent['targets'],
            'completion':done['sha256'],'limits':['Explicit test authority only; no literary or audience evaluation.']}
    write('result.json',result);return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    try:print(json.dumps(run(args.out.absolute()),indent=2));return 0
    except (ValueError,OSError) as exc:print(json.dumps({'ok':False,'error':str(exc)}));return 1
if __name__=='__main__':raise SystemExit(main())
