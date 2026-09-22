#!/usr/bin/env python3
"""Validate synthetic public artifacts, state scope and actual delivery."""
import copy
import tempfile
import unittest
from pathlib import Path
import execution_contract as c
from protocol_contract import finalize_artifact
from activation_fixtures import fixture
from reference_activation_gate import gate,settle
from reference_carriers import delivered

class ActivationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.package,self.activation,self.inputs=fixture(self.root)
    def verdict(self):return gate(self.activation,self.root)
    def test_admitted(self):self.assertEqual(self.verdict()['status'],'admitted')
    def test_public_self_hash(self):
        self.package['reference_preamble']='changed';(self.root/'package.json').write_bytes(c.encoded(self.package))
        self.assertEqual(self.verdict()['status'],'refused')
    def test_added_reference(self):
        self.activation['uses'].append({'reference':'absent','settles':['identity']})
        self.assertIn('REFERENCE_NOT_IN_PACKAGE',[x['code'] for x in self.verdict()['errors']])
    def test_missing_reference(self):
        self.activation['uses'].pop()
        self.assertIn('REFERENCE_DROPPED_SILENTLY',[x['code'] for x in self.verdict()['errors']])
    def test_declined_is_explicit(self):
        self.activation['uses'][1]={'reference':'SYN-BIND-2','declined':True,'reason':'Synthetic exclusion.'}
        self.assertEqual(self.verdict()['status'],'admitted')
    def test_scope(self):
        self.activation['uses'][0]['settles']=['lighting']
        self.assertIn('OUTSIDE_AUTHORITY',[x['code'] for x in self.verdict()['errors']])
    def test_story_range(self):
        self.activation['story_point']=101
        self.assertIn('AFTER_STORY_RANGE',[x['code'] for x in self.verdict()['errors']])
    def test_missing_binding_is_unmeasured(self):
        self.activation['state_bindings'].pop('SYN-BIND-1')
        self.assertTrue(any(x['field']=='state_binding' for x in self.verdict()['unmeasured']))
    def test_exact_binding_source(self):
        ref=self.activation['state_bindings']['SYN-BIND-1'];p=self.root/ref['path'];state=c.load(p)
        state['source']['reference_id']='different';state=finalize_artifact(state);p.write_bytes(c.encoded(state));ref['sha256']=c.digest(p.read_bytes())
        self.assertEqual(self.verdict()['status'],'refused')
    def test_delivered_order(self):
        result=delivered(self.package,root=self.root,package_dir=self.root,inputs=self.inputs)
        self.assertEqual([x['input_index'] for x in result],[0,1])
        with self.assertRaises(ValueError):delivered(self.package,root=self.root,package_dir=self.root,inputs=self.inputs[::-1])
    def test_missing_attachment(self):
        with self.assertRaises(ValueError):delivered(self.package,root=self.root,package_dir=self.root,inputs=self.inputs[:1])
    def test_board_regions(self):
        package,_,inputs=fixture(self.root,board=True)
        result=delivered(package,root=self.root,package_dir=self.root,inputs=inputs)
        self.assertEqual([x['input_index'] for x in result],[0,0])
        package['single_board']['panels'][0]['box']['x']=8
        package['single_board']['panels'][1]['box']['x']=0
        with self.assertRaises(ValueError):delivered(package,root=self.root,package_dir=self.root,inputs=inputs)
    def test_byte_mismatch(self):
        with (self.root/'image-1.png').open('ab') as stream:stream.write(b'changed')
        with self.assertRaises(ValueError):delivered(self.package,root=self.root,package_dir=self.root,inputs=self.inputs)
    def test_no_character_name_guess(self):
        self.activation['activation_id']='two characters and an overview'
        self.assertEqual(self.verdict()['status'],'admitted')

if __name__=='__main__':unittest.main()
