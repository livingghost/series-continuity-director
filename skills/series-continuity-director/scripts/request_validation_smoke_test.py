"""Synthetic schema provenance, exact probes and declared delegation cases."""
import copy
import unittest
from pathlib import Path
import execution_contract as c
import request_contract as rc
import request_validation as rv
import request_scope as scope
from input_evidence import InputEvidence
import request_contract_smoke_test as fixture

class ValidationTests(unittest.TestCase):
    def setUp(self):
        fixture.RequestContractTests.setUp(self);self.rendered=fixture.RequestContractTests.seal(self)
        self.reader=InputEvidence(self.root)
        self.schema={'type':'object','properties':{'count':{'type':'integer','minimum':1,'maximum':2},'seed':{'type':'integer'}},'required':['count']}
        self.response=self.save('response.json',{'schema':self.schema})
        self.acquisition={'artifact_type':'schema-acquisition','target':self.target,'source':{'kind':'document','identifier':'Synthetic interface declaration','locator':'schema member'},
            'acquired_at':'2026-01-01T00:00:00Z','response':self.response,'status':{'document_status':'schema-provided'}}
        self.evidence=self.save('acquisition.json',self.acquisition)
        self.contract={'artifact_type':'model-schema-contract','target':self.target,'schema':self.schema,'schema_sha256':c.content_id(self.schema),'response_pointer':'/schema','local_overlay':None}
        self.contract_ref=self.save('contract.json',self.contract)
        self.choices={'mode':'target-schema','contract':'contract.json','evidence':'acquisition.json','execution_policy':None}
    def tearDown(self):self.temp.cleanup()
    def save(self,name,value):return fixture.RequestContractTests.save(self,name,value)
    def build(self):return rv.build_record(self.choices,self.reader,expected_target=self.target,execution=self.execution,rendered=self.rendered)
    def probe(self):
        self.acquisition['status']={'document_status':'schema-not-provided'};self.evidence=self.save('acquisition.json',self.acquisition)
        plan={'artifact_type':'model-probe-plan','target':self.target,'reason':'Synthetic one-output trial.',
            'basis':self.evidence,'reference_schemas':[],'fixed_request_profile':self.rendered['sealed'],'unknowns':[]}
        self.save('probe.json',plan);self.choices.update(mode='bounded-probe',contract='probe.json');return plan
    def test_01_target_document_matches_its_exact_bytes(self):self.assertEqual(self.build()['unmeasured'],[])
    def test_02_other_target_source_refused(self):
        self.acquisition['target']=dict(self.target,model_identifier='other');self.save('acquisition.json',self.acquisition)
        with self.assertRaises(ValueError):self.build()
    def test_03_schema_modified_from_original_refused(self):
        self.contract['schema']={'type':'string'};self.contract['schema_sha256']=c.content_id(self.contract['schema']);self.save('contract.json',self.contract)
        with self.assertRaises(ValueError):self.build()
    def test_04_response_modified_without_new_hash_refused(self):
        self.save('response.json',{'schema':{'type':'string'}})
        with self.assertRaises(ValueError):self.build()
    def test_05_known_count_constraint_enforced(self):
        self.request['count']=3;self.rendered=fixture.RequestContractTests.seal(self)
        with self.assertRaises(ValueError):self.build()
    def test_06_unimplemented_keyword_is_visible(self):
        self.schema['unevaluatedProperties']=False;self.response=self.save('response.json',{'schema':self.schema});self.acquisition['response']=self.response
        self.save('acquisition.json',self.acquisition);self.contract['schema_sha256']=c.content_id(self.schema);self.save('contract.json',self.contract)
        self.assertTrue(any('unevaluatedProperties' in x['scope'] for x in self.build()['unmeasured']))
    def test_07_unmeasured_cannot_be_deleted(self):
        self.probe();record=self.build();record['unmeasured']=[]
        with self.assertRaises(ValueError):rv.require(record,self.reader,rendered=self.rendered)
    def test_08_probe_is_one_exact_output(self):
        self.probe();record=self.build();self.assertEqual(record['mode'],'bounded-probe')
    def test_09_probe_different_seed_refused(self):
        self.probe();self.request['seed']=9;self.rendered=fixture.RequestContractTests.seal(self)
        with self.assertRaises(ValueError):self.build()
    def test_10_probe_multiple_outputs_refused(self):
        self.request['count']=2;self.rendered=fixture.RequestContractTests.seal(self);self.probe()
        with self.assertRaises(ValueError):self.build()
    def test_11_probe_does_not_require_a_sibling_schema(self):
        plan=self.probe();self.assertEqual(plan['reference_schemas'],[]);self.build()
    def test_12_probe_keeps_current_known_schema_constraints(self):
        self.probe();record=self.build()
        with self.assertRaises(ValueError):rv.require(record,self.reader,rendered=self.rendered,known_schema={'schema':{'type':'object','properties':{'count':{'const':2}}},'overlay':None})
    def test_13_error_word_is_not_http_status(self):
        self.acquisition['source']['kind']='http';self.acquisition['status']={'http_status':None,'transport_outcome':'connection-failed'}
        self.acquisition['source']['identifier']='Synthetic response containing 404';self.save('acquisition.json',self.acquisition)
        with self.assertRaises(ValueError):self.build()
    def test_14_only_successful_http_schema_is_own_schema(self):
        self.acquisition['source']['kind']='http';self.acquisition['status']={'http_status':404,'transport_outcome':'completed'};self.save('acquisition.json',self.acquisition)
        with self.assertRaises(ValueError):self.build()
    def test_15_external_schema_reference_is_not_fetched(self):
        with self.assertRaises(ValueError):rv._schema_shape({'$ref':'https://invalid.example/schema'})
    def test_16_reference_keeps_its_own_target(self):
        other=dict(self.target,model_identifier='source-model');self.acquisition['target']=other;self.evidence=self.save('acquisition.json',self.acquisition)
        basis=self.save('relationship.json',{'declaration':'Synthetic related source, not target support.'})
        value={'artifact_type':'model-schema-reference','target':self.target,'source_target':other,'acquisition':self.evidence,'schema':self.schema,
            'response_pointer':'/schema','relationship':{**basis,'locator':'declaration'}}
        ref=self.save('reference.json',value);self.assertEqual(rv.reference_schema(ref,self.reader)['source_target'],other)
    def test_17_reference_does_not_become_target_schema(self):
        self.contract['artifact_type']='model-schema-reference';self.save('contract.json',self.contract)
        with self.assertRaises(ValueError):self.build()
    def test_18_overlay_cannot_remove_model_constraints(self):
        overlay={'fields':{'model':{'type':'string'}}}
        with self.assertRaises(ValueError):rv.check_schema(self.request,{'schema':self.schema,'overlay':overlay},envelope_fields=[['task_id']])
    def test_19_overlay_preserves_original_declared_envelope_constraint(self):
        found={'schema':{'type':'object','properties':{'task_id':{'const':'required'}}},'overlay':{'fields':{'task_id':{'type':'string'}}}}
        with self.assertRaises(ValueError):rv.check_schema(self.request,found,envelope_fields=[['task_id']])
    def test_20_historical_contract_uses_saved_sources(self):
        record=self.build();saved=copy.deepcopy(self.reader.snapshots)
        for path in self.root.iterdir():path.unlink()
        rv.require(record,InputEvidence(None,snapshots=saved,live=False),rendered=self.rendered)
    def test_21_record_for_other_execution_refused(self):
        record=self.build()
        with self.assertRaises(ValueError):rv.require(record,self.reader,execution=dict(self.execution,transport_sha256='c'*64))
    def test_22_boolean_probe_count_is_not_one_output(self):
        plan=self.probe();plan['fixed_request_profile']['output_count']=True;self.save('probe.json',plan)
        with self.assertRaises(ValueError):self.build()

