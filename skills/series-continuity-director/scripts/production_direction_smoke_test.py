#!/usr/bin/env python3
"""Current-form purpose, authority and actual-evidence regression tests."""
from pathlib import Path
import copy
import io
import tempfile
import unittest
from PIL import Image
import execution_contract as c
import production_direction as direction
import production_authority as authority
import media_evidence as media
import production_test_support as support

class DirectionTests(unittest.TestCase):
    def setUp(self):
        self.task={'sources':[{'id':'persona','disposition':'applied','path':'persona.md'}],
            'criteria':[{'id':'reading','strength':'hard','text':'Declared effect','evidence':'image'}]}
        self.value=support.direction(self.task,'Keep the existing bearing; do not add a conventional smile.')
    def check(self):direction.validate(self.value,self.task['sources'],self.task['criteria'])
    def test_full_source_is_referenced_not_replaced_by_label(self):self.check();self.assertEqual(self.value['basis'][0]['source'],'persona')
    def test_no_cast_source_is_required(self):self.task['sources']=[];self.value['basis']=[];self.check()
    def test_settled_choice_has_one_realization(self):self.check()
    def test_material_branch_requires_comparison(self):
        self.value['decisions'][0]['compare']=True
        with self.assertRaises(ValueError):self.check()
    def test_material_branch_accepts_distinct_choices(self):
        d=self.value['decisions'][0];d['compare']=True;d['options'].append({'id':'contrast','realization':'Use a deliberate contrast.','consequence':'Changes the reading.'});self.check()
    def test_selected_option_must_exist(self):
        self.value['decisions'][0]['selected']='missing'
        with self.assertRaises(ValueError):self.check()
    def test_applied_basis_only(self):
        self.task['sources'][0]['disposition']='considered-not-used'
        with self.assertRaises(ValueError):self.check()
    def test_each_criterion_has_realization(self):
        self.task['criteria'].append({'id':'unlinked','strength':'hard','text':'Some other effect','evidence':'any'})
        with self.assertRaises(ValueError):self.check()
    def test_authored_delivery_retains_selected_evidence(self):
        before=copy.deepcopy(self.value)
        result=direction.compile_direction(self.value,'A distinct authored rendition.','authored-rendition')
        decision=self.value['decisions'][0]
        option=next(x for x in decision['options'] if x['id']==decision['selected'])
        self.assertEqual(result['selected'],[{'decision':decision['id'],'instruction':option['realization'],'criteria':decision['criteria']}])
        self.assertEqual(self.value,before)
    def test_bounded_delivery_excludes_alternatives(self):
        self.value['decisions'][0]['options'].append({'id':'unused','realization':'PRIVATE UNUSED MATERIAL','consequence':'Private consideration.'})
        result=direction.compile_direction(self.value,'Instructions','bounded-context');self.assertNotIn('PRIVATE',str(result));self.assertNotIn('persona',str(result))
    def test_departure_keeps_reason_and_preserved_conditions(self):
        self.value['departures']=[{'source':'persona','scope':'This plate','reason':'An intentional contrast','preserved':'Core identity and commitments'}];self.check()
    def test_instant_cannot_omit_motion_limits(self):
        self.value['action_context']={'phase':'supported','before':'approach','after':'release','relations':[{'subjects':['surface','form'],'relation':'support','condition':'Contact is maintained.'}]}
        self.value['verification_limits']=[]
        with self.assertRaises(ValueError):self.check()
    def test_generic_nonhuman_action_context(self):
        self.value['action_context']={'phase':'maintained','before':'formation','after':'dispersion','relations':[{'subjects':['field','pattern'],'relation':'modulation','condition':'No fixed anatomy.'}]};self.check()
    def test_repair_requires_actual_observation(self):
        repair={'decisions':['realization'],'observation_indices':[1],'operation':'change framing','scope':'current plate','reason':'Observed ambiguity','targets':['delivery'],'expected_evidence':'A readable distinction'}
        with self.assertRaises(ValueError):direction.validate_repairs([repair],self.value,[{'observation':'one'}])
    def test_dependency_impact_does_not_infer_artistic_success(self):
        p={'task':{**self.task,'direction':self.value}};result=direction.impact(p,{'persona.md'})
        self.assertEqual(result['reconsider_decisions'],['realization']);self.assertIn('Artistic',result['meaning'])

