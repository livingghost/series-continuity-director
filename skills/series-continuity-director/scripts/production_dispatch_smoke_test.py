#!/usr/bin/env python3
"""No-network tests of real claim, output recording and no-resend recovery.

The generic dispatch tests use the synthetic transport, whose request shape no
real service defines. Only RunwareTransportTests exercise transport_runware.
Every network test talks only to local servers on 127.0.0.1.
"""
import copy
import http.server
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
import execution_contract as c
import production_workflow as w
import production_dispatch as d
import production_test_support as support
import run_gallery
import service_profile
import transport_contract
import transport_runware
import transport_synthetic as transport
import work_ledger

# A synthetic deadline for fixtures whose network calls are replaced.
FIXTURE_DEADLINE_SECONDS = 30


class SimulatedCrash(BaseException):
    """Stops a run the way a killed process does, past every ordinary handler."""


def returned(text=b'Actual returned text.'):
    return patch.object(d, 'open_result', side_effect=lambda url, seconds: io.BytesIO(text))


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        task=work_ledger.begin(self.root,'Synthetic bounded dispatch',['deliver'])
        self.spec={'submission_id':'fixture','kind':'asset','service':'synthetic-service','target':'fixture',
            'model':'synthetic-target',
            'operation':'generate','text':'Hold the declared condition.','inputs':[],
            'parameters':{'count':1},'output':{'dir':'outputs','basename':'fixture','suffix':'.txt'}}
        self.service={'transport':'synthetic','operations':{'generate':{}},
            'endpoint':{'base_url':'http://127.0.0.1:9/not-contacted'},'http_timeout_seconds':FIXTURE_DEADLINE_SECONDS}
        self.save_service()
        (self.root/'spec.json').write_bytes(c.encoded(self.spec));(self.root/'prompt.txt').write_text(self.spec['text'])
        self.task={'task_id':task['task_id'],'route':'development','features':[],
            'sources':[{'id':n,'path':n+'.json','role':'configuration','disposition':'applied','locator':'whole','reason':'Synthetic bound.'} for n in ['spec','services']],
            'delivery':{'path':'prompt.txt','transport':'authored-rendition','translation_notes':'Test only.'},
            'criteria':[{'id':'hold','text':'The condition is recorded.','strength':'hard','evidence':'text'}],
            'sequence_plan':None}
        self.task['sources'].append({'id': 'target-profile', 'path': 'profiles/fixture.json',
            'role': 'configuration', 'disposition': 'applied', 'locator': 'whole', 'reason': 'Synthetic target interface.'})
        self.task['direction']=support.direction(self.task,self.spec['text']);self.run=None;self.reserved_outputs=1
        self.answer={'outputs':[{'job':'one','location':'https://example.invalid/result'}]}
        self.report={'status':'admitted','unmeasured':['Synthetic provider; no actual quality test.']}
    def save_service(self):
        (self.root/'services.json').write_bytes(c.encoded({'services':{self.spec['service']:self.service}}))
    def prepare(self):
        from reading_fixtures import task_reading
        self.profile, self.offering, self.profiles = support.model_inputs(self.root, self.spec, self.service)
        task_reading(self.root,self.task)
        (self.root/'spec.json').write_bytes(c.encoded(self.spec));(self.root/'task.json').write_bytes(c.encoded(self.task))
        self.run=w.prepare(self.root,'task.json')['run'];w.handoff(self.root,self.run,'mock provider','dispatcher')
        self.auth=support.grant(w,self.root,self.run,operations=('submit','select'),outputs=self.reserved_outputs,stop_conditions=['Synthetic reviewed condition'])
    def invoke(self,transport_module=transport,**changes):
        if self.run is None:self.prepare()
        options=dict(authorization=self.auth,actor='synthetic selector',outputs=self.reserved_outputs,cost='0',currency='none',poll=False)
        decision_change = changes.pop('decision_change', None)
        options.update(changes)
        consumer = w.assert_current(self.root, self.run)[2]
        built, report, _ = d.render(self.root, self.spec, self.service, self.offering, transport, self.profiles, consumer=consumer)
        decision = support.model_decision(w, self.root, self.run, self.auth, built['rendered'])
        if decision_change is not None:
            decision_change(decision)
        return d.execute(self.root,self.run,self.root/'spec.json',self.spec,self.root/'services.json',self.service,self.offering,report,transport_module,'not-a-credential',
                         profiles=self.profiles, decision=decision, rendered=built['rendered'], **options)
    def guards(self):
        return patch.object(transport,'send',return_value=self.answer),patch.object(transport,'upload_bytes',side_effect=AssertionError('not expected')),returned()
    def events(self):
        return [r['event'] for r in w.load_run(self.root,self.run)[3]]
    def claim(self):
        return w.find(w.load_run(self.root,self.run)[3],'dispatch-claim')['sha256']
    def recorded(self,stage):
        rows=[r for r in w.load_run(self.root,self.run)[3] if r['event']=='dispatch-trace' and r['data']['stage']==stage]
        return c.decode(c.object_read(w.run_dir(self.root,self.run),rows[-1]['data']['files'][0]['sha256']))
    def test_actual_record_and_review_selection_completion(self):
        a,b,z=self.guards()
        with a as send,b,z:self.invoke();self.assertEqual(send.call_count,1)
        _,p,_,rows=w.load_run(self.root,self.run);candidate=w.find(rows,'candidate');r=support.observed(w.draft_review(self.root,self.run,candidate['sha256']))
        (self.root/'review.json').write_bytes(c.encoded(r));w.review(self.root,self.run,'review.json')
        sel=w.draft_selection(self.root,self.run,candidate['sha256']);sel.update(selector='synthetic selector',authorization=self.auth,reason='Synthetic fixture only.')
        (self.root/'select.json').write_bytes(c.encoded(sel));w.select(self.root,self.run,'select.json');w.complete(self.root,self.run)
        self.assertEqual(w.status(self.root,self.run)['next'],'done')
    def test_no_authority_no_send(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):self.invoke(authorization='a'*64)
        self.assertEqual(send.call_count,0)
    def test_count_mismatch_no_send(self):
        self.spec['parameters']['count']=2;a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):self.invoke()
        self.assertEqual(send.call_count,0)
    def test_options_cannot_replace_the_prepared_text(self):
        self.spec['options']={'prompt':'A different instruction.'};a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):self.invoke()
        self.assertEqual(send.call_count,0)
    def test_unknown_result_is_not_resent(self):
        with patch.object(transport,'send',side_effect=OSError('Synthetic lost connection')) as send:
            with self.assertRaises(OSError):self.invoke()
            with self.assertRaises(ValueError):self.invoke()
            self.assertEqual(send.call_count,1)
        self.assertIn('recover',w.status(self.root,self.run)['next'])
    def test_recorded_unknown_outcome_blocks_resubmission(self):
        self.answer={'unknown':{'outcome':'indeterminate','reason':'Synthetic server error.','status':503}}
        with patch.object(transport,'send',return_value=self.answer) as send,returned() as download:
            with self.assertRaisesRegex(ValueError,'outcome is unknown'):self.invoke()
            with self.assertRaises(ValueError):self.invoke()
            with self.assertRaisesRegex(ValueError,'outcome is unknown'):
                d.obtain(self.root,self.run,self.claim(),transport,'',poll=True,poll_seconds=0,poll_limit=1)
        self.assertEqual(send.call_count,1);self.assertEqual(download.call_count,0)
        self.assertEqual(self.recorded('transport-outcome.json')['outcome'],'indeterminate')
        self.assertEqual(self.recorded('answer.json'),self.answer)
        status=w.status(self.root,self.run)
        self.assertIn('recover',status['next']);self.assertFalse(status['execution']['new_submission_allowed_by_this_report'])
    def test_recovery_only_downloads_known_result(self):
        with patch.object(transport,'send',return_value=self.answer),patch.object(d,'open_result',side_effect=OSError('Synthetic download failure')):
            with self.assertRaises(OSError):self.invoke()
        with patch.object(transport,'send',side_effect=AssertionError('resend')),patch.object(transport,'upload_bytes',side_effect=AssertionError('reupload')),returned():
            result=d.obtain(self.root,self.run,self.claim(),transport,'',poll=False,poll_seconds=0,poll_limit=0)
        self.assertEqual(result['event'],'dispatch-results');self.assertEqual(w.status(self.root,self.run)['next'],'review')
        self.assertEqual(self.recorded('download-001.json')['size'],len(b'Actual returned text.'))
    def test_modified_trace_stops_recovery(self):
        a,b,z=self.guards()
        with a,b,z:self.invoke()
        (w.run_dir(self.root,self.run)/'dispatch'/self.claim()/'answer.json').write_text('{}')
        with self.assertRaises(ValueError):d.obtain(self.root,self.run,self.claim(),transport,'',poll=False,poll_seconds=0,poll_limit=0)
    def test_more_results_than_authorized_not_registered(self):
        self.answer['outputs'].append({'job':'two','location':'https://example.invalid/other'});a,b,z=self.guards()
        with a,b,z,self.assertRaises(ValueError):self.invoke()
        self.assertFalse(any(r['event']=='candidate' for r in w.load_run(self.root,self.run)[3]))
    def test_source_mutation_before_send_is_detected(self):
        self.prepare();(self.root/'prompt.txt').write_text('Different premise');a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):self.invoke()
        self.assertEqual(send.call_count,0)
    def test_polling_existing_task_records_actual_output(self):
        self.answer={'outputs':[{'job':'one'}]}
        a,b,z=self.guards()
        with a as send,b,z,patch.object(transport,'poll',return_value={'outputs':[{'job':'one','location':'https://example.invalid/result'}]}) as poll:
            self.invoke(poll=True,poll_limit=1,poll_seconds=0);self.assertEqual(send.call_count,1);self.assertEqual(poll.call_count,1)

    def test_one_pending_task_can_return_multiple_artifacts(self):
        self.spec['parameters']['count']=2;self.reserved_outputs=2
        self.answer={'outputs':[{'job':'one'}]}
        returned_data={'outputs':[{'job':'one','location':'https://example.invalid/first'},
                          {'job':'one','location':'https://example.invalid/second'}]}
        a,b,z=self.guards()
        with a as send,b,z,patch.object(transport,'poll',return_value=returned_data):
            result=self.invoke(poll=True,poll_limit=1,poll_seconds=0)
            self.assertEqual(send.call_count,1);self.assertEqual(len(result['data']['files']),2)
        urls={self.recorded(f'download-{i:03d}.json')['result']['url'] for i in (1,2)}
        self.assertEqual(urls,{e['location'] for e in returned_data['outputs']})

    def test_poll_merge_retains_previously_completed_artifacts(self):
        self.spec['parameters']['count']=2;self.reserved_outputs=2
        self.answer={'outputs':[{'job':'one','location':'https://example.invalid/first'},{'job':'two'}]}
        returned_data={'outputs':[{'job':'two','location':'https://example.invalid/second'}]}
        a,b,z=self.guards()
        with a,b,z,patch.object(transport,'poll',return_value=returned_data):
            result=self.invoke(poll=True,poll_limit=1,poll_seconds=0)
        self.assertEqual(len(result['data']['files']),2)

    def test_interruption_after_a_recorded_poll_keeps_completed_outputs(self):
        # The run stops right after poll-000001 is recorded, before any later step.
        self.spec['parameters']['count']=2;self.reserved_outputs=2
        self.answer={'outputs':[{'job':'one','location':'https://example.invalid/first'},{'job':'two'}]}
        polled={'outputs':[{'job':'two','location':'https://example.invalid/second'}]}
        original=d.append_trace
        def interrupted(root,run,claim,name,value):
            record=original(root,run,claim,name,value)
            if name.startswith('poll-'):raise SimulatedCrash(name)
            return record
        a,b,z=self.guards()
        with a,b,z,patch.object(transport,'poll',return_value=polled),patch.object(d,'append_trace',side_effect=interrupted):
            with self.assertRaises(SimulatedCrash):self.invoke(poll=True,poll_limit=1,poll_seconds=0)
        with patch.object(transport,'send',side_effect=AssertionError('resend')),patch.object(transport,'poll',side_effect=AssertionError('poll')),returned():
            result=d.obtain(self.root,self.run,self.claim(),transport,'',poll=False,poll_seconds=0,poll_limit=0)
        self.assertEqual(len(result['data']['files']),2)
        urls={self.recorded(f'download-{i:03d}.json')['result']['url'] for i in (1,2)}
        self.assertEqual(urls,{'https://example.invalid/first','https://example.invalid/second'})

    def test_unrecorded_poll_file_does_not_block_recovery(self):
        self.answer={'outputs':[{'job':'one'}]}
        a,b,z=self.guards()
        with a,b,z,self.assertRaisesRegex(ValueError,'not every reserved output'):self.invoke()
        journal=w.run_dir(self.root,self.run)/'dispatch'/self.claim()
        (journal/'poll-000001.json').write_bytes(c.encoded({'outputs':[{'job':'one'}],'note':'written without its record'}))
        with patch.object(transport,'poll',return_value={'outputs':[{'job':'one','location':'https://example.invalid/result'}]}),returned():
            result=d.obtain(self.root,self.run,self.claim(),transport,'',poll=True,poll_seconds=0,poll_limit=1)
        self.assertEqual(result['event'],'dispatch-results');self.assertTrue((journal/'poll-000002.json').is_file())

    def test_result_url_needs_https(self):
        self.answer={'outputs':[{'job':'one','location':'http://example.invalid/result'}]}
        a,b,z=self.guards()
        with a,b,z as download,self.assertRaisesRegex(ValueError,'https'):self.invoke()
        self.assertEqual(download.call_count,0)

    def assert_refused_before_claim(self,pattern,transport_module=transport):
        with patch.object(transport,'send',side_effect=AssertionError('network send')) as send:
            with self.assertRaisesRegex(ValueError,pattern):self.invoke(transport_module)
        self.assertEqual(send.call_count,0)
        self.assertNotIn('dispatch-claim',self.events());self.assertNotIn('reservation',self.events())

    def test_missing_deadline_refused_before_claim(self):
        self.service.pop('http_timeout_seconds')
        with patch.dict(os.environ):
            os.environ.pop(service_profile.TIMEOUT_VARIABLE,None)
            self.assert_refused_before_claim('http_timeout_seconds.*PRODUCTION_HTTP_TIMEOUT_SECONDS')

    def test_plain_http_endpoint_refused_before_claim(self):
        self.service['endpoint']['base_url']='http://example.invalid/not-contacted'
        self.assert_refused_before_claim('https')

    def test_transport_missing_a_function_refused_before_claim(self):
        partial=types.SimpleNamespace(**{name:getattr(transport,name) for name in dir(transport) if not name.startswith('__')})
        partial.__file__=transport.__file__;partial.__name__='transport_partial';del partial.observation_outcome
        self.assert_refused_before_claim('observation_outcome',partial)

    def test_successful_dispatch_can_be_observed_without_network(self):
        import model_observation
        a,b,z=self.guards()
        with a,b,z:self.invoke()
        with patch.object(transport,'send',side_effect=AssertionError('send during observation')), \
             patch.object(transport,'upload_bytes',side_effect=AssertionError('upload during observation')):
            result=model_observation.publish(self.root,self.run,self.root/'observations',relative_prefix='observations')
        self.assertEqual(result['outcome'],'completed')
        self.assertTrue((self.root/result['profile']['path']).is_file())

    def test_review_of_other_request_never_sends(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):
            self.invoke(decision_change=lambda value: value['rendition_review'].update(request_sha256='f'*64))
        self.assertEqual(send.call_count,0)

    def test_missing_stop_assessment_never_sends(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):
            self.invoke(decision_change=lambda value: value.update(stop_assessments=[]))
        self.assertEqual(send.call_count,0)

    def test_unsatisfied_review_never_sends(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):
            self.invoke(decision_change=lambda value: value['rendition_review'].update(conclusion='unmeasured'))
        self.assertEqual(send.call_count,0)

    def test_missing_principal_approval_without_delegation_never_sends(self):
        a,b,z=self.guards()
        with a as send,b,z,self.assertRaises(ValueError):
            self.invoke(decision_change=lambda value: value.update(principal_approval=None))
        self.assertEqual(send.call_count,0)

    def test_trace_binds_reserved_request(self):
        a,b,z=self.guards()
        with a,b,z:self.invoke()
        rows=w.load_run(self.root,self.run)[3];claim=w.find(rows,'dispatch-claim')
        reservation=w.find(rows,'reservation',claim['data']['reservation'])
        self.assertEqual(claim['data']['manifest']['request_sha256'],reservation['data']['request_sha256'])
        self.assertEqual(claim['data']['manifest']['request_sha256'],claim['data']['manifest']['rendered']['request_sha256'])

    def test_end_to_end_through_a_loopback_service(self):
        # The synthetic transport's own exchange, a real download and the generic records, unpatched.
        def service_answer(server, handler):
            if handler.command == 'GET':
                return 200, {'Content-Type': 'text/plain'}, b'Synthetic returned text.'
            sent = json.loads(server.requests[-1]['body'])
            return 200, {'Content-Type': 'application/json'}, json.dumps({'outputs': [
                {'job': sent['envelope']['request_id'], 'location': server.url + '/result', 'seed': 7}]}).encode()
        server = LocalServer(self, service_answer)
        self.service['endpoint']['base_url'] = server.url + '/generate'
        self.save_service()
        result = self.invoke()
        self.assertEqual(result['event'], 'dispatch-results')
        sent = json.loads(server.requests[0]['body'])
        self.assertEqual((sent['prompt'], sent['engine'], sent['action'], sent['count']),
                         (self.spec['text'], 'synthetic-target', 'generate', 1))
        self.assertEqual(server.requests[0]['key'], 'not-a-credential')
        self.assertEqual((server.requests[1]['method'], server.requests[1]['key']), ('GET', None))
        entry = run_gallery.index(self.root)['entries'][0]
        self.assertEqual((entry['text'], entry['model'], entry['operation'], entry['outcome']),
                         (self.spec['text'], 'synthetic-target', 'generate', 'accepted'))
        self.assertEqual(entry['settings'], {'count': 1})
        self.assertEqual(list(entry['management']), ['envelope.request_id'])
        self.assertEqual(entry['results'][0]['seed'], 7)
        self.assertIsNone(run_gallery.stale(self.root))


