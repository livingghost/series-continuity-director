#!/usr/bin/env python3
"""Actual project-run, authority, observation, selection and ledger tests."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import execution_contract as c
import production_workflow as w
import production_test_support as support
import work_ledger
import execution_routes
from reading_fixtures import task_reading

SCRIPTS = Path(__file__).resolve().parent

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
    def test_impact_names_the_runs_that_used_a_material(self):
        import scene_persona
        self.scene_task(); run, _ = self.selected()
        rows = scene_persona.impact(self.root)['scenes']
        self.assertEqual([(row['material'], row['runs']) for row in rows],
                         [('scene-material/material.json', [{'run': run, 'selection_recorded': True}])])
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
    def test_prepare_updates_the_open_task_under_the_project_lock(self):
        task_reading(self.root,self.task);(self.root/'task.json').write_bytes(c.encoded(self.task))
        held=[];original=work_ledger.write_current
        def observed(root,value):
            held.append(str(root.resolve()) in getattr(c._held_locks,'roots',set()));original(root,value)
        with patch.object(work_ledger,'write_current',side_effect=observed):
            run=w._prepare(self.root,'task.json')['run']
        self.assertEqual(held,[True]);self.assertEqual(work_ledger.read_current(self.root)['production_run'],run)
    def test_run_listing_ignores_templates_and_file_manager_entries(self):
        run=self.prepare();folder=self.root/'production'
        for name in ('desktop.ini','Thumbs.db','.DS_Store','production-task.json'):(folder/name).write_bytes(b'synthetic entry')
        (folder/'notes').mkdir();(folder/'00000000-0000-4000-8000-000000000000').mkdir()
        self.assertEqual(w.run_ids(self.root),[run])


def cli(*args):
    """Run one documented production_workflow.py command and decode its JSON output."""
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    done=subprocess.run([sys.executable,str(SCRIPTS/'production_workflow.py'),*map(str,args)],
                        capture_output=True,text=True,encoding='utf-8',env=env)
    return done.returncode,json.loads(done.stdout),done.stderr


class InitializedProjectTests(unittest.TestCase):
    """The flow in references/production-execution.md, in a project init_project.py created."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'project'
        subprocess.run([sys.executable,str(SCRIPTS/'init_project.py'),'--out',str(self.root),
                        '--series-id','synthetic-series','--title','Synthetic series'],check=True,capture_output=True)
        production=self.root/'production'
        for name in ('desktop.ini','Thumbs.db','.DS_Store'):(production/name).write_bytes(b'Synthetic file manager entry.')
        (production/'notes').mkdir()
        opened=work_ledger.begin(self.root,'Synthetic initialized project',['deliver'])
        (self.root/'brief.md').write_text('A synthetic brief for an initialized project.\n',encoding='utf-8')
        (self.root/'delivery.txt').write_text('Hold the declared condition.\n',encoding='utf-8')
        # The shipped task template, filled in where it stands.
        task=c.load(production/'production-task.json');task['task_id']=opened['task_id']
        task['direction']=support.direction(task,'Hold the declared condition.');task_reading(self.root,task)
        (production/'production-task.json').write_bytes(c.encoded(task))
    def ok(self,*args):
        code,out,err=cli(*args);self.assertEqual((code,err),(0,''),out);return out
    def fill(self,name,**fields):
        value=c.load(self.root/name);value.update(fields);(self.root/name).write_bytes(c.encoded(value))
    def selection(self,artifact,operations):
        root=['--root',self.root]
        run=self.ok('prepare',*root,'--task','production/production-task.json')['run'];at=[*root,'--run',run]
        self.ok('handoff',*at,'--recipient','synthetic operator','--method','manual')
        candidate=self.ok('capture',*at,'--artifact',artifact,'--note','Synthetic acquired artifact.')['sha256']
        self.ok('draft-review',*at,'--candidate',candidate,'--out','review.json')
        (self.root/'review.json').write_bytes(c.encoded(support.observed(c.load(self.root/'review.json'))))
        self.ok('review',*at,'--file','review.json')
        self.ok('draft-authorization',*at,'--out','grant.json')
        (self.root/'grant-evidence.txt').write_text('SYNTHETIC AUTHORITY FIXTURE. NOT A HUMAN APPROVAL.\n',encoding='utf-8')
        self.fill('grant.json',principal='SYNTHETIC TEST PRINCIPAL, NOT USER CONSENT',actor='synthetic selector',
            purpose='Only this synthetic test.',evidence={'path':'grant-evidence.txt','locator':'whole'},
            permissions=[{'operation':op,'scopes':['task'],'max_calls':1,'max_outputs':0,'max_cost':'0','currency':'none',
                          'request_scope':None,'submission_validation_modes':[]} for op in operations])
        authorization=self.ok('authorize',*at,'--file','grant.json')['sha256']
        self.ok('draft-selection',*at,'--candidate',candidate,'--out','selection.json')
        self.fill('selection.json',selector='synthetic selector',reason='Synthetic selection.',authorization=authorization)
        return at,candidate
    def test_documented_flow_completes_beside_templates_and_file_manager_entries(self):
        (self.root/'result.txt').write_text('The condition persists.\n',encoding='utf-8')
        at,_=self.selection('result.txt',('select',))
        self.ok('select',*at,'--file','selection.json');self.ok('complete',*at)
        self.assertEqual(self.ok('status',*at)['next'],'done')
    def registry(self,digest):
        """Fill the shipped registry template's identity record the way its fields ask."""
        text=(self.root/'asset-registry.md').read_text(encoding='utf-8')
        record,rest=text.split('### S01-SCENE',1)
        record=record.replace('- role:\n','- role: C01/identity\n',1).replace('- status: candidate\n','- status: accepted\n',1)
        record=record.replace('- files and views:\n','- files and views:\n  - `media/c01-identity.png` (front view)\n',1)
        record=record.replace('- SHA-256 per file:\n','- SHA-256 per file:\n  - `media/c01-identity.png`: '+digest+'\n',1)
        (self.root/'asset-registry.md').write_text(record+'### S01-SCENE'+rest,encoding='utf-8')
    def adopting(self):
        from PIL import Image
        Image.new('RGB',(8,8),(40,40,40)).save(self.root/'media/c01-identity.png')
        at,candidate=self.selection('media/c01-identity.png',('select','adopt'))
        self.fill('selection.json',scope='registry-adoption',
                  adoption={'owner_path':'asset-registry.md','asset_id':'C01-IDENTITY','role':'C01/identity'})
        return at,c.digest((self.root/'media/c01-identity.png').read_bytes())
    def test_template_registry_record_adopts_the_candidate(self):
        at,digest=self.adopting();self.registry(digest.upper())
        selected=self.ok('select',*at,'--file','selection.json')
        self.assertIn('asset-registry.md',[f['path'] for f in selected['data']['files']])
        self.ok('complete',*at)
    def test_template_registry_record_with_other_bytes_is_refused(self):
        at,_=self.adopting();self.registry('0'*64)
        code,out,err=cli('select',*at,'--file','selection.json')
        self.assertEqual((code,err,out['ok']),(1,'',False));self.assertIn('exact candidate path and bytes',out['error'])
    def test_missing_root_is_one_error_and_creates_nothing(self):
        missing=self.root/'mistyped'/'deeper'
        for command in ('status','impact','draft-authorization'):
            args=[command,'--root',missing,'--run',c.new_run_id()]+(['--out','grant.json'] if command=='draft-authorization' else [])
            code,out,err=cli(*args)
            self.assertEqual((code,err,out['ok']),(1,'',False));self.assertIn('not an existing directory',out['error'])
        self.assertFalse((self.root/'mistyped').exists())
    def test_malformed_record_is_one_json_error(self):
        run=self.ok('prepare','--root',self.root,'--task','production/production-task.json')['run']
        (self.root/'grant.json').write_bytes(c.encoded(['not','an','object']))
        code,out,err=cli('authorize','--root',self.root,'--run',run,'--file','grant.json')
        self.assertEqual((code,err,out['ok']),(1,'',False));self.assertIn('malformed record',out['error'])

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