class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.p={'input_sha256':'a'*64,'task':{'sources':[],'criteria':[{'id':'hard','strength':'hard'}]}}
        self.grant={'input_sha256':'a'*64,'principal':'SYNTHETIC TEST','actor':'test','purpose':'Test only',
          'permissions':[{'operation':'edit','scopes':['decision:one'],'max_calls':2,'max_outputs':2,'max_cost':'0.30','currency':'USD', 'request_scope': None, 'submission_validation_modes': (['target-schema', 'bounded-probe', 'observed-profile'] if 'edit' == 'submit' else [])}],
          'preserve_sources':[],'stop_conditions':[],'halt_on':[],'expires_at':None,'evidence':{'path':'test.txt','locator':'whole'}}
        self.rows=[{'event':'authorization','sha256':'b'*64,'sequence':1,'data':{'authorization':self.grant}}]
        self.args={'authorization':'b'*64,'actor':'test','operation':'edit','scopes':['decision:one'],'request_sha256':'c'*64,'outputs':1,'cost':'0.10','currency':'USD'}
    def reserve(self,**kw):return authority.reservation(self.p,self.rows,**{**self.args,**kw})
    def used(self,**kw):
        r=self.reserve(**kw)
        row={'event':'reservation','sequence':len(self.rows)+1,'data':r}
        row['sha256']=c.content_id(row)
        self.rows.append(row)
        return r
    def test_explicit_permission(self):self.reserve()
    def test_spending_does_not_imply_adoption(self):
        with self.assertRaises(ValueError):self.reserve(operation='adopt')
    def test_actor_is_bound(self):
        with self.assertRaises(ValueError):self.reserve(actor='another')
    def test_scope_is_bound(self):
        with self.assertRaises(ValueError):self.reserve(scopes=['decision:other'])
    def test_task_scope_is_explicitly_bounded_to_prepared_input(self):
        self.grant['permissions'][0]['scopes']=['task'];self.reserve(scopes=['decision:other'])
        self.p['input_sha256']='d'*64
        with self.assertRaises(ValueError):self.reserve()
    def test_decimal_accumulation_not_float_rounding(self):
        self.used();self.used(request_sha256='d'*64,cost='0.20')
    def test_budget_cannot_be_exceeded(self):
        self.used(cost='0.25')
        with self.assertRaises(ValueError):self.reserve(request_sha256='d'*64,cost='0.06')
    def test_output_limit(self):
        self.used(outputs=2)
        with self.assertRaises(ValueError):self.reserve(request_sha256='d'*64)
    def test_call_limit(self):
        self.grant['permissions'][0]['max_calls']=1;self.used()
        with self.assertRaises(ValueError):self.reserve(request_sha256='d'*64,outputs=0)
    def test_idempotent_identity_not_new_permission(self):
        first=self.used();self.assertEqual(first,self.reserve())
        with self.assertRaises(ValueError):self.reserve(cost='0.11')
    def test_revocation(self):
        self.rows.append({'event':'revocation','sequence':2,'data':{'authorization':'b'*64}})
        with self.assertRaises(ValueError):self.reserve()
    def test_expiry(self):
        self.grant['expires_at']='2000-01-01T00:00:00Z'
        with self.assertRaises(ValueError):self.reserve()
    def test_review_halt(self):
        self.grant['halt_on']=['failed-hard-review'];self.rows.append({'event':'review','sequence':2,'data':{'review':{'checks':[{'criterion':'hard','verdict':'fail'}],'unresolved':[]}}})
        with self.assertRaises(ValueError):self.reserve()
    def test_unresolved_halt(self):
        self.grant['halt_on']=['unresolved-review'];self.rows.append({'event':'review','sequence':2,'data':{'review':{'checks':[],'unresolved':['Need actual acting evidence.']}}})
        with self.assertRaises(ValueError):self.reserve()
    def test_invalid_money(self):
        for value in [0.1,'NaN','-1','1e6','01.2',True]:
            with self.subTest(value=value),self.assertRaises(ValueError):self.reserve(cost=value)
    def test_currency_not_inferred(self):
        with self.assertRaises(ValueError):self.reserve(currency='none')
    def test_no_wildcard_scope(self):
        self.grant['permissions'][0]['scopes']=['*']
        with self.assertRaises(ValueError):self.reserve()

class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        out=io.BytesIO();Image.new('RGB',(8,12)).save(out,format='PNG');self.raw=out.getvalue();self.path=self.root/'test.png';self.path.write_bytes(self.raw);self.media=media.inspect(self.path,self.raw)
    def test_actual_dimensions(self):self.assertEqual((self.media['width'],self.media['height']),(8,12))
    def test_still_cannot_prove_motion(self):self.assertFalse(media.supports(self.media,'video'))
    def test_still_cannot_prove_sound(self):self.assertFalse(media.supports(self.media,'audio'))
    def test_region(self):media.validate_locator({'kind':'region','unit':'normalized','x':.2,'y':.1,'width':.8,'height':.9},self.raw,self.media)
    def test_region_out_of_bounds(self):
        with self.assertRaises(ValueError):media.validate_locator({'kind':'region','unit':'normalized','x':.2,'y':.1,'width':1,'height':.9},self.raw,self.media)
    def test_absent_stream(self):
        with self.assertRaises(ValueError):media.validate_locator({'kind':'time','unit':'seconds','start':0,'end':1,'stream':0},self.raw,self.media)
    def test_text_line_and_byte_coordinates(self):
        media.validate_locator({'kind':'lines','start':2,'end':2},b'a\nb\n',{'kind':'text'})
        with self.assertRaises(ValueError):media.validate_locator({'kind':'bytes','start':0,'end':1},b'abc',{'kind':'text'})
    def test_unknown_media_stays_unmeasured(self):
        p=self.root/'unknown';p.write_bytes(b'\x00\xffgarbage');self.assertEqual(media.inspect(p)['kind'],'unmeasured')

if __name__=='__main__':unittest.main(verbosity=2)
