#!/usr/bin/env python3
"""No-network tests of real claim, output recording and no-resend recovery."""
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import execution_contract as c
import production_workflow as w
import production_dispatch as d
import production_test_support as support
import work_ledger
import transport_runware as transport

class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        task=work_ledger.begin(self.root,'Synthetic bounded dispatch',['deliver'])
        self.spec={'submission_id':'fixture','kind':'asset','service':'runware','target':'fixture',
            'model':'synthetic-target',
            'operation':'imageInference','text':'Hold the declared condition.','inputs':[],
            'parameters':{'numberResults':1},'output':{'dir':'outputs','basename':'fixture','suffix':'.txt'}}
        self.service={'operations':{'imageInference':{}},'endpoint':{'base_url':'https://example.invalid/not-contacted'}}
        (self.root/'services.json').write_bytes(c.encoded({'services':{'runware':self.service}}))
        (self.root/'spec.json').write_bytes(c.encoded(self.spec));(self.root/'prompt.txt').write_text(self.spec['text'])
        self.task={'task_id':task['task_id'],'route':'development','features':[],
            'sources':[{'id':n,'path':n+'.json','role':'configuration','disposition':'applied','locator':'whole','reason':'Synthetic bound.'} for n in ['spec','services']],
            'delivery':{'path':'prompt.txt','transport':'authored-rendition','translation_notes':'Test only.'},
            'criteria':[{'id':'hold','text':'The condition is recorded.','strength':'hard','evidence':'text'}],
            'sequence_plan':None}
        self.task['sources'].append({'id': 'target-profile', 'path': 'profiles/fixture.json',
            'role': 'configuration', 'disposition': 'applied', 'locator': 'whole', 'reason': 'Synthetic target interface.'})
        self.task['direction']=support.direction(self.task,self.spec['text']);self.run=None;self.reserved_outputs=1
        self.answer={'data':[{'taskUUID':'one','imageURL':'https://example.invalid/result'}]}
        self.report={'status':'admitted','unmeasured':['Synthetic provider; no actual quality test.']}
    def prepare(self):
        from reading_fixtures import task_reading
        self.profile, self.offering, self.profiles = support.model_inputs(self.root, self.spec, self.service)
        task_reading(self.root,self.task)
        (self.root/'spec.json').write_bytes(c.encoded(self.spec));(self.root/'task.json').write_bytes(c.encoded(self.task))
        self.run=w.prepare(self.root,'task.json')['run'];w.handoff(self.root,self.run,'mock provider','dispatcher')
        self.auth=support.grant(w,self.root,self.run,operations=('submit','select'),outputs=self.reserved_outputs,stop_conditions=['Synthetic reviewed condition'])
    def invoke(self,**changes):
        if self.run is None:self.prepare()
        options=dict(authorization=self.auth,actor='synthetic selector',outputs=self.reserved_outputs,cost='0',currency='none',poll=False)
        decision_change = changes.pop('decision_change', None)
        options.update(changes)
        consumer = w.assert_current(self.root, self.run)[2]
        built, report, _ = d.render(self.root, self.spec, self.service, self.offering, transport, self.profiles, consumer=consumer)
        decision = support.model_decision(w, self.root, self.run, self.auth, built['rendered'])
        if decision_change is not None:
            decision_change(decision)
        return d.execute(self.root,self.run,self.root/'spec.json',self.spec,self.root/'services.json',self.service,self.offering,report,transport,'not-a-credential',
                         profiles=self.profiles, decision=decision, rendered=built['rendered'], **options)
    def guards(self):
        return patch.object(transport,'send',return_value=self.answer),patch.object(transport,'upload_bytes',side_effect=AssertionError('not expected')),patch('urllib.request.urlopen',side_effect=lambda *a,**k:io.BytesIO(b'Actual returned text.'))
    def test_actual_record_and_review_selection_completion(self):
        a,b,z=self.guards()
        with a as send,b,z:self.invoke();self.assertEqual(send.call_count,1)
        _,p,_,rows=w.load_run(self.root,self.run);candidate=w.find(rows,'candidate');r=support.observed(w.draft_review(self.root,self.run,candidate['sha256']))
        (self.root/'review.json').write_bytes(c.encoded(r));w.review(self.root,self.run,'review.json')
        sel=w.draft_selection(self.root,self.run,candidate['sha256']);sel.update(selector='synthetic selector',authorization=self.auth,reason='Synthetic fixture only.')
        (self.root/'select.json').write_bytes(c.encoded(sel));w.select(self.root,self.run,'select.json');w.complete(self.root,self.run)
        self.assertEqual(w.status(self.root,self.run)['next'],'done')
    def test_no_authority_no_send(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):self.invoke(authorization='a'*64)
        self.assertEqual(send.call_count,0)
    def test_count_mismatch_no_send(self):
        self.spec['parameters']['numberResults']=2;a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):self.invoke()
        self.assertEqual(send.call_count,0)
    def test_options_cannot_replace_the_prepared_text(self):
        self.spec['options']={'positivePrompt':'A different instruction.'};a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):self.invoke()
        self.assertEqual(send.call_count,0)
    def test_unknown_result_is_not_resent(self):
        with patch.object(transport,'send',side_effect=OSError('Synthetic lost connection')) as send:
            with self.assertRaises(OSError):self.invoke()
            with self.assertRaises(ValueError):self.invoke()
            self.assertEqual(send.call_count,1)
        self.assertIn('recover',w.status(self.root,self.run)['next'])
    def test_recovery_only_downloads_known_result(self):
        with patch.object(transport,'send',return_value=self.answer),patch('urllib.request.urlopen',side_effect=OSError('Synthetic download failure')):
            with self.assertRaises(OSError):self.invoke()
        claim=w.find(w.load_run(self.root,self.run)[3],'dispatch-claim')['sha256']
        with patch.object(transport,'send',side_effect=AssertionError('resend')),patch.object(transport,'upload_bytes',side_effect=AssertionError('reupload')),patch('urllib.request.urlopen',return_value=io.BytesIO(b'Actual returned text.')):
            result=d.obtain(self.root,self.run,claim,transport,'',poll=False,poll_seconds=0,poll_limit=0)
        self.assertEqual(result['event'],'dispatch-results');self.assertEqual(w.status(self.root,self.run)['next'],'review')
    def test_modified_trace_stops_recovery(self):
        a,b,z=self.guards()
        with a,b,z:self.invoke()
        claim=w.find(w.load_run(self.root,self.run)[3],'dispatch-claim')['sha256']
        (w.run_dir(self.root,self.run)/'dispatch'/claim/'answer.json').write_text('{}')
        with self.assertRaises(ValueError):d.obtain(self.root,self.run,claim,transport,'',poll=False,poll_seconds=0,poll_limit=0)
    def test_more_results_than_authorized_not_registered(self):
        self.answer['data'].append({'taskUUID':'two','imageURL':'https://example.invalid/other'});a,b,z=self.guards()
        with a,b,z,self.assertRaises(ValueError):self.invoke()
        self.assertFalse(any(r['event']=='candidate' for r in w.load_run(self.root,self.run)[3]))
    def test_source_mutation_before_send_is_detected(self):
        self.prepare();(self.root/'prompt.txt').write_text('Different premise');a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):self.invoke()
        self.assertEqual(send.call_count,0)
    def test_polling_existing_task_records_actual_output(self):
        self.answer={'data':[{'taskUUID':'one'}]}
        a,b,z=self.guards()
        with a as send,b,z,patch.object(transport,'poll',return_value={'data':[{'taskUUID':'one','imageURL':'https://example.invalid/result'}]}) as poll:
            self.invoke(poll=True,poll_limit=1,poll_seconds=0);self.assertEqual(send.call_count,1);self.assertEqual(poll.call_count,1)

    def test_one_pending_task_can_return_multiple_artifacts(self):
        self.spec['parameters']['numberResults']=2;self.reserved_outputs=2
        self.answer={'data':[{'taskUUID':'one'}]}
        returned={'data':[{'taskUUID':'one','imageURL':'https://example.invalid/first'},
                          {'taskUUID':'one','imageURL':'https://example.invalid/second'}]}
        a,b,z=self.guards()
        with a as send,b,z,patch.object(transport,'poll',return_value=returned):
            result=self.invoke(poll=True,poll_limit=1,poll_seconds=0)
            self.assertEqual(send.call_count,1);self.assertEqual(len(result['data']['files']),2)
        merged=[r for r in w.load_run(self.root,self.run)[3] if r['event']=='dispatch-trace' and r['data']['stage'].startswith('answer-merged-')][-1]
        data=c.decode(c.object_read(w.run_dir(self.root,self.run),merged['data']['files'][0]['sha256']))
        self.assertEqual({e['url'] for e in data['entries']},{e['imageURL'] for e in returned['data']})

    def test_poll_merge_retains_previously_completed_artifacts(self):
        self.spec['parameters']['numberResults']=2;self.reserved_outputs=2
        self.answer={'data':[{'taskUUID':'one','imageURL':'https://example.invalid/first'},{'taskUUID':'two'}]}
        returned={'data':[{'taskUUID':'two','imageURL':'https://example.invalid/second'}]}
        a,b,z=self.guards()
        with a,b,z,patch.object(transport,'poll',return_value=returned):
            result=self.invoke(poll=True,poll_limit=1,poll_seconds=0)
        self.assertEqual(len(result['data']['files']),2)

    def test_review_of_other_request_never_sends(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):
            self.invoke(decision_change=lambda value: value['rendition_review'].update(request_sha256='f'*64))
        self.assertEqual(send.call_count,0)

    def test_missing_stop_assessment_never_sends(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):
            self.invoke(decision_change=lambda value: value.update(stop_assessments=[]))
        self.assertEqual(send.call_count,0)

    def test_unsatisfied_review_never_sends(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):
            self.invoke(decision_change=lambda value: value['rendition_review'].update(conclusion='unmeasured'))
        self.assertEqual(send.call_count,0)

    def test_missing_principal_approval_without_delegation_never_sends(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):
            self.invoke(decision_change=lambda value: value.update(principal_approval=None))
        self.assertEqual(send.call_count,0)

    def test_trace_binds_reserved_request(self):
        a,b,z=self.guards()
        with a,b,z:self.invoke()
        rows=w.load_run(self.root,self.run)[3];claim=w.find(rows,'dispatch-claim')
        reservation=w.find(rows,'reservation',claim['data']['reservation'])
        self.assertEqual(claim['data']['manifest']['request_sha256'],reservation['data']['request_sha256'])
        self.assertEqual(claim['data']['manifest']['request_sha256'],claim['data']['manifest']['rendered']['request_sha256'])

    def test_successful_dispatch_can_be_observed_without_network(self):
        import model_observation
        a,b,z=self.guards()
        with a,b,z:self.invoke()
        with patch.object(transport,'send',side_effect=AssertionError('send during observation')), \
             patch.object(transport,'upload_bytes',side_effect=AssertionError('upload during observation')):
            result=model_observation.publish(self.root,self.run,self.root/'observations',relative_prefix='observations')
        self.assertEqual(result['outcome'],'completed')
        self.assertTrue((self.root/result['profile']['path']).is_file())

if __name__=='__main__':unittest.main(verbosity=2)
