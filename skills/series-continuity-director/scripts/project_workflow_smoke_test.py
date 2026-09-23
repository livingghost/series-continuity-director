#!/usr/bin/env python3
"""Exercise project initialization, resource selection and submission preparation."""
from __future__ import annotations
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import resource_files
import vocabulary
import build_resources
import dispatch
import transport_runware
import state_protocol
import narrative
import scene_plot

ROOT=Path(__file__).resolve().parents[1]

class ProjectWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='directing-workspace-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        # Children print JSON with non-ASCII paths; pin their stdout to UTF-8 on every host locale.
        self.env={'HOME':str(self.root/'home'),'PATH':os.environ.get('PATH',''),'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'}
        Path(self.env['HOME']).mkdir()
        self.guard=patch.dict(os.environ,self.env,clear=True);self.guard.start();self.addCleanup(self.guard.stop)
    def save(self,name,value):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value));return p
    def command(self,script,*args):
        return subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],cwd=self.root,env=os.environ.copy(),capture_output=True,encoding='utf-8',timeout=30)
    def test_bundled_vocabulary_without_user_state(self):
        data,path=vocabulary.load();self.assertEqual(path,ROOT/'assets/resources/prompt-vocabulary.json');self.assertIn('close-up',vocabulary.index(data))
    def test_prose_is_read_for_the_terms_inside_it(self):
        data,_=vocabulary.load()
        prose=('A wide shot at eye level from across the wet lane, the courier small at frame left and walking '
               'toward the lit stall, lanterns strung overhead and receding into the rain beyond the awning.')
        rows=vocabulary.describe(prose,data)
        self.assertEqual(vocabulary.text_form(rows),'prose')
        self.assertIn('eye level',[row['term'] for row in vocabulary.terms_inside(rows,data)])
        self.assertEqual(vocabulary.text_form(vocabulary.describe('close-up, eye level, rain',data)),'tags')
    def test_vocabulary_source_is_reproducible(self):
        self.assertEqual(build_resources.build(),json.loads((ROOT/build_resources.OUTPUT).read_text()))
    def test_explicit_resource_file(self):
        p=self.save('vocabulary.json',{'categories':[]});self.assertEqual(resource_files.resolve_resource('prompt-vocabulary',str(p)),p)
    def test_invalid_explicit_resource_not_replaced(self):
        self.assertRaises(ValueError,resource_files.resolve_resource,'prompt-vocabulary',str(self.root/'missing.json'))
    def test_explicit_environment_resource(self):
        p=self.save('terms.json',{'categories':[]});os.environ['VOCABULARY_PATH']=str(p);self.assertEqual(vocabulary.load()[1],p)
    def test_explicit_config_must_exist(self):
        os.environ['SERIES_RESOURCES']=str(self.root/'missing.json');self.assertRaises(ValueError,resource_files.resolve_resource,'prompt-vocabulary')
    def test_configured_relative_resource(self):
        wanted=self.save('data/terms.json',{'categories':[]});p=self.save('resources.json',{'resources':{'prompt-vocabulary':'data/terms.json'}});os.environ['SERIES_RESOURCES']=str(p);self.assertEqual(resource_files.resolve_resource('prompt-vocabulary'),wanted)
    def test_malformed_resource_configuration(self):
        p=self.save('resources.json',{'resources':[]});os.environ['SERIES_RESOURCES']=str(p);self.assertRaises(ValueError,resource_files.resolve_resource,'prompt-vocabulary')
    def test_resource_file_precedes_catalog(self):
        wanted=self.save('chosen.json',{'categories':[]});p=self.save('resources.json',{'resources':{'prompt-vocabulary':'missing.json'}});os.environ['SERIES_RESOURCES']=str(p);self.assertEqual(resource_files.resolve_resource('prompt-vocabulary',str(wanted)),wanted)
    def test_missing_selected_file_does_not_use_bundled_resource(self):
        p=self.save('resources.json',{'resources':{'prompt-vocabulary':'missing.json'}});os.environ['SERIES_RESOURCES']=str(p);self.assertRaises(ValueError,resource_files.resolve_resource,'prompt-vocabulary')
    def init(self, name='project', medium='screen'):
        project=self.root/name
        result=self.command('init_project.py','--out',project,'--series-id','FIXTURE-SERIES','--title','Fixture series','--medium',medium)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return project,json.loads(result.stdout)
    def test_fresh_medium_workspaces(self):
        # A fresh project reports only the authoring nobody has done yet, and
        # its coverage table counts the units its medium has.
        units={'screen':['shots'],'comics':['pages'],'prose':['passages'],'mixed':['shots','pages','passages']}
        for medium,kinds in units.items():
            with self.subTest(medium=medium):
                project,created=self.init(medium,medium)
                self.assertEqual(json.loads((project/'narrative/narrative.json').read_text())['medium'],medium)
                result=self.command('validate_project.py',project);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(json.loads(result.stdout)['warnings'],['the narrative is not approved, so everything below is measured against a document nobody has signed off'])
                self.assertFalse(list((project/'narrative/personas').glob('c01*.md')))
                self.assertIn('session_entry_points.py',created['next'][0]['run']);self.assertIn('--next',created['next'][0]['run'])
                header=self.command('narrative_coverage.py',project).stdout.splitlines()[2].split()
                self.assertEqual([word for word in header if word in ('shots','pages','passages')],kinds)
    def test_project_persona_creation(self):
        project,_=self.init()
        result=self.command('narrative_entity.py','--project',project,'add','persona','second','--character','C02');self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        text=(project/'narrative/personas/second.md').read_text(encoding='utf-8');self.assertGreater(len(text.splitlines()),1000)
    def test_design_record_named_by_init(self):
        project,created=self.init()
        self.assertIn('add design project',created['next'][1]['run'])
        result=self.command('narrative_entity.py','--project',project,'add','design','project','--name','Fixture series')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue((project/'narrative/design/project.md').is_file())
    def test_validate_reports_each_problem_once(self):
        project,_=self.init()
        (project/'narrative/scenes/sc01-plot.json').write_text('{"artifact_type": "scene-plot",, }',encoding='utf-8')
        report=json.loads(self.command('validate_project.py',project).stdout)
        naming=[message for message in report['errors'] if 'sc01-plot.json' in message]
        self.assertEqual(len(naming),1,report['errors'])
        self.assertTrue(naming[0].startswith('narrative/scenes/sc01-plot.json: not valid JSON'),naming[0])
        self.assertFalse([message for message in report['errors']+report['warnings'] if chr(92) in message])
        self.assertEqual(len(report['errors']),len(set(report['errors'])))
    def test_validate_names_a_mistyped_project_once(self):
        for target,fragment in ((self.root/'no-such-project','the directory does not exist'),(self.root,'has no project-manifest.json')):
            with self.subTest(target=target.name):
                result=self.command('validate_project.py',target);report=json.loads(result.stdout)
                self.assertNotEqual(result.returncode,0);self.assertEqual(len(report['errors']),1,report['errors']);self.assertIn(fragment,report['errors'][0])
    def test_work_ledger_writes_only_into_a_project(self):
        loose=self.root/'loose';loose.mkdir()
        for argv,fragment,written in ((['--project',loose],'has no project-manifest.json',loose/'work'),([],'has no project-manifest.json',self.root/'work'),(['--project',ROOT],'inside the installed suite',ROOT/'work')):
            with self.subTest(argv=argv):
                result=self.command('work_ledger.py',*argv,'begin','--goal','g','--step','s')
                self.assertNotEqual(result.returncode,0);self.assertIn(fragment,result.stderr);self.assertFalse(written.exists())
    def test_writers_refuse_the_installed_suite(self):
        inside=ROOT/'scd-suite-write-probe'
        result=self.command('init_project.py','--out',inside,'--series-id','FIXTURE-SERIES','--title','Fixture')
        self.assertNotEqual(result.returncode,0);self.assertIn('inside the installed suite',result.stderr);self.assertFalse(inside.exists())
        result=self.command('init_line.py','--project',ROOT,'--line','E01')
        self.assertNotEqual(result.returncode,0);self.assertIn('inside the installed suite',result.stderr);self.assertFalse((ROOT/'media').exists())
    def test_next_asks_for_the_story_before_its_approval(self):
        import session_entry_points as entry
        project,_=self.init()
        actions=entry.next_actions(project)
        self.assertTrue(actions[0].startswith('Write what the series is about'),actions)
        self.assertFalse(any(action.startswith('Approve the narrative') for action in actions))
    def test_next_names_identity_sheets_and_shot_records(self):
        import session_entry_points as entry
        project,_=self.init()
        plot={'scene_id':'SC01','characters':['C01','C02'],'realization':{'kind':'shots','units':[{'id':'SH01'},{'id':'SH02'}]}}
        sheets=entry.identity_sheet_action(project,[plot],{'C01/identity':['accepted']})
        self.assertIn('identity sheet of C02 before',sheets);self.assertIn('--subject C02 recurring C02',sheets)
        self.assertIsNone(entry.identity_sheet_action(project,[dict(plot,characters=['C01'])],{}))
        (project/'shots'/'SC01').mkdir(parents=True,exist_ok=True)
        (project/'shots'/'SC01'/'SH01.camera.json').write_text(json.dumps({'artifact_type':'shot-camera-spec','scene_id':'SC01','shot_id':'SH01'}))
        actions=entry.shot_record_actions(project,[plot])
        self.assertIn('Place the camera for SC01 SH02',actions[0]);self.assertIn('Write the shot request for SC01 SH01',actions[1])
    def test_line_keeps_the_id_as_given(self):
        project,_=self.init()
        result=self.command('init_line.py','--project',project,'--line','E01','--json')
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['line'],'E01')
        self.assertIn('media/episodes/E01/prompts',report['created'])
    def test_concurrent_steps_all_land(self):
        # Two sessions marking steps at once both land: every writer holds the
        # project lock and replaces the open task in one step.
        project,_=self.init()
        count=6
        steps=[value for n in range(1,count+1) for value in ('--step',f'step {n}')]
        self.assertEqual(self.command('work_ledger.py','--project',project,'begin','--goal','Synthetic concurrency check',*steps).returncode,0)
        processes=[subprocess.Popen([sys.executable,str(ROOT/'scripts'/'work_ledger.py'),'--project',str(project),'step',str(n)],cwd=self.root,env=os.environ.copy(),stdout=subprocess.PIPE,stderr=subprocess.PIPE) for n in range(1,count+1)]
        for process in processes:
            _,error=process.communicate(timeout=120);self.assertEqual(process.returncode,0,error)
        task=json.loads((project/'work/current.json').read_text(encoding='utf-8'))
        self.assertTrue(all(step['done_at'] for step in task['steps']),task)
        events=[json.loads(line)['event'] for line in (project/'work/ledger.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(events.count('step'),count)
        result=self.command('validate_project.py',project);self.assertEqual(result.returncode,0,result.stdout)
    def test_truncated_open_task_is_explained(self):
        project,_=self.init()
        self.assertEqual(self.command('work_ledger.py','--project',project,'begin','--goal','g','--step','s').returncode,0)
        current=project/'work/current.json';current.write_bytes(current.read_bytes()[:20])
        result=self.command('work_ledger.py','--project',project,'show')
        self.assertNotEqual(result.returncode,0);self.assertIn('work/current.json is not a readable task',result.stderr);self.assertNotIn('Traceback',result.stderr)
    def test_drafted_contract_finalization(self):
        data=json.loads((ROOT/'examples/protocol-exchange/fixtures/character-identity-contract.json').read_text());data['contract_id']='CIC-authored';source=self.save('identity-draft.json',data);out=self.root/'identity.json'
        result=self.command('state_protocol.py','finalize',source,'--out',out);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(state_protocol.validate_artifact(json.loads(out.read_text()))['ok'])
    def test_character_state_requires_project_declaration(self):
        event=state_protocol.load_jsonl(ROOT/'examples/mixed-viewpoint-workshop/source/events.jsonl')[0]
        self.assertRaisesRegex(ValueError,'missing character state schema',state_protocol.resolve_world,base_state={'characters':{}},events=[event],processes=[],timeline_id='main',story_order=10,story_time='now',snapshot_id='world',scene_context_id='scene')
    def test_dry_dispatch_from_project_service_file(self):
        service=self.save('service-profiles.json',{'services':{'runware':{'transport':'runware','endpoint':{'base_url':'https://example.invalid/not-called'},'operations':{'imageInference':{}},'observed_at':'synthetic-test'}}})
        spec=self.save('submission.json',{'submission_id':'preview-fixture','kind':'asset','target':'xai-grok-imagine-2','service':'runware','operation':'imageInference','text':'A painted empty room, warm light across a wooden table.','inputs':[],'parameters':{'width':1024,'height':1024,'numberResults':1},'obligations':{}})
        import execution_contract as c
        import production_test_support as support
        value=json.loads(spec.read_text())
        value.update(target='fixture',model='synthetic-target')
        service_record=json.loads(service.read_text())['services']['runware']
        _,_,profiles=support.model_inputs(self.root,value,service_record)
        spec.write_bytes(c.encoded(value))
        out=io.StringIO()
        with patch.object(transport_runware,'send',side_effect=AssertionError('network send')),patch.object(transport_runware,'upload_bytes',side_effect=AssertionError('network upload')),redirect_stdout(out):
            result=dispatch.main([str(spec),'--service-profiles',str(service),'--profiles',str(profiles)])
        self.assertEqual(result,0,out.getvalue());self.assertIn('Preview recorded.',out.getvalue());self.assertFalse((self.root/'runs').exists())

    def test_example_inventory_is_relative_to_its_root(self):
        import runpy
        builder=runpy.run_path(str(ROOT/'examples/mixed-viewpoint-workshop/build_example.py'))
        for parent in ['source', 'workspace']:
            example=self.root/parent/'example'
            (example/'generated').mkdir(parents=True)
            (example/'source').mkdir()
            (example/'generated/result.json').write_bytes(b'{"state":"draft"}\n')
            (example/'source/input.json').write_bytes(b'{}\n')
            (example/'README.md').write_text('Fixture documentation')
            self.assertEqual(builder['file_map'](example),{'generated/result.json':b'{"state":"draft"}\n'})

    def test_service_configuration_does_not_execute_an_endpoint(self):
        import service_profile
        p=self.save('services.json',{'services':{'fixture':{'endpoint':{'base_url':'https://example.invalid/not-called'},'observed_at':'synthetic fixture'}}})
        before=p.read_bytes()
        with patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network call')):
            service,path=service_profile.load_service('fixture',str(p))
        self.assertEqual(path,p)
        self.assertEqual(service['endpoint']['base_url'],'https://example.invalid/not-called')
        self.assertEqual(p.read_bytes(),before)
    def test_resource_config_location_does_not_approve_its_content(self):
        document=self.save('supplied/resource.json',{'categories':[],'note':'synthetic unapproved input'})
        settings=self.save('supplied/config.json',{'resources':{'prompt-vocabulary':'resource.json'}})
        os.environ['SERIES_RESOURCES']=str(settings)
        before=document.read_bytes()
        self.assertEqual(resource_files.resolve_resource('prompt-vocabulary'),document)
        self.assertEqual(document.read_bytes(),before)
    def test_target_schema_ref_cannot_fetch_url(self):
        import target_protocol
        with patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network retrieval')):
            with self.assertRaisesRegex(ValueError,r'HTTP\(S\) schema references are not retrieved'):
                target_protocol._resolve_ref('https://example.invalid/not-read.json')

    def run_documented_project_start(self, project_name):
        import shlex
        documentation = (ROOT / "scripts/README.md").read_text(encoding="utf-8")
        block = documentation.split("<!-- executable-example: project-start -->", 1)[1].split("<!-- end-example: project-start -->", 1)[0]
        block = block.split("```text", 1)[1].split("```", 1)[0]
        commands = [shlex.split(line) for line in block.splitlines() if line.strip()]
        self.assertEqual(len(commands), 7)
        for command in commands:
            self.assertEqual(command[0], "python")
            script = Path(command[1]).name
            args = [project_name if value == "PROJECT" else value for value in command[2:]]
            completed = self.command(script, *args)
            self.assertEqual(completed.returncode, 0, str(command) + "\n" + completed.stdout + completed.stderr)
        project = self.root / project_name
        self.assertTrue((project / "narrative/narrative.json").is_file())
        self.assertTrue((project / "narrative/world/locations/station.md").is_file())
        data = json.loads((project / "narrative/narrative.json").read_text(encoding="utf-8"))
        self.assertEqual(data["series_id"], "SERIES-01")
        return project

    def test_documented_start_commands_create_and_inspect_project(self):
        self.run_documented_project_start("series-example")

    def test_documented_commands_with_spaces_and_unicode_then_move(self):
        project = self.run_documented_project_start("작품 초안")
        moved = self.root / "另一个位置" / "series"
        moved.parent.mkdir()
        project.rename(moved)
        result = self.command("validate_project.py", moved)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProjectWorkflow));sys.stderr.write(stream.getvalue());print(json.dumps({'ok':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}));raise SystemExit(not result.wasSuccessful())
