#!/usr/bin/env python3
"""Cross-run permissions, observation intervals and reviewed child-run changes."""
from __future__ import annotations
import copy
import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path
import execution_contract as c
import production_workflow as w
import production_authority as authority
import production_revision as revision
import production_recovery as recovery
import production_test_support as support
import media_evidence as media
import timed_sequence
import timed_test_support
import production_workflow_smoke_test as base_tests


class IntegrityTests(unittest.TestCase):
    setUp=base_tests.ProductionTests.setUp
    prepare=base_tests.ProductionTests.prepare
    captured=base_tests.ProductionTests.captured
    def put(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data if isinstance(data,bytes) else c.encoded(data));return p
    def permission(self,run,**kw):return support.grant(w,self.root,run,actor='test',operations=('edit',),**kw)
    def reserve(self,run,grant,request='c'*64,outputs=1):
        return w.reserve_action(self.root,run,authorization=grant,actor='test',operation='edit',scopes=['task'],request_sha256=request,outputs=outputs)
    def copy_grant(self,run,original,other):
        data=copy.deepcopy(w.find(w.load_run(self.root,original)[3],'authorization',other)['data']['authorization']);data['input_sha256']=w.load_run(self.root,run)[1]['input_sha256']
        self.put('rebound.json',data);return w.authorize(self.root,run,'rebound.json')['sha256']
    def test_repreparation_has_distinct_run_binding(self):
        a=self.prepare();b=self.prepare();self.assertNotEqual(w.load_run(self.root,a)[1]['input_sha256'],w.load_run(self.root,b)[1]['input_sha256'])
    def test_output_ceiling_survives_reprepare(self):
        a=self.prepare();grant=self.permission(a,outputs=1,calls=10);self.reserve(a,grant)
        b=self.prepare();rebound=self.copy_grant(b,a,grant)
        with self.assertRaisesRegex(ValueError,'output limit'):self.reserve(b,rebound,request='d'*64)
    def test_same_request_in_another_run_is_not_a_free_retry(self):
        a=self.prepare();grant=self.permission(a,outputs=1,calls=10);self.reserve(a,grant)
        b=self.prepare();rebound=self.copy_grant(b,a,grant)
        with self.assertRaisesRegex(ValueError,'output limit'):self.reserve(b,rebound)
    def test_call_ceiling_survives_reprepare(self):
        a=self.prepare();grant=self.permission(a,outputs=10,calls=1);self.reserve(a,grant)
        b=self.prepare();rebound=self.copy_grant(b,a,grant)
        with self.assertRaisesRegex(ValueError,'call limit'):self.reserve(b,rebound,request='d'*64)
    def test_same_evidence_cannot_enlarge_permissions(self):
        a=self.prepare();grant=self.permission(a,outputs=1,calls=1);b=self.prepare()
        data=copy.deepcopy(w.find(w.load_run(self.root,a)[3],'authorization',grant)['data']['authorization']);data['input_sha256']=w.load_run(self.root,b)[1]['input_sha256'];data['permissions'][0]['max_outputs']=100
        self.put('enlarged.json',data)
        with self.assertRaisesRegex(ValueError,'same approval'):w.authorize(self.root,b,'enlarged.json')
    def test_machine_stop_survives_repreparation(self):
        a,candidate=self.captured()
        grant=self.permission(a,outputs=2,calls=3)
        original=w.find(w.load_run(self.root,a)[3],'authorization',grant)['data']['authorization']
        # Establish a distinct explicit synthetic approval with this stop condition.
        self.put('halt-proof.txt',b'Synthetic explicit halt-on-review approval.')
        altered=copy.deepcopy(original);altered['halt_on']=['unresolved-review'];altered['evidence']['path']='halt-proof.txt'
        self.put('halt.json',altered);grant=w.authorize(self.root,a,'halt.json')['sha256']
        review=support.observed(w.draft_review(self.root,a,candidate['sha256']));review.update(reviewer='test',conclusion='Unresolved synthetic question.',unresolved=['Cannot yet assess the purpose.'])
        for check in review['checks']:check.update(verdict='not-assessed',evidence_basis='not-assessed',reason='Not assessed.')
        self.put('unresolved.json',review);w.review(self.root,a,'unresolved.json')
        b=self.prepare();rebound=self.copy_grant(b,a,grant)
        with self.assertRaisesRegex(ValueError,'stopped'):self.reserve(b,rebound)
    def test_revocation_blocks_rebinding(self):
        a=self.prepare();grant=self.permission(a,outputs=1,calls=1);w.revoke(self.root,a,grant,'Synthetic revocation');b=self.prepare()
        with self.assertRaisesRegex(ValueError,'revoked'):self.copy_grant(b,a,grant)
    def test_revocation_in_other_run_blocks_execution(self):
        a=self.prepare();grant=self.permission(a,outputs=2,calls=2);b=self.prepare();rebound=self.copy_grant(b,a,grant)
        w.revoke(self.root,a,grant,'Synthetic task-wide revocation')
        with self.assertRaisesRegex(ValueError,'revoked'):self.reserve(b,rebound)
    def video_candidate(self):
        self.task['criteria'][0]['evidence']='video';run=self.prepare();w.handoff(self.root,run,'test','manual')
        output=self.root/'video.mp4'
        p=subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i','color=c=gray:s=32x32:r=24:d=1','-c:v','libx264','-pix_fmt','yuv420p',str(output)],capture_output=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        return run,w.capture(self.root,run,'video.mp4','Synthetic timed evidence, no artistic assessment.')
    def video_review(self,run,candidate,locator):
        d=support.observed(w.draft_review(self.root,run,candidate['sha256']),method='measurement');d['observations'][0]['locator']=locator
        self.put('video-review.json',d);return w.review(self.root,run,'video-review.json')
    def test_video_bytes_do_not_prove_motion(self):
        run,candidate=self.video_candidate()
        with self.assertRaisesRegex(ValueError,'interval'):self.video_review(run,candidate,{'kind':'bytes','start':1,'end':1})
    def test_actual_video_interval_is_supported(self):
        run,candidate=self.video_candidate();self.assertEqual(self.video_review(run,candidate,{'kind':'time','unit':'seconds','start':0,'end':.5,'stream':0})['event'],'review')
    def test_tiny_video_interval_not_multiple_frames(self):
        run,candidate=self.video_candidate()
        with self.assertRaisesRegex(ValueError,'distinct frames'):self.video_review(run,candidate,{'kind':'time','unit':'seconds','start':0,'end':.001,'stream':0})
    def test_stream_duration_not_container_duration(self):
        measured={'kind':'video','duration':9,'streams':[{'index':0,'codec_type':'video','duration':'9','avg_frame_rate':'24/1'},{'index':1,'codec_type':'audio','duration':'1'}]}
        with self.assertRaisesRegex(ValueError,'duration of its stream'):media.validate_locator({'kind':'time','unit':'seconds','start':0,'end':2,'stream':1},b'x',measured)
    def test_unmeasured_stream_cannot_use_container_duration(self):
        with self.assertRaisesRegex(ValueError,'no measured'):media.validate_locator({'kind':'time','unit':'seconds','start':0,'end':.5,'stream':0},b'x',{'kind':'video','duration':9,'streams':[{'index':0,'codec_type':'video','avg_frame_rate':'24/1'}]})
    def reviewed_repair(self):
        run,candidate=self.captured();d=support.observed(w.draft_review(self.root,run,candidate['sha256']));d['checks'][0]['verdict']='fail'
        d['repairs']=[{'decisions':['realization'],'observation_indices':[0],'operation':'Reword the delivered passage','scope':'This deliverable only.','reason':'Observed synthetic defect.','targets':['delivery'],'expected_evidence':'Read the revised passage.'}]
        self.put('review.json',d);w.review(self.root,run,'review.json')
        grant=self.permission(run,outputs=0,calls=2)
        self.put('new-delivery.txt',b'Hold the declared condition. Add the clarified detail.')
        changed=copy.deepcopy(self.task);changed['delivery']['path']='new-delivery.txt';self.put('revised-task.json',changed)
        return run,candidate,grant,changed
    def test_reviewed_revision_creates_empty_child_run(self):
        run,candidate,grant,_=self.reviewed_repair();intent=revision.revision_intent(self.root,run,'revised-task.json',candidate['sha256'],0)
        self.assertEqual(intent['targets'],['delivery'])
        result=revision.revise(self.root,run,'revised-task.json',candidate['sha256'],0,grant,'test');p=w.load_run(self.root,result['run'])
        self.assertEqual(p[1]['parent']['candidate'],candidate['sha256']);self.assertEqual(p[3],[])
        with self.assertRaises(ValueError):w.complete(self.root,result['run'])
    def test_repeated_revision_reuses_child(self):
        run,candidate,grant,_=self.reviewed_repair();args=(self.root,run,'revised-task.json',candidate['sha256'],0,grant,'test')
        first=revision.revise(*args);self.assertEqual(first,revision.revise(*args))
    def test_revision_cannot_change_unreviewed_criterion(self):
        run,candidate,grant,changed=self.reviewed_repair();changed['criteria'][0]['text']='different requirement';self.put('revised-task.json',changed)
        with self.assertRaisesRegex(ValueError,'exceeds'):revision.revise(self.root,run,'revised-task.json',candidate['sha256'],0,grant,'test')
    def test_revision_cannot_name_nonexistent_repair(self):
        run,candidate,grant,_=self.reviewed_repair()
        with self.assertRaisesRegex(ValueError,'repair index'):revision.revision_intent(self.root,run,'revised-task.json',candidate['sha256'],7)
    def test_changed_review_is_not_reused(self):
        run,candidate,grant,_=self.reviewed_repair();self.put('review.json',b'changed')
        with self.assertRaisesRegex(ValueError,'recorded'):revision.revision_intent(self.root,run,'revised-task.json',candidate['sha256'],0)
    def timed_run(self):
        timed_test_support.inputs(self.root);self.task.update(sequence_plan='sequence.json',route='timed-sequence');self.task['criteria'][0]['evidence']='video'
        run=self.prepare();w.handoff(self.root,run,'editor','editor');grant=self.permission(run,outputs=1,calls=2);return run,grant
    def test_timed_result_recovery_does_not_render_again(self):
        run,grant=self.timed_run()
        with patch.object(recovery,'recover',side_effect=OSError('Synthetic publication interruption')):
            with self.assertRaises(OSError):timed_sequence.execute(self.root,run,'movie.mp4',grant,'test')
        with patch.object(timed_sequence,'render_files',side_effect=AssertionError('must not render')):
            candidate=timed_sequence.execute(self.root,run,'movie.mp4',grant,'test')
        self.assertEqual(candidate['event'],'candidate');self.assertTrue((self.root/'movie.mp4').is_file())
    def test_timed_render_failure_does_not_retry(self):
        run,grant=self.timed_run()
        with patch.object(timed_sequence,'render_files',side_effect=ValueError('Synthetic failure')):
            with self.assertRaises(ValueError):timed_sequence.execute(self.root,run,'movie.mp4',grant,'test')
        with patch.object(timed_sequence,'render_files',side_effect=AssertionError('must not rerender')):
            with self.assertRaisesRegex(ValueError,'no retained'):timed_sequence.execute(self.root,run,'movie.mp4',grant,'test')
    def test_actual_sequence_change_scopes(self):
        run,_=self.timed_run();directory,prepared,_,_=w.load_run(self.root,run)
        old={d['sha256']:c.object_read(directory,d['sha256']) for d in prepared['dependencies']}
        value=c.load(self.root/'sequence.json');value['placements'][1]['video']['x']=[5,115];self.put('sequence-next.json',value)
        changed=copy.deepcopy(self.task);changed['sequence_plan']='sequence-next.json';self.put('revised-task.json',changed)
        after,_,_,new=w.snapshot(self.root,'revised-task.json')
        self.assertEqual(revision.changed_scopes(prepared,after,old,new),['placement:moving'])


if __name__=='__main__':unittest.main(verbosity=2)
