#!/usr/bin/env python3
"""Synthetic public dispatcher previews without network or authority consumption."""
import contextlib
import copy
import io
from pathlib import Path
import unittest
from unittest.mock import patch
import dispatch
import execution_contract as c
import production_workflow as workflow
import production_dispatch_smoke_test as fixture

class PreviewTests(unittest.TestCase):
    setUp=fixture.DispatchTests.setUp
    prepare=fixture.DispatchTests.prepare
    def call(self, extra=()):
        if self.run is None:self.prepare()
        before=copy.deepcopy(workflow.load_run(self.root,self.run)[3])
        with patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network')),contextlib.redirect_stdout(io.StringIO()):
            result=dispatch.main([str(self.root/'spec.json'),'--root',str(self.root),
                '--profiles',str(self.profiles),'--service-profiles',str(self.root/'services.json'),
                '--production-run',self.run,'--authorization',self.auth,'--actor','synthetic selector',
                '--preview-out',str(self.root/'preview.json'),'--decision-out',str(self.root/'decision.json'),*extra])
        self.assertEqual(workflow.load_run(self.root,self.run)[3],before)
        return result
    def test_public_cli_derives_review_and_stops(self):
        self.assertEqual(self.call(),0)
        view=c.load(self.root/'preview.json');decision=c.load(self.root/'decision.json')
        self.assertEqual(view['request_contract']['request_sha256'],decision['rendition_review']['request_sha256'])
        self.assertIsNone(decision['rendition_review']['conclusion'])
        self.assertEqual(decision['stop_assessments'][0]['condition'],'Synthetic reviewed condition')
        self.assertIsNone(decision['stop_assessments'][0]['clear'])
        self.assertIsNone(decision['principal_approval'])
    def test_existing_preview_is_preserved(self):
        self.prepare();(self.root/'preview.json').write_text('Existing preview.')
        with self.assertRaises(FileExistsError):self.call()
        self.assertFalse((self.root/'decision.json').exists())
    def test_target_model_selection_is_exact(self):
        self.prepare();value=dict(self.spec,model='wrong-model')
        with self.assertRaises(ValueError):dispatch.offering_for(value,self.profiles)

if __name__=='__main__':unittest.main(verbosity=2)
