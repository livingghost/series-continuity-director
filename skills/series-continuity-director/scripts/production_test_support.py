"""Synthetic current-form fixtures. Never represents real user authorization."""
from pathlib import Path
import execution_contract as c

def direction(task, instructions):
    return {'purpose':'Exercise this declared synthetic production task.',
      'intended_effect':'Known fixture behavior; not evidence of audience effect.',
      'basis':[{'source':s['id'],'applicability':'Applicable synthetic premise, retained in full.'} for s in task['sources'] if s['disposition']=='applied'],
      'decisions':[{'id':'realization','question':'How is this fixture realized?','compare':False,
        'options':[{'id':'specified','realization':instructions,'consequence':'A measured fixture, not proof of artistic merit.'}],
        'selected':'specified','reason':'Explicit fixture requirement.', 'criteria':[x['id'] for x in task['criteria']]}],
      'departures':[],'action_context':None,'verification_limits':['Synthetic tests do not demonstrate acting or audience response.']}

def grant(workflow, root, run, actor='synthetic selector', operations=('select',), outputs=0, calls=10, cost='0',currency='none'):
    name='grant-'+c.new_run_id()
    data=workflow.draft_authorization(root,run)
    data.update(principal='SYNTHETIC TEST PRINCIPAL, NOT USER CONSENT',actor=actor,purpose='Only this synthetic test.',
        permissions=[{'operation':op,'scopes':['task'],'max_calls':calls,'max_outputs':outputs,'max_cost':cost,'currency':currency} for op in operations],
        evidence={'path':name+'.txt','locator':'whole'})
    (root/(name+'.txt')).write_text('SYNTHETIC AUTHORITY FIXTURE. NOT A HUMAN APPROVAL.\n',encoding='utf-8')
    (root/(name+'.json')).write_bytes(c.encoded(data))
    return workflow.authorize(root,run,name+'.json')['sha256']

def observed(data, text='The synthetic file was inspected.', method='text-inspection'):
    data.update(reviewer='synthetic reviewer',observations=[{'locator':{'kind':'whole'},'observation':text,'method':method}],conclusion='Synthetic integrity check only.')
    for check in data['checks']:check.update(verdict='pass',observation_indices=[0],evidence_basis='technical-measurement',reason='Actual synthetic fixture.')
    return data
