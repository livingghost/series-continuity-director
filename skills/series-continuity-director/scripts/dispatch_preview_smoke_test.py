#!/usr/bin/env python3
"""Synthetic public dispatcher previews without network or authority consumption."""
import contextlib
import copy
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import dispatch
import execution_contract as c
import production_dispatch
import production_workflow as workflow
import production_dispatch_smoke_test as fixture
import production_test_support as support
import service_profile
import transport_synthetic

class PreviewTests(unittest.TestCase):
    setUp=fixture.DispatchTests.setUp
    prepare=fixture.DispatchTests.prepare
    save_service=fixture.DispatchTests.save_service
    def main(self, arguments):
        out,err=io.StringIO(),io.StringIO()
        with patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network')), \
             patch.object(transport_synthetic,'send',side_effect=AssertionError('network send')), \
             patch.object(production_dispatch,'open_result',side_effect=AssertionError('network download')), \
             contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            result=dispatch.main(arguments)
        return result,out.getvalue(),err.getvalue()
    def call(self, extra=()):
        if self.run is None:self.prepare()
        before=copy.deepcopy(workflow.load_run(self.root,self.run)[3])
        result=self.main([str(self.root/'spec.json'),'--root',str(self.root),
                '--profiles',str(self.profiles),'--service-profiles',str(self.root/'services.json'),
                '--production-run',self.run,'--authorization',self.auth,'--actor','synthetic selector',
                '--preview-out',str(self.root/'preview.json'),'--decision-out',str(self.root/'decision.json'),*extra])
        self.assertEqual(workflow.load_run(self.root,self.run)[3],before)
        return result
    def test_public_cli_derives_review_and_stops(self):
        result,out,_=self.call()
        self.assertEqual(result,0)
        self.assertIn('network deadline 30 s per network wait, from http_timeout_seconds',out)
        view=c.load(self.root/'preview.json');decision=c.load(self.root/'decision.json')
        self.assertEqual(view['request_contract']['request_sha256'],decision['rendition_review']['request_sha256'])
        self.assertIsNone(decision['rendition_review']['conclusion'])
        self.assertEqual(decision['stop_assessments'][0]['condition'],'Synthetic reviewed condition')
        self.assertIsNone(decision['stop_assessments'][0]['clear'])
        self.assertIsNone(decision['principal_approval'])
    def test_existing_preview_is_preserved(self):
        self.prepare();(self.root/'preview.json').write_text('Existing preview.')
        result,_,err=self.call()
        self.assertEqual(result,1);self.assertIn('preview destination already exists',err)
        self.assertFalse((self.root/'decision.json').exists())
    def test_target_model_selection_is_exact(self):
        self.prepare();value=dict(self.spec,model='wrong-model')
        with self.assertRaises(ValueError) as caught:dispatch.offering_for(value,self.profiles)
        self.assertIn(repr(self.spec['model']),str(caught.exception))
    def test_missing_dispatch_fields_are_named_with_their_values(self):
        self.prepare()
        value={k:v for k,v in self.spec.items() if k not in ('model','operation','request_validation','input_snapshots')}
        with self.assertRaises(ValueError) as caught:dispatch.dispatch_fields(value,self.service,self.profiles)
        message=str(caught.exception)
        self.assertIn(repr(self.spec['model']),message);self.assertIn(repr(self.spec['operation']),message)
        self.assertIn('production_workflow.py build-inputs',message)
    def test_missing_service_data_names_the_dispatch_flag(self):
        with patch.dict(os.environ):
            os.environ.pop('SERVICE_PROFILES_PATH',None);os.environ.pop('SERIES_RESOURCES',None)
            with self.assertRaises(ValueError) as caught:
                service_profile.load_service('synthetic',None,flag='--service-profiles')
        self.assertIn('pass --service-profiles FILE',str(caught.exception))
    def test_expected_failure_prints_one_error(self):
        result,out,err=self.main([str(self.root/'absent-spec.json')])
        self.assertEqual(result,1);self.assertEqual(out,'')
        self.assertTrue(err.startswith('dispatch: '));self.assertNotIn('Traceback',err);self.assertEqual(len(err.splitlines()),1)
    def test_send_without_deadline_stops_before_claim(self):
        self.service.pop('http_timeout_seconds')
        self.save_service()
        self.prepare()
        consumer=workflow.assert_current(self.root,self.run)[2]
        built,_,_=production_dispatch.render(self.root,self.spec,self.service,self.offering,transport_synthetic,self.profiles,consumer=consumer)
        (self.root/'decision.json').write_bytes(c.encoded(support.model_decision(workflow,self.root,self.run,self.auth,built['rendered'])))
        with patch.dict(os.environ):
            os.environ.pop(service_profile.TIMEOUT_VARIABLE,None)
            result,_,err=self.main([str(self.root/'spec.json'),'--root',str(self.root),
                '--profiles',str(self.profiles),'--service-profiles',str(self.root/'services.json'),
                '--production-run',self.run,'--authorization',self.auth,'--actor','synthetic selector',
                '--request-decision',str(self.root/'decision.json'),'--outputs','1','--cost-bound','0',
                '--currency','none','--send'])
        self.assertEqual(result,1)
        self.assertIn('http_timeout_seconds',err);self.assertIn('PRODUCTION_HTTP_TIMEOUT_SECONDS',err)
        events=[row['event'] for row in workflow.load_run(self.root,self.run)[3]]
        self.assertNotIn('dispatch-claim',events);self.assertNotIn('reservation',events)

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
