#!/usr/bin/env python3
"""Synthetic schema acquisition and atomic publication tests; no provider is called."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import execution_contract as c
from input_evidence import InputEvidence
import schema_observation as observation
import request_validation as rv

class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.target={'service':'synthetic','model_identifier':'synthetic:one','operation':'generate'}
        self.schema={'type':'object','properties':{'seed':{'type':'integer'}}}
        self.raw=b'{ "schema" : '+json.dumps(self.schema).encode()+b', "notes": "synthetic source" }\n'
        (self.root/'response.json').write_bytes(self.raw)
        self.acquisition={'artifact_type':'schema-acquisition','target':self.target,
            'source':{'kind':'document','identifier':'Synthetic source','locator':'schema'},
            'acquired_at':'2000-01-01T00:00:00Z','response':{'path':'response.json','sha256':c.digest(self.raw)},
            'status':{'document_status':'schema-provided'}}
        self.save()
    def save(self): (self.root/'acquisition.json').write_bytes(c.encoded(self.acquisition))
    def assemble(self,**changes):
        args=dict(target=self.target,acquisition='acquisition.json',pointer='/schema',prefix='evidence',kind='schema')
        args.update(changes);return observation.assemble(self.root,**args)
    def test_original_response_bytes_are_preserved(self):
        files,manifest=self.assemble();self.assertEqual(files['response.json'],self.raw)
        observation.publish(self.root,'evidence',files)
        rv.schema_contract(c.decode(files['contract.json']),c.decode(files['acquisition.json']),InputEvidence(self.root),self.target)
    def test_source_target_cannot_be_relabelled(self):
        self.acquisition['target']=dict(self.target,model_identifier='other');self.save()
        with self.assertRaises(ValueError):self.assemble()
        self.assertFalse((self.root/'evidence').exists())
    def test_reference_keeps_source_identity(self):
        self.acquisition['target']=dict(self.target,model_identifier='source-only');self.save()
        (self.root/'relationship.txt').write_text('Synthetic author-selected reference; not a target observation.')
        ref={'path':'relationship.txt','sha256':c.digest(c.read(self.root/'relationship.txt')),'locator':'whole'}
        files,manifest=self.assemble(kind='reference',relationship=ref)
        self.assertEqual(c.decode(files['reference.json'])['source_target'],self.acquisition['target'])
        self.assertNotIn('contract.json',files)
    def test_no_relationship_is_inferred_from_names(self):
        with self.assertRaises(ValueError):self.assemble(kind='reference')
    def test_overlay_never_changes_acquired_schema(self):
        (self.root/'basis.txt').write_text('Synthetic adapter envelope.')
        value={'artifact_type':'request-envelope-overlay','target':self.target,'fields':{'taskType':{'type':'string'}},
            'basis':{'path':'basis.txt','sha256':c.digest(c.read(self.root/'basis.txt')),'locator':'whole'}}
        (self.root/'overlay.json').write_bytes(c.encoded(value))
        files,_=self.assemble(overlay='overlay.json')
        self.assertEqual(c.decode(files['contract.json'])['schema'],self.schema)
        self.assertEqual(files['response.json'],self.raw);self.assertIn('overlay.json',files)
    def test_http_failure_is_not_schema_observation(self):
        self.acquisition.update(source={'kind':'http','identifier':'Synthetic endpoint','locator':'body'},
            status={'http_status':404,'transport_outcome':'completed'});self.save()
        with self.assertRaises(ValueError):self.assemble()
    def test_changed_response_witness_refused(self):
        (self.root/'response.json').write_text('{}')
        with self.assertRaises(ValueError):self.assemble()
    def test_existing_destination_is_preserved(self):
        files,_=self.assemble();observation.publish(self.root,'evidence',files)
        original=(self.root/'evidence/manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):observation.publish(self.root,'evidence',files)
        self.assertEqual((self.root/'evidence/manifest.json').read_bytes(),original)
    def test_no_network_in_schema_assembly(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network')):self.assemble()
    def test_pointer_selects_structure_not_words(self):
        with self.assertRaises(ValueError):self.assemble(pointer='/synthetic')

class ProfileImportTests(AcquisitionTests):
    def setUp(self):
        super().setUp()
        import production_test_support as support
        spec={'target':'fixture','service':self.target['service'],'model':self.target['model_identifier'],'operation':self.target['operation']}
        service={'operations':{'generate':{}}}
        profile,_,_=support.model_inputs(self.root,spec,service)
        (self.root/'profile.json').write_bytes(c.encoded(profile))
        self.args=SimpleNamespace(command='schema',root=self.root,profile='profile.json',service=self.target['service'],
            model=self.target['model_identifier'],operation='generate',out_dir='published',
            acquisition='acquisition.json',pointer='/schema',overlay=None)
    def test_schema_command_keeps_public_profile_unchanged(self):
        import observe_schema as cli
        before=c.read(self.root/'profile.json');result=cli.publish(self.args)
        self.assertTrue(result['ok']);self.assertEqual(c.read(self.root/'profile.json'),before)
        catalog=c.load(self.root/result['catalog']['path'])
        self.assertEqual(catalog['target'],self.target)
        self.assertEqual(c.load(self.root/catalog['schema_snapshot']['path'])['schema'],self.schema)
    def test_schema_error_does_not_publish_partial_catalog(self):
        import observe_schema as cli
        self.acquisition['target']=dict(self.target,model_identifier='other');self.save()
        with self.assertRaises(ValueError):cli.publish(self.args)
        self.assertFalse((self.root/'published').exists())

if __name__=='__main__':unittest.main(verbosity=2)
