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
    def test_fresh_medium_workspaces(self):
        for medium in ['screen','comics','prose','mixed']:
            with self.subTest(medium=medium):
                project=self.root/medium;result=self.command('init_project.py','--out',project,'--series-id','FIXTURE-SERIES','--title','Fixture series','--medium',medium);self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads((project/'narrative/narrative.json').read_text())['medium'],medium)
                result=self.command('validate_project.py',project);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_project_persona_creation(self):
        project=self.root/'project';self.assertEqual(self.command('init_project.py','--out',project,'--series-id','FIXTURE-SERIES','--title','Fixture').returncode,0)
        result=self.command('narrative_entity.py','--series',project,'add','persona','second','--character','C02');self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        text=(project/'narrative/personas/second.md').read_text(encoding='utf-8');self.assertGreater(len(text.splitlines()),1000)
    def test_drafted_contract_finalization(self):
        data=json.loads((ROOT/'examples/protocol-exchange/fixtures/character-identity-contract.json').read_text());data['contract_id']='CIC-authored';source=self.save('identity-draft.json',data);out=self.root/'identity.json'
        result=self.command('state_protocol.py','finalize',source,'--out',out);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(state_protocol.validate_artifact(json.loads(out.read_text()))['ok'])
    def test_character_state_requires_project_declaration(self):
        event=state_protocol.load_jsonl(ROOT/'examples/mixed-viewpoint-workshop/source/events.jsonl')[0]
        self.assertRaisesRegex(ValueError,'missing character state schema',state_protocol.resolve_world,base_state={'characters':{}},events=[event],processes=[],timeline_id='main',story_order=10,story_time='now',snapshot_id='world',scene_context_id='scene')
    def test_dry_dispatch_from_project_service_file(self):
        service=self.save('service-profiles.json',{'services':{'runware':{'endpoint':{'base_url':'https://example.invalid/not-called'},'operations':{'imageInference':{}},'observed_at':'synthetic-test'}}})
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
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProjectWorkflow));sys.stderr.write(stream.getvalue());print(json.dumps({'ok':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}));raise SystemExit(not result.wasSuccessful())
