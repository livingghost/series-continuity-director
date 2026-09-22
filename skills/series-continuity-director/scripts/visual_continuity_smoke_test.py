#!/usr/bin/env python3
"""Check explicit synthetic subjects without inferring them from prose."""
import copy
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

if __name__=='__main__':unittest.main()