class RequestShapeTests(unittest.TestCase):
    def test_sent_fields_must_match_the_declared_shape(self):
        spec = {'service': 'synthetic-service', 'model': 'synthetic-target', 'operation': 'generate',
                'text': 'Synthetic text.', 'negative_text': 'Synthetic exclusion.', 'parameters': {'count': 1}}
        offering = {'model_identifier': 'synthetic-target', 'request_shape': dict(transport.REQUEST_SHAPE)}
        layout = transport.compile_request(spec, offering, {'operations': {'generate': {}}})['layout']
        d.require_declared_shape(offering, layout)
        for key, value in (('text_key', 'positivePrompt'), ('model_key', 'model'), ('negative_text_key', 'negative')):
            changed = dict(offering, request_shape=dict(transport.REQUEST_SHAPE, **{key: value}))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'request_shape declares'):
                d.require_declared_shape(changed, layout)
        with self.assertRaisesRegex(ValueError, 'no request_shape'):
            d.require_declared_shape({}, layout)


class LocalServer:
    """One HTTP server on 127.0.0.1 that answers with a supplied function."""

    def __init__(self, test, answer):
        self.requests = []
        self.release = threading.Event()
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def handle_one(self):
                length = int(self.headers.get('Content-Length') or 0)
                owner.requests.append({'method': self.command, 'path': self.path,
                    'authorization': self.headers.get('Authorization'), 'key': self.headers.get('X-Synthetic-Key'),
                    'body': self.rfile.read(length)})
                status, headers, body = answer(owner, self)
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST = handle_one

        class Server(http.server.ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass  # A client that stopped waiting is part of the fixture.

        self.server = Server(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        test.addCleanup(self.close)

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()


def json_answer(value, status=200):
    return lambda server, handler: (status, {'Content-Type': 'application/json'}, json.dumps(value).encode())


class RunwareTransportTests(unittest.TestCase):
    """The Runware transport against local servers; no request leaves 127.0.0.1."""

    def setUp(self):
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(service_profile.TIMEOUT_VARIABLE, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def service(self, server, **changes):
        value = {'transport': 'runware', 'endpoint': {'base_url': server.url + '/v1'}, 'operations': {'imageInference': {}},
                 'http_timeout_seconds': FIXTURE_DEADLINE_SECONDS}
        value.update(changes)
        return value

    def test_redirect_never_carries_the_credential(self):
        other = LocalServer(self, json_answer({'data': [{'taskUUID': 'moved', 'imageURL': 'https://example.invalid/x'}]}))
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                endpoint = LocalServer(self, lambda s, h, status=status: (status, {'Location': other.url + '/collect'}, b''))
                answer = transport_runware.send({'taskType': 'imageInference'}, self.service(endpoint), 'synthetic-secret')
                self.assertEqual(answer['exchange']['outcome'], transport_contract.UNKNOWN)
                self.assertEqual(answer['exchange']['status'], status)
                self.assertEqual(answer['exchange']['location'], other.url + '/collect')
                self.assertEqual(transport_runware.observation_outcome(answer), 'indeterminate')
                self.assertEqual(endpoint.requests[0]['authorization'], 'Bearer synthetic-secret')
        self.assertEqual(other.requests, [])

    def test_upload_and_poll_refuse_redirects(self):
        other = LocalServer(self, json_answer({'data': [{'imageUUID': 'moved'}]}))
        endpoint = LocalServer(self, lambda s, h: (302, {'Location': other.url + '/collect'}, b''))
        with self.assertRaisesRegex(ValueError, 'outcome is unknown'):
            transport_runware.upload_bytes(b'\x89PNG\r\n\x1a\n', 'image/png', self.service(endpoint), 'synthetic-secret')
        self.assertEqual(transport_runware.poll(['one'], self.service(endpoint), 'synthetic-secret')['exchange']['status'], 302)
        self.assertEqual(other.requests, [])

    def test_upload_returns_the_service_identifier(self):
        endpoint = LocalServer(self, json_answer({'data': [{'imageUUID': 'u1'}]}))
        self.assertEqual(transport_runware.upload_bytes(b'bytes', 'image/png', self.service(endpoint), 'k'), 'u1')
        with self.assertRaisesRegex(ValueError, 'media table'):
            transport_runware.upload_bytes(b'bytes', 'application/octet-stream', self.service(endpoint), 'k')
        self.assertEqual(len(endpoint.requests), 1)

    def test_server_error_is_unknown_not_refused(self):
        endpoint = LocalServer(self, json_answer({'errors': [{'code': 'busy'}]}, status=503))
        answer = transport_runware.send({}, self.service(endpoint), 'k')
        self.assertEqual(transport_runware.rejections(answer), [])
        self.assertEqual(transport_runware.observation_outcome(answer), 'indeterminate')
        self.assertEqual(answer['exchange']['body']['json'], {'errors': [{'code': 'busy'}]})

    def test_client_error_is_a_refusal(self):
        endpoint = LocalServer(self, json_answer({'errors': [{'code': 'invalidModel'}]}, status=400))
        answer = transport_runware.send({}, self.service(endpoint), 'k')
        self.assertEqual(transport_runware.rejections(answer), [{'code': 'invalidModel'}])
        self.assertEqual(transport_runware.observation_outcome(answer), 'rejected')

    def test_non_json_success_body_is_recorded(self):
        endpoint = LocalServer(self, lambda s, h: (200, {'Content-Type': 'text/html'}, 'Gateway page \u00e9'.encode()))
        answer = transport_runware.send({}, self.service(endpoint), 'k')
        self.assertEqual(answer['exchange']['outcome'], transport_contract.UNKNOWN)
        self.assertEqual(answer['exchange']['body']['text'], 'Gateway page \u00e9')
        self.assertEqual(answer['exchange']['body']['content_type'], 'text/html')
        c.encoded(answer)

    def test_timeout_is_unknown(self):
        def stall(server, handler):
            server.release.wait()
            return 200, {}, b'{}'
        endpoint = LocalServer(self, stall)
        # A short test watchdog, not a product deadline.
        answer = transport_runware.send({}, self.service(endpoint, http_timeout_seconds=0.5), 'k')
        self.assertEqual(answer['exchange']['outcome'], transport_contract.UNKNOWN)
        self.assertEqual(answer['exchange']['timeout_seconds'], 0.5)
        self.assertEqual(answer['exchange']['timeout_source'], 'http_timeout_seconds')

    def test_connection_failure_is_unknown(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        service = {'endpoint': {'base_url': f'http://127.0.0.1:{port}/v1'}, 'http_timeout_seconds': FIXTURE_DEADLINE_SECONDS}
        answer = transport_runware.send({}, service, 'k')
        self.assertEqual(answer['exchange']['outcome'], transport_contract.UNKNOWN)
        self.assertEqual(transport_runware.observation_outcome(answer), 'indeterminate')

    def test_endpoint_needs_https_or_loopback(self):
        for url in ('http://example.invalid/v1', 'ftp://example.invalid/v1', 'https:///v1', ''):
            with self.subTest(url=url), self.assertRaises(ValueError):
                transport_runware.send({}, {'endpoint': {'base_url': url}, 'http_timeout_seconds': 1}, 'k')
        for url in ('https://example.invalid/v1', 'http://127.0.0.1:9/v1', 'http://[::1]:9/v1', 'http://localhost:9/v1'):
            self.assertEqual(service_profile.endpoint_url({'endpoint': {'base_url': url}}), url)

    def test_deadline_comes_from_explicit_configuration(self):
        endpoint = LocalServer(self, json_answer({'data': []}))
        with self.assertRaisesRegex(ValueError, 'http_timeout_seconds.*PRODUCTION_HTTP_TIMEOUT_SECONDS'):
            transport_runware.send({}, {'endpoint': {'base_url': endpoint.url}}, 'k')
        self.assertEqual(endpoint.requests, [])
        self.assertEqual(service_profile.http_timeout({'http_timeout_seconds': 12}), (12, 'http_timeout_seconds'))
        os.environ[service_profile.TIMEOUT_VARIABLE] = '7.5'
        self.assertEqual(service_profile.http_timeout({'http_timeout_seconds': 12}), (7.5, service_profile.TIMEOUT_VARIABLE))
        for value in (0, -1, True, 'ten', float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                os.environ.pop(service_profile.TIMEOUT_VARIABLE, None)
                service_profile.http_timeout({'http_timeout_seconds': value})

    def test_result_download_streams_to_disk(self):
        body = bytes(range(256)) * 300
        server = LocalServer(self, lambda s, h: (200, {'Content-Type': 'image/png'}, body))
        target = self.root / 'outputs' / 'result.png'
        sha256, size = d.download(server.url + '/result', target, FIXTURE_DEADLINE_SECONDS)
        self.assertEqual((sha256, size), (c.digest(body), len(body)))
        self.assertEqual(target.read_bytes(), body)
        self.assertEqual(d.download(server.url + '/result', target, FIXTURE_DEADLINE_SECONDS), (sha256, size))
        target.write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            d.download(server.url + '/result', target, FIXTURE_DEADLINE_SECONDS)
        self.assertEqual(sorted(p.name for p in target.parent.iterdir()), ['result.png'])

    def test_result_redirect_keeps_to_https(self):
        final = LocalServer(self, lambda s, h: (200, {}, b'redirected result'))
        local = LocalServer(self, lambda s, h: (302, {'Location': final.url + '/file'}, b''))
        self.assertEqual(d.download(local.url + '/r', self.root / 'a.bin', FIXTURE_DEADLINE_SECONDS)[1], len(b'redirected result'))
        downgrade = LocalServer(self, lambda s, h: (302, {'Location': 'http://example.invalid/file'}, b''))
        with self.assertRaisesRegex(ValueError, 'https'):
            d.download(downgrade.url + '/r', self.root / 'b.bin', FIXTURE_DEADLINE_SECONDS)
        with self.assertRaisesRegex(ValueError, 'loopback'):
            service_profile.require_network_url(final.url, 'redirected result URL', allow_loopback=False)
        self.assertFalse((self.root / 'b.bin').exists())

    def test_transport_is_named_by_the_service_record(self):
        self.assertIs(transport_contract.load({'transport': 'runware'}), transport_runware)
        self.assertIs(transport_contract.load({'transport': 'synthetic'}), transport)
        for record in ({}, {'transport': ''}, {'transport': '../runware'}, {'transport': 'os.path'},
                       {'transport': 'Runware'}, {'transport': 3}, 'runware'):
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, 'must name its transport'):
                transport_contract.load(record)
        with self.assertRaisesRegex(ValueError, 'no transport module'):
            transport_contract.load({'transport': 'absent_service'})
        with self.assertRaisesRegex(ValueError, 'compile_request.*observation_outcome'):
            transport_contract.check(types.SimpleNamespace(__name__='empty'))


if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
