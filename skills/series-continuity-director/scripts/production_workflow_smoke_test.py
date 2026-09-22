#!/usr/bin/env python3
"""Actual project-run, authority, observation, selection and ledger tests."""
from pathlib import Path
import copy
import tempfile
import unittest
import execution_contract as c
import production_workflow as w
import production_test_support as support
import work_ledger
import execution_routes

class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        task=work_ledger.begin(self.root,'Synthetic production test',['deliver'])
        (self.root/'brief.txt').write_text('An unpeopled work; no mandatory plot change. PRIVATE dossier text.')
        (self.root/'delivery.txt').write_text('Hold the declared condition.')
        self.task={'task_id':task['task_id'],'route':'development','features':[],
            'sources':[{'id':'brief','path':'brief.txt','role':'world','disposition':'applied','locator':'whole','reason':'Test'}],
            'delivery':{'path':'delivery.txt','transport':'authored-rendition','translation_notes':'Only selected instructions.'},
            'criteria':[{'id':'condition','strength':'hard','text':'Holds the condition','evidence':'text'}],'sequence_plan':None}
        self.task['direction']=support.direction(self.task,'Hold the declared condition.')
    def prepare(self):
        from reading_fixtures import task_reading
        task_reading(self.root,self.task)
        (self.root/'task.json').write_bytes(c.encoded(self.task));return w.prepare(self.root,'task.json')['run']
    def captured(self):
        run=self.prepare();w.handoff(self.root,run,'test','manual');(self.root/'result.txt').write_text('The condition persists.')
        return run,w.capture(self.root,run,'result.txt','Synthetic text fixture.')
    def reviewed(self):
        run,ca=self.captured();r=support.observed(w.draft_review(self.root,run,ca['sha256']));(self.root/'review.json').write_bytes(c.encoded(r));w.review(self.root,run,'review.json');return run,ca
    def selected(self):
        run,ca=self.reviewed();authorization=support.grant(w,self.root,run)
        d=w.draft_selection(self.root,run,ca['sha256']);d.update(selector='synthetic selector',reason='Test delivery only.',authorization=authorization)
        (self.root/'selection.json').write_bytes(c.encoded(d));w.select(self.root,run,'selection.json');return run,authorization
    def scene_task(self):
        import scene_material_smoke_test as material_fixture
        import scene_persona
        material_fixture.fixture(self.root)
        scene_persona.build(self.root, 'plan.json', 'scene-material')
        self.task['route'] = 'performance'
        self.task['features'] = ['scene-persona']
        self.task['scene_materials'] = [{'plan': 'plan.json', 'bundle': 'scene-material'}]
        pass
    def test_scene_material_is_pinned_and_self_contained_in_actual_run(self):
        self.scene_task(); run = self.prepare()
        _, prepared, consumer, _ = w.load_run(self.root, run)
        self.assertIn('Do not replace listening', consumer['authoring_materials'][0]['document'])
        self.assertTrue(any(d['space'] == 'project' and d['path'] == 'persona.md' for d in prepared['dependencies']))
        self.assertNotIn('persona', prepared['route']['features'])
        self.assertFalse(any(r['path'].endswith('persona-template.md') for r in prepared['route']['reads']))
    def test_scene_run_invalidated_by_unquoted_original_content(self):
        self.scene_task(); run = self.prepare()
        with (self.root/'persona.md').open('a') as handle:
            handle.write('A changed contextual exception outside the excerpts.\n')
        self.assertFalse(w.status(self.root, run)['ok'])
    def test_public_material_production_uses_explicit_snapshot_acceptance(self):
        import material_support as m
        self.scene_task()
        value = m.load(self.root, 'scene-material/material.json')
        for source in value['sources']:
            source['path'] = '../../unavailable-private-source'
        value = m.sealed(value)
        (self.root/'received.json').write_bytes(m.encoded(value))
        self.task['scene_materials'] = [{'artifact': 'received.json', 'accepted_content_sha256': value['content_sha256'],
                                   'accepted_by': 'fixture-reviewer', 'acceptance_basis': 'Exact public snapshot, originals unavailable.'}]
        pass
        run = self.prepare(); consumer = w.load_run(self.root, run)[2]
        self.assertEqual(consumer['authoring_materials'][0]['source_integrity'], 'snapshot-only-originals-not-checked')
    def test_actual_failed_review_drives_derived_failure_report(self):
        import repair_analysis
        run, ca = self.captured(); data = support.observed(w.draft_review(self.root, run, ca['sha256']))
        data['checks'][0]['verdict'] = 'fail'; data['unresolved'] = ['A scoped correction needs review.']
        (self.root/'review.json').write_bytes(c.encoded(data)); w.review(self.root, run, 'review.json')
        result = repair_analysis.analyze(self.root, [run], 'derived-failures')
        report = c.load(self.root/'derived-failures/analysis.json')
        self.assertTrue(result['ok']); self.assertEqual(len(report['failure_groups']), 1)
        self.assertFalse(report['execution_authorized'])
    def test_routes_have_owners_and_reads(self):self.assertTrue(execution_routes.validate()['ok'],execution_routes.validate())
    def test_private_sources_do_not_cross_consumer_boundary(self):
        run=self.prepare();self.assertNotIn('PRIVATE',str(w.load_run(self.root,run)[2]))
    def test_actual_review_and_authority_complete_ledger(self):
        run,_=self.selected();w.complete(self.root,run);work_ledger.step_done(self.root,1);work_ledger.finish(self.root);self.assertEqual(w.status(self.root,run)['next'],'done')
    def test_flags_do_not_finish_a_production_run(self):
        self.prepare();work_ledger.step_done(self.root,1)
        with self.assertRaises(ValueError):work_ledger.finish(self.root)
    def test_changed_source_requires_repreparation(self):
        run=self.prepare();(self.root/'brief.txt').write_text('Different premise');self.assertFalse(w.status(self.root,run)['ok']);self.assertEqual(w.impact(self.root,run)['direction']['reconsider_decisions'],['realization'])
    def test_revoked_select_does_not_complete(self):
        run,authorization=self.selected();w.revoke(self.root,run,authorization,'Synthetic revocation')
        with self.assertRaises(ValueError):w.complete(self.root,run)
    def test_no_authority_no_selection(self):
        run,ca=self.reviewed();d=w.draft_selection(self.root,run,ca['sha256']);d.update(selector='test',reason='Test',authorization='a'*64);(self.root/'selection.json').write_bytes(c.encoded(d))
        with self.assertRaises(ValueError):w.select(self.root,run,'selection.json')
    def test_text_cannot_pass_a_video_criterion(self):
        self.task['criteria'][0]['evidence']='video';run,ca=self.captured();d=support.observed(w.draft_review(self.root,run,ca['sha256']));(self.root/'review.json').write_bytes(c.encoded(d))
        with self.assertRaises(ValueError):w.review(self.root,run,'review.json')
    def test_failed_review_needs_a_repair_or_unresolved_issue(self):
        run,ca=self.captured();d=support.observed(w.draft_review(self.root,run,ca['sha256']));d['checks'][0]['verdict']='fail';(self.root/'review.json').write_bytes(c.encoded(d))
        with self.assertRaises(ValueError):w.review(self.root,run,'review.json')
    def test_timed_route_requires_its_plan(self):
        self.task['route']='timed-sequence'
        with self.assertRaises(ValueError):self.prepare()
    def test_completed_run_is_immutable(self):
        run,_=self.selected();w.complete(self.root,run);(self.root/'other.txt').write_text('Other output')
        with self.assertRaises(ValueError):w.capture(self.root,run,'other.txt','Not the completed choice')
    def test_recorded_output_change_is_detected(self):
        run,ca=self.captured();(self.root/'result.txt').write_text('Changed artifact');self.assertFalse(w.status(self.root,run)['ok'])

if __name__=='__main__':unittest.main(verbosity=2)