class DelegationTests(unittest.TestCase):
    def setUp(self):
        fixture.RequestContractTests.setUp(self);self.rendered=fixture.RequestContractTests.seal(self)
        self.basis={'path':'plan.txt','sha256':'a'*64,'locator':'selected case'}
        self.case=scope.build_case(self.rendered,identifier='comparison',productions=['series'],variations={'seed':{'kind':'values','values':[3,4]}},review_criteria=[])
        self.plan={'plan':self.basis,'cases':[self.case]}
    def tearDown(self):self.temp.cleanup()
    def assess(self,**kwargs):
        args={'case_id':'comparison','rendered':self.rendered,'production':'series','mode':'bounded-probe','modes':['bounded-probe']};args.update(kwargs)
        return scope.assess(self.plan,**args)
    def test_01_scope_is_ready_with_explicit_values(self):self.assertEqual(self.assess()['state'],'delegated-ready')
    def test_02_new_allowed_seed_has_new_request_hash(self):
        initial=self.rendered['request_sha256'];self.request['seed']=4;self.rendered=fixture.RequestContractTests.seal(self)
        self.assertNotEqual(initial,self.rendered['request_sha256']);self.assertEqual(self.assess()['state'],'delegated-ready')
    def test_03_outside_seed_needs_principal(self):
        self.request['seed']=5;self.rendered=fixture.RequestContractTests.seal(self);self.assertEqual(self.assess()['state'],'principal-decision-required')
    def test_04_budget_does_not_authorize_probe_mode(self):self.assertEqual(self.assess(modes=['target-schema'])['state'],'principal-decision-required')
    def test_05_subject_change_is_not_a_seed_variation(self):
        self.rendered=rc.seal(self.request,self.layout,self.media,self.target,self.execution,[],[],{'subjects':{'new':'person'},'output_kind':'image'})
        self.assertEqual(self.assess()['state'],'principal-decision-required')
    def test_06_other_series_needs_principal(self):self.assertEqual(self.assess(production='other')['state'],'principal-decision-required')
    def test_07_other_target_needs_principal(self):
        self.request['model']='different';self.target['model_identifier']='different';self.rendered=fixture.RequestContractTests.seal(self)
        self.assertEqual(self.assess()['state'],'principal-decision-required')
    def test_08_unassessed_criterion_is_not_cleared(self):
        self.case['review_criteria']=['intent'];self.assertEqual(self.assess()['state'],'actor-assessment-required')
    def test_09_supplied_criterion_coverage(self):
        self.case['review_criteria']=['intent'];row={'criterion':'intent','request_sha256':self.rendered['request_sha256'],'conclusion':'satisfied','reason':'Synthetic assessor declaration.'}
        self.assertEqual(self.assess(assessments=[row])['state'],'delegated-ready')
    def test_10_other_request_assessment_refused(self):
        self.case['review_criteria']=['intent'];row={'criterion':'intent','request_sha256':'0'*64,'conclusion':'satisfied','reason':'Synthetic assessor declaration.'}
        with self.assertRaises(ValueError):self.assess(assessments=[row])
    def test_11_model_cannot_be_authored_content(self):
        self.case['variations']['fixed:["model"]']={'kind':'authored-content','source':self.basis,'criterion':'intent'}
        self.case['fixed'].pop('fixed:["model"]');self.case['review_criteria']=['intent']
        self.assertEqual(self.assess()['state'],'principal-decision-required')
    def test_12_unselected_cases_are_not_merged(self):
        with self.assertRaises(ValueError):self.assess(case_id=None)
    def test_13_integer_range_excludes_boolean(self):
        self.case['variations']['seed']={'kind':'range','type':'integer','minimum':0,'maximum':8}
        self.request['seed']=True;self.rendered=fixture.RequestContractTests.seal(self)
        self.assertEqual(self.assess()['state'],'principal-decision-required')
    def test_14_single_exact_consent_is_distinct_from_delegation(self):
        result=scope.assess(None,case_id=None,rendered=self.rendered,production='series',mode='bounded-probe',modes=['bounded-probe'])
        self.assertEqual(result['state'],'principal-decision-required')
    def test_15_explicit_exact_approval_covers_only_its_request(self):
        approval={'request_sha256':self.rendered['request_sha256'],'principal':'Synthetic principal','evidence':self.basis}
        result=scope.assess(None,case_id=None,rendered=self.rendered,production='series',mode='bounded-probe',modes=['bounded-probe'],principal_approval=approval)
        self.assertEqual(result['state'],'delegated-ready')
    def test_16_non_submit_has_no_submission_mode(self):
        with self.assertRaises(ValueError):scope.validate(None,submit=False,modes=['target-schema'])
    def test_17_default_fields_are_fixed_by_drafting(self):self.assertIn('fixed:["operation"]',self.case['fixed'])
    def test_18_unknown_new_request_field_requires_new_scope(self):
        self.request['new_control']='on';self.rendered=fixture.RequestContractTests.seal(self)
        self.assertEqual(self.assess()['state'],'principal-decision-required')
    def test_19_authored_content_needs_its_declared_criterion(self):
        self.case['fixed'].pop('prompt');self.case['variations']['prompt']={'kind':'authored-content','source':self.basis,'criterion':'intent'}
        with self.assertRaises(ValueError):self.assess()
    def test_20_scope_draft_keeps_every_other_field_fixed(self):
        self.assertEqual(set(self.case['fixed'])|set(self.case['variations']),set(self.rendered['fields']))
    def test_21_original_source_pointer_does_not_infer_scope(self):
        self.plan['plan']['locator']='Permission to do anything';self.request['count']=2;self.rendered=fixture.RequestContractTests.seal(self)
        self.assertEqual(self.assess()['state'],'principal-decision-required')
    def test_22_same_request_receipt_ignores_ephemeral_task_id(self):
        first=rc.receipt_projection(self.rendered);self.request['task_id']='new-task';self.rendered=fixture.RequestContractTests.seal(self)
        self.assertEqual(first,rc.receipt_projection(self.rendered))

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main()
