#!/usr/bin/env python3
"""Draft changes through declared compiler fields with synthetic recorded evidence."""
import copy
from pathlib import Path
import unittest
import request_contract as rc
import request_contract_smoke_test as fixture
from input_evidence import InputEvidence
import production_variation as variation

class FieldTests(fixture.RequestContractTests):
    def test_variation_seed_changes_exact_tuple(self):
        before=self.seal();changed,diff=variation.apply_changes(before,{'seed':4},self.root,InputEvidence(self.root))
        self.assertEqual(changed['request']['seed'],4);self.assertNotEqual(before['profile'],changed['profile'])
        self.assertEqual(before['request']['seed'],3)
    def test_variation_content_is_not_a_parameter_measurement(self):
        before=self.seal();changed,_=variation.apply_changes(before,{'prompt':'Other explicit content.'},self.root,InputEvidence(self.root))
        self.assertEqual(before['profile'],changed['profile']);self.assertNotEqual(before['request_sha256'],changed['request_sha256'])
    def test_variation_cannot_mutate_model_as_content(self):
        with self.assertRaises(ValueError):variation.apply_changes(self.seal(),{'model':'other'},self.root,InputEvidence(self.root))
    def test_variation_cannot_invent_a_field(self):
        with self.assertRaises(ValueError):variation.apply_changes(self.seal(),{'unknown-field':1},self.root,InputEvidence(self.root))
    def test_variation_rejects_empty_change(self):
        with self.assertRaises(ValueError):variation.apply_changes(self.seal(),{'seed':3},self.root,InputEvidence(self.root))

import production_dispatch_smoke_test as dispatch_fixture
import execution_contract as c
import production_workflow as workflow
from unittest.mock import patch

class RecordedVariationTests(dispatch_fixture.DispatchTests):
    def make_variation(self):
        self.spec['parameters']['seed']=3
        a,b,z=self.guards()
        with a,b,z:self.invoke()
        candidate=workflow.find(workflow.load_run(self.root,self.run)[3],'candidate')
        (self.root/'changes.json').write_bytes(c.encoded({'candidate':candidate['sha256'],'changes':{'seed':4},'reason':'Synthetic seed comparison.'}))
        return candidate
    def test_draft_uses_actual_run_and_preserves_its_receipts(self):
        self.make_variation();before=copy.deepcopy(workflow.load_run(self.root,self.run)[3])
        result=variation.draft(self.root,self.run,'changes.json','variation')
        self.assertEqual(result['state'],'draft');self.assertEqual(workflow.load_run(self.root,self.run)[3],before)
        self.assertTrue(result['profile_changed']);self.assertFalse(result['external_effect'])
        spec=c.load(self.root/'variation/submission-source.json');self.assertEqual(spec['parameters']['seed'],4)
        self.assertNotIn('request_validation',spec)
        original=c.load(self.root/'spec.json');self.assertEqual(original['parameters']['seed'],3)
    def test_draft_existing_destination_does_not_change_receipts(self):
        self.make_variation();variation.draft(self.root,self.run,'changes.json','variation')
        with self.assertRaises(FileExistsError):variation.draft(self.root,self.run,'changes.json','variation')
    def test_draft_does_not_accept_a_candidate_from_another_run(self):
        self.make_variation();data=c.load(self.root/'changes.json');data['candidate']='f'*64
        (self.root/'changes.json').write_bytes(c.encoded(data))
        with self.assertRaises(ValueError):variation.draft(self.root,self.run,'changes.json','variation')

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
