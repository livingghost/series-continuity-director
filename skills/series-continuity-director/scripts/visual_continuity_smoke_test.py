#!/usr/bin/env python3
"""Check explicit synthetic subjects without inferring them from prose."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
import execution_contract as c
import visual_continuity as v

class SubjectTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.root=Path(t.name)
        (self.root/'basis.txt').write_text('Synthetic single-subject exploration. Not a user approval.\n')
        self.basis=v.file_ref(self.root,'basis.txt',locator='whole')
    def subject(self,continuity='one-off',character=None):
        return {'continuity':continuity,'character_id':character,'identity_refs':[]}
    def visual(self,subjects,purpose='image'):
        return {'purpose':purpose,'basis':self.basis,'subjects':subjects,'shot_camera':None,'shot_request':None,'reference_activation':None}
    def check(self,value):
        v.validate_content(value,kind='asset')
    def test_empty_non_sheet(self): self.check(self.visual({}))
    def test_single_undecided(self): self.check(self.visual({'subject-a':self.subject('undecided')}))
    def test_multiple_undecided(self):
        with self.assertRaises(ValueError): self.check(self.visual({'subject-a':self.subject('undecided'),'subject-b':self.subject()}))
    def test_missing_continuity(self):
        s=self.subject();del s['continuity']
        with self.assertRaises(ValueError):self.check(self.visual({'subject-a':s}))
    def test_recurring_needs_character(self):
        with self.assertRaises(ValueError):self.check(self.visual({'subject-a':self.subject('recurring')}))
    def test_multiple_recurring_needs_identity(self):
        with self.assertRaises(ValueError):self.check(self.visual({'subject-a':self.subject('recurring','CHAR-A'),'subject-b':self.subject()}))
    def test_one_off_pair(self):self.check(self.visual({'subject-a':self.subject(),'subject-b':self.subject()}))
    def test_sheet_is_one_subject(self):
        with self.assertRaises(ValueError):self.check(self.visual({'subject-a':self.subject(),'subject-b':self.subject()},'sheet-panel'))
    def test_empty_sheet(self):
        with self.assertRaises(ValueError):self.check(self.visual({},'sheet-panel'))
    def test_unknown_continuity(self):
        with self.assertRaises(ValueError):self.check(self.visual({'subject-a':self.subject('unknown')}))
    def test_identity_array_required(self):
        s=self.subject();s['identity_refs']='identity'
        with self.assertRaises(ValueError):self.check(self.visual({'subject-a':s}))
    def test_source_hash_is_exact(self):
        value=self.visual({'subject-a':self.subject()});(self.root/'basis.txt').write_text('Changed synthetic source.')
        with self.assertRaises(ValueError):v.check_file(self.root,value['basis'],basis=True)
    def test_locator_does_not_infer_subjects(self):
        value=self.visual({'subject-a':self.subject('undecided')});value['basis']['locator']='A multilingual document about two figures; literal selector only.'
        self.check(value)
    def test_arbitrary_display_words_do_not_change_set(self):
        value=self.visual({'two figures and an overview':self.subject('undecided')})
        self.check(value)
    def test_page_and_passage_carry_no_camera(self):
        value=self.visual({'subject-a':self.subject()})
        for kind in ('page','passage'): v.validate_content(value,kind=kind)
        value['shot_camera']=v.file_ref(self.root,'basis.txt')
        with self.assertRaisesRegex(ValueError,"kind 'page' carries no shot_camera"): v.validate_content(value,kind='page')
    def test_undeclared_kind_is_named(self):
        with self.assertRaisesRegex(ValueError,'shot, page, passage, asset'): v.validate_content(self.visual({}),kind='frame')
    def test_missing_block_field_is_named(self):
        value=self.visual({});del value['basis']
        with self.assertRaisesRegex(ValueError,'missing basis'): self.check(value)

class CommandTests(unittest.TestCase):
    """The build and verify commands on a synthetic asset submission."""
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.root=Path(t.name)
        (self.root/'basis.txt').write_text('Synthetic single-subject exploration. Not a user approval.\n')
        self.path=self.root/'asset.submission.json'
        self.path.write_text(json.dumps({'kind':'asset','target':'xai-grok-imagine-2','text':'A synthetic plate.'}))
    def run_command(self,*arguments):
        out=io.StringIO()
        with contextlib.redirect_stdout(out): code=v.main(list(arguments))
        return code,json.loads(out.getvalue())
    def build(self,*extra):
        return self.run_command('build',str(self.path),'--root',str(self.root),*extra)
    def test_build_write_and_verify(self):
        code,report=self.build('--basis','basis.txt','--basis-locator','whole','--subject','subject-a','one-off','--write')
        self.assertEqual(code,0,report)
        self.assertEqual(report['visual_continuity']['purpose'],'image')
        saved=json.loads(self.path.read_text())
        self.assertEqual(saved['visual_continuity_sha256'],c.content_id(saved['visual_continuity']))
        self.assertEqual(self.run_command('verify',str(self.path),'--root',str(self.root))[0],0)
        (self.root/'basis.txt').write_text('Changed synthetic source.\n')
        code,report=self.run_command('verify',str(self.path),'--root',str(self.root))
        self.assertEqual(code,1); self.assertIn('source bytes changed',report['error'])
    def test_build_without_write_leaves_the_file(self):
        before=self.path.read_bytes()
        code,_=self.build('--basis','basis.txt','--basis-locator','whole')
        self.assertEqual(code,0); self.assertEqual(self.path.read_bytes(),before)
    def test_choices_are_explicit(self):
        for arguments,fragment in [((),'state the choices'),
                                   (('--subject','subject-a','one-off'),'--basis PATH and --basis-locator TEXT'),
                                   (('--basis','basis.txt','--basis-locator','whole','--subject','subject-a','sometimes'),'continuity must be one of'),
                                   (('--purpose','nonvisual','--basis','basis.txt'),'a nonvisual block carries no basis'),
                                   (('--choices','choices.json','--basis','basis.txt'),'not both')]:
            code,report=self.build(*arguments)
            self.assertEqual(code,1,arguments); self.assertIn(fragment,report['error'])
    def test_verify_names_a_missing_block(self):
        code,report=self.run_command('verify',str(self.path),'--root',str(self.root))
        self.assertEqual(code,1); self.assertIn('carries no visual_continuity',report['error'])

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main()
