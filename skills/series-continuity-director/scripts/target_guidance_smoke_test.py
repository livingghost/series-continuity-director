#!/usr/bin/env python3
"""Exercise advice selection and exact request construction with synthetic data."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import execution_contract as c
import execution_choices as choices
from input_evidence import InputEvidence
import input_contracts
import production_direction
import production_test_support as support
import request_renderer
import target_guidance
import target_protocol
import transport_synthetic
import visual_language


class ChoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = {'transport': 'synthetic', 'operations': {'draw': {}},
                        'endpoint': {'base_url': 'https://example.invalid/not-used'}}
        self.spec = {'submission_id': 'study', 'kind': 'asset', 'target': 'synthetic-study',
                     'service': 'synthetic-service', 'model': 'synthetic:model-1', 'operation': 'draw',
                     'text': 'One geometric form.', 'inputs': [], 'parameters': {'count': 1, 'seed': 0},
                     'obligations': {'locks': [], 'permanent_features': []}}
        self.profile, self.offering, self.profiles = support.model_inputs(self.root, self.spec, self.service)
        self.reader = InputEvidence(self.root)
        import request_validation
        request_validation.require(self.spec["request_validation"], self.reader)
        self.plan = support.execution_plan(self.spec)
        self.guidance = {'artifact_type': 'target-guidance', 'id': 'synthetic-advice', 'label': 'Synthetic test advice',
                        'applies_to': {'target_id': self.spec['target'], 'service': self.spec['service'],
                                       'model_identifier': self.spec['model'], 'operation': self.spec['operation'],
                                       'output_kinds': ['text'], 'input_modes': [], 'purposes': ['synthetic-test'], 'visual_language': []},
                        'prompt_structure': ['Subject, then observable treatment.'], 'entries': [],
                        'limits': ['A test fixture, not an observed model result.']}
        self.policy = {}; self.guidance_refs = []

    def write(self, name, data):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(c.encoded(data))
        return self.reader.select(name)

    def entry(self, identifier, **fields):
        return {'id': identifier, 'reason': 'Synthetic choice for this test only.', 'conflicts_with': [],
                'evidence': [{'kind': 'hypothesis', 'reference': 'synthetic fixture', 'scope': 'no real service'}], 'limits': [], **fields}

    def add_parameter(self):
        self.guidance['entries'] = [self.entry('setting', kind='parameter', field='seed', proposed={'kind': 'choices', 'values': [0, 4]})]
        self.guidance_refs = [self.write('advice.json', self.guidance)]
        self.plan['recommendations'] = [{'guidance': 'synthetic-advice', 'entry': 'setting', 'decision': 'adopt', 'reason': 'Test selection.'}]
        self.plan['settings'][1].update(state='recommended', recommendation={'guidance': 'synthetic-advice', 'entry': 'setting'})

    def add_text(self, *, channel='positive'):
        field = 'text' if channel == 'positive' else 'negative_text'
        if channel == 'negative':
            self.spec[field] = 'No border.'
            self.plan = support.execution_plan(self.spec)
        self.guidance['entries'] = [self.entry('wording', kind='text', channel=channel, text=self.spec[field], allow_rewording=False, role='treatment')]
        self.guidance_refs = [self.write('advice.json', self.guidance)]
        self.plan['recommendations'] = [{'guidance': 'synthetic-advice', 'entry': 'wording', 'decision': 'adopt', 'reason': 'Test selection.'}]
        self.plan['segments'][channel][0]['recommendation'] = {'guidance': 'synthetic-advice', 'entry': 'wording'}

    def build(self):
        value = choices.build(self.plan, self.reader, spec=self.spec,
                              profile_ref=self.reader.select('profiles/fixture.json'),
                              service_ref=self.reader.select('selected-test-services.json'),
                              guidance_refs=self.guidance_refs, policy=self.policy)
        resolved = choices.resolve(value, self.reader, spec=self.spec, policy=self.policy)
        choices.attach(self.spec, value, resolved)
        input_contracts.attach(self.spec, self.spec['request_validation'], self.reader)
        return value, resolved

    def render(self):
        self.build()
        return request_renderer.submission(self.spec, self.profile, self.offering, self.service, transport_synthetic, root=self.root)

    def test_no_guidance_still_allows_explicit_values(self):
        result = self.render()
        self.assertEqual(result['rendered']['request']['seed'], 0)
        self.assertEqual(result['target_info']['guidance_status'], 'not-registered-for-context')

    def test_recommendation_is_visible_and_bound_to_parameter(self):
        self.add_parameter(); built = self.render()
        self.assertEqual(built['target_info']['guidance'][0]['guidance']['id'], 'synthetic-advice')
        trace = next(x for x in built['rendered']['request_trace'] if x['target_field'] == ['seed'])
        self.assertEqual(trace['transform_id'], 'selected-recommended')
        self.assertEqual(trace['source_refs'][0]['source']['path'], 'advice.json')

    def test_recommendation_rejection_is_explicit(self):
        self.add_parameter(); self.plan['recommendations'][0]['decision'] = 'reject'
        self.plan['settings'][1].update(state='explicit', recommendation=None)
        self.render()

    def test_missing_decision_is_not_automatic_adoption(self):
        self.add_parameter(); self.plan['recommendations'] = []
        with self.assertRaises(ValueError): self.build()

    def test_range_never_selects_a_midpoint(self):
        self.add_parameter(); self.guidance['entries'][0]['proposed'] = {'kind': 'range', 'minimum': 0, 'maximum': 8, 'integer': True}
        self.guidance_refs = [self.write('range-advice.json', self.guidance)]
        self.assertEqual(self.render()['rendered']['request']['seed'], 0)

    def test_out_of_range_recommended_value_is_refused(self):
        self.add_parameter(); self.plan['settings'][1]['value'] = 7
        with self.assertRaises(ValueError): self.build()

    def test_false_zero_and_empty_array_are_values(self):
        self.spec['parameters'].update(sound=False, stops=[])
        self.plan = support.execution_plan(self.spec)
        built = self.render()['rendered']['request']
        self.assertIs(built['sound'], False); self.assertEqual(built['seed'], 0); self.assertEqual(built['stops'], [])

    def test_bool_is_not_integer_recommendation(self):
        self.add_parameter(); self.plan['settings'][1]['value'] = False
        with self.assertRaises(ValueError): self.build()

    def test_parameters_and_options_cannot_overlap(self):
        self.spec['options'] = {'seed': 0}
        with self.assertRaises(ValueError): self.build()

    def test_overlapping_setting_paths_are_refused(self):
        self.plan['settings'].append({'field': 'seed.child', 'state': 'explicit', 'value': 1, 'reason': 'Test.', 'recommendation': None})
        with self.assertRaises(ValueError): self.build()

    def test_unresolved_state_is_refused(self):
        self.plan['settings'][0]['state'] = 'undecided'
        with self.assertRaises(ValueError): self.build()

    def test_no_schema_or_parameter_is_inferred_from_model_name(self):
        self.plan['settings'] = []
        with self.assertRaises(ValueError): self.build()

    def test_offering_value_requires_a_choice(self):
        self.offering['constraints']['as_written'] = {'detail': 2}
        self.profile['offerings'] = [self.offering]
        self.profile = target_protocol.finalize_profile(self.profile)
        self.write('profiles/fixture.json', self.profile)
        with self.assertRaises(ValueError): self.build()

    def test_transport_does_not_insert_offering_values(self):
        self.offering['constraints']['as_written'] = {'detail': 2}
        built = transport_synthetic.compile_request(self.spec, self.offering, self.service)
        self.assertNotIn('detail', built['request'])

    def test_applicable_control_requires_selection(self):
        self.policy = {'controls': [{'field': 'detail', 'availability': 'selectable', 'allow_provider_managed': False, 'reason': 'Synthetic exposed control.'}]}
        with self.assertRaises(ValueError): self.build()

    def test_nonapplicable_control_has_no_wire_key(self):
        self.policy = {'controls': [{'field': 'denoise', 'availability': 'not-applicable', 'allow_provider_managed': False, 'reason': 'No input image in this test.'}]}
        self.plan['settings'].append({'field': 'denoise', 'state': 'not-applicable', 'value': None, 'reason': 'Text input only.', 'recommendation': None})
        _, resolved = self.build(); self.assertNotIn('denoise', resolved['parameters'])

    def test_nonapplicable_value_cannot_be_sent(self):
        self.policy = {'controls': [{'field': 'seed', 'availability': 'not-applicable', 'allow_provider_managed': False, 'reason': 'Synthetic restricted operation.'}]}
        with self.assertRaises(ValueError): self.build()

    def test_unexposed_control_is_distinct_from_an_omission(self):
        self.policy = {'controls': [{'field': 'internal-rate', 'availability': 'not-exposed', 'allow_provider_managed': False, 'reason': 'No public control.'}]}
        self.plan['settings'].append({'field': 'internal-rate', 'state': 'not-exposed', 'value': None, 'reason': 'Not user controlled.', 'recommendation': None})
        _, resolved = self.build(); self.assertNotIn('internal-rate', resolved['parameters'])

    def test_provider_managed_is_an_explicit_per_control_choice(self):
        self.policy = {'controls': [{'field': 'rate', 'availability': 'selectable', 'allow_provider_managed': True, 'reason': 'Optional exposed control.'}]}
        self.plan['settings'].append({'field': 'rate', 'state': 'provider-managed', 'value': None, 'reason': 'No fixed rate required for this trial.', 'recommendation': None})
        _, result = self.build(); self.assertNotIn('rate', result['parameters'])

    def test_cannot_delegate_a_required_control(self):
        self.policy = {'controls': [{'field': 'rate', 'availability': 'selectable', 'allow_provider_managed': False, 'reason': 'Rate is required.'}]}
        self.plan['settings'].append({'field': 'rate', 'state': 'provider-managed', 'value': None, 'reason': 'Test.', 'recommendation': None})
        with self.assertRaises(ValueError): self.build()

    def test_text_recommendation_reaches_normal_request_trace(self):
        self.add_text(); built = self.render()
        trace = next(x for x in built['rendered']['request_trace'] if x['target_field'] == ['prompt'])
        self.assertEqual(trace['transform_id'], 'chosen-recommendation')
        self.assertEqual(trace['source_refs'][0]['source']['path'], 'advice.json')

    def test_negative_recommendation_has_its_own_trace(self):
        self.add_text(channel='negative'); built = self.render()
        trace = next(x for x in built['rendered']['request_trace'] if x['target_field'] == ['avoid'])
        self.assertEqual(trace['transform_id'], 'chosen-recommendation')

    def test_changed_text_is_refused(self):
        self.build(); self.spec['text'] += ' Different.'
        with self.assertRaises(ValueError):
            choices.require(self.spec, self.reader, policy={}, profile=self.profile, service=self.service)

    def test_gap_in_text_segments_is_refused(self):
        self.plan['segments']['positive'][0]['start'] = 1
        with self.assertRaises(ValueError): self.build()

    def test_rewording_needs_explicit_permission_and_relation(self):
        self.add_text(); self.guidance['entries'][0]['text'] = 'Original wording.'
        self.guidance_refs = [self.write('exact-advice.json', self.guidance)]
        with self.assertRaises(ValueError): self.build()
        self.guidance['entries'][0]['allow_rewording'] = True
        self.guidance_refs = [self.write('adaptable-advice.json', self.guidance)]
        self.render()

    def test_conflicting_advice_is_not_combined(self):
        self.add_parameter()
        other = self.entry('opposed', kind='text', channel='positive', text=self.spec['text'], allow_rewording=False, role='test')
        other['conflicts_with'] = ['setting']; self.guidance['entries'].append(other)
        self.guidance_refs = [self.write('conflict-advice.json', self.guidance)]
        self.plan['recommendations'].append({'guidance': 'synthetic-advice', 'entry': 'opposed', 'decision': 'adopt', 'reason': 'Test.'})
        with self.assertRaises(ValueError): self.build()

    def test_wrong_operation_advice_is_not_used(self):
        self.add_parameter(); self.guidance['applies_to']['operation'] = 'another-operation'
        self.guidance_refs = [self.write('wrong-advice.json', self.guidance)]
        with self.assertRaises(ValueError): self.build()

    def test_wrong_output_context_is_refused(self):
        self.plan['context']['output_kind'] = 'video'
        with self.assertRaises(ValueError): self.build()

    def test_guidance_change_invalidates_source_snapshot(self):
        self.add_parameter(); self.build()
        self.guidance['label'] += ' changed'; (self.root/'advice.json').write_bytes(c.encoded(self.guidance))
        with self.assertRaises(ValueError):
            choices.require(self.spec, self.reader, policy={}, profile=self.profile, service=self.service)

    def test_actual_model_cannot_replace_selected_model(self):
        self.build(); changed = copy.deepcopy(self.profile); changed['label'] += ' changed'
        with self.assertRaises(ValueError):
            choices.require(self.spec, self.reader, policy={}, profile=changed, service=self.service)

    def test_service_cannot_be_silently_replaced(self):
        self.build()
        with self.assertRaises(ValueError):
            choices.require(self.spec, self.reader, policy={}, profile=self.profile, service={**self.service, 'transport': 'runware'})

    def test_adapter_cannot_add_an_unselected_field(self):
        value, result = self.build(); compiled = transport_synthetic.compile_request(self.spec, self.offering, self.service)
        compiled['request']['detail'] = 7
        with self.assertRaises(ValueError): choices.bind_trace(compiled, value, result, native_controls=[])

    def test_adapter_cannot_change_a_selected_value(self):
        value, result = self.build(); compiled = transport_synthetic.compile_request(self.spec, self.offering, self.service)
        compiled['request']['seed'] = 5
        with self.assertRaises(ValueError): choices.bind_trace(compiled, value, result, native_controls=[])

    def test_selected_guidance_changes_sealed_request_even_with_same_text(self):
        first = self.render()['rendered']['request_sha256']
        self.add_text(); second = self.render()['rendered']['request_sha256']
        self.assertNotEqual(first, second)

    def test_external_profile_information_is_displayed(self):
        self.add_parameter()
        result = target_protocol.describe(self.spec['target'], [self.profiles], service=self.spec['service'], operation=self.spec['operation'], context=self.plan['context'], guidance_paths=[self.root/'advice.json'])
        self.assertEqual(result['guidance_status'], 'available')
        self.assertEqual(result['definition']['path'], str(self.profiles/'fixture.json'))

    def test_same_priority_duplicate_target_is_refused(self):
        self.write('profiles/duplicate.json', self.profile)
        with self.assertRaises(ValueError): target_protocol.resolve_profile(self.spec['target'], [self.profiles])

    def test_ordered_override_uses_first_explicit_source(self):
        changed = copy.deepcopy(self.profile); changed['label'] = 'Selected project definition'
        changed = target_protocol.finalize_profile(changed); self.write('preferred/model.json', changed)
        result = target_protocol.resolve_profile(self.spec['target'], [self.root/'preferred', self.profiles])
        self.assertEqual(result[1]['label'], 'Selected project definition')

    def test_pinned_selection_ignores_another_catalog_search(self):
        self.build()
        result = target_protocol.selected_profile(self.spec, [self.root/'absent'], self.root)
        self.assertEqual(result[1], self.profile)

    def test_no_network_dispatch_during_preparation(self):
        with patch.object(transport_synthetic, 'send', side_effect=AssertionError('send')):
            self.render()


    def cli(self, *args):
        import subprocess, sys
        done = subprocess.run([sys.executable, str(Path(__file__).parent / args[0]), *args[1:]],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def selection_arguments(self):
        return ['--target', self.spec['target'], '--profiles', str(self.profiles),
                '--guidance', str(self.root/'advice.json'), '--service', self.spec['service'],
                '--operation', self.spec['operation'], '--output-kind', 'text',
                '--purpose', 'synthetic-test']

    def test_external_card_is_printed_by_inspect_command(self):
        self.add_parameter()
        card = json.loads(self.cli('target_protocol.py', 'inspect', *self.selection_arguments()))
        self.assertEqual(card['guidance'][0]['guidance']['id'], 'synthetic-advice')
        self.assertEqual(card['definition']['path'], str(self.profiles/'fixture.json'))

    def test_route_reading_prints_external_model_advice(self):
        self.add_parameter()
        output = self.cli('execution_routes.py', 'read', 'media', '--root', str(self.root), *self.selection_arguments())
        self.assertIn('target-guidance:', output)
        self.assertIn('synthetic-advice', output)
        self.assertIn('reading-key: media', output)

    def test_submission_draft_prints_external_advice_without_sending(self):
        self.add_parameter()
        (self.root/'wording.txt').write_text(self.spec['text'])
        args = self.selection_arguments()
        args[args.index('--purpose')] = '--guidance-purpose'
        output = self.cli('submission_draft.py', 'new', '--json', '--project', str(self.root),
                          '--out', 'media/study.submission.json', '--kind', 'asset', '--no-inputs',
                          '--text-file', str(self.root/'wording.txt'), *args)
        card = json.loads(output)['target_info']
        self.assertEqual(card['guidance'][0]['guidance']['id'], 'synthetic-advice')
        self.assertNotIn('execution_choices', c.load(self.root/'media/study.submission.json'))

    def test_request_review_rechecks_choices_and_advice(self):
        import production_request
        self.add_parameter(); built = self.render()
        self.assertTrue(production_request.validate_request(self.spec, built['rendered'], live_root=self.root))
        self.spec['execution_choices']['settings'][0]['reason'] = 'Different choice evidence.'
        self.spec['execution_choices_sha256'] = c.content_id(self.spec['execution_choices'])
        with self.assertRaises(ValueError):
            production_request.validate_request(self.spec, built['rendered'], live_root=self.root)

    def test_historical_request_review_uses_preserved_advice_bytes(self):
        import production_request
        self.add_parameter(); built = self.render()
        (self.root/'advice.json').unlink()
        self.assertTrue(production_request.validate_request(self.spec, built['rendered']))
        with self.assertRaises(ValueError):
            production_request.validate_request(self.spec, built['rendered'], live_root=self.root)


    def test_changed_choice_is_reported_as_gate_refusal(self):
        import submission_gate
        self.render()
        self.spec['execution_choices']['settings'][0]['value'] = 3
        report = submission_gate.gate(self.spec, self.profiles, self.root)
        self.assertEqual(report['status'], 'refused')
        self.assertIn('EXECUTION_CHOICES_INVALID', {item['code'] for item in report['errors']})

    def test_shipped_example_is_valid_advice_and_explicit_plan(self):
        from state_protocol import validate_against_schema
        root = Path(__file__).resolve().parents[1]
        document = c.load(root/'examples/target-guidance/guidance.json')
        target_guidance.validate(document)
        plan = c.load(root/'examples/target-guidance/execution-plan.json')
        self.assertEqual(validate_against_schema(plan, c.load(root/'schemas/authoring/execution-choices.schema.json')), [])
        self.assertEqual(''.join(row['text'] for row in plan['segments']['positive']),
                         'One geometric form. Keep a continuous boundary.')

    def test_parameter_paths_match_preliminary_gate_and_real_transport(self):
        import submission_gate
        self.spec['parameters']['treatment.edge'] = 'continuous'
        self.plan = support.execution_plan(self.spec)
        made = self.render()['rendered']['request']
        checked = submission_gate.build_instance(self.spec['text'], [], [], self.spec['parameters'], self.offering)
        self.assertEqual(checked['treatment'], made['treatment'])
        self.assertNotIn('treatment.edge', checked)

    def test_installed_definition_is_pinned_like_project_definition(self):
        import production_dispatch
        import production_workflow
        install = self.root/'installed'; install.mkdir()
        path = install/'service.json'; raw = c.encoded({'label': 'Synthetic installed definition'})
        path.write_bytes(raw)
        run = self.root/'stored'; run.mkdir()
        sha = c.object_store(run, raw)
        prepared = {'dependencies': [{'space': 'skill', 'path': 'service.json', 'sha256': sha}]}
        with patch.object(production_workflow, 'ROOT', install):
            ref, found = production_dispatch.pinned_definition(self.root, run, prepared, path)
            self.assertEqual(ref, '@skill/service.json'); self.assertEqual(found, raw)
            path.write_text('{}')
            with self.assertRaises(ValueError):
                production_dispatch.pinned_definition(self.root, run, prepared, path)

class VisualChoiceTests(unittest.TestCase):
    def setUp(self):
        self.task = {'sources': [{'id': 'style', 'disposition': 'applied', 'path': 'style.md'}],
                     'criteria': [{'id': 'appearance', 'strength': 'hard', 'text': 'Inspect treatment.', 'evidence': 'image'}]}
        self.direction = support.direction(self.task, 'Keep one flat form and a continuous boundary.')
        self.direction['visual_language'] = support.visual_selection()

    def test_visual_output_requires_selection(self):
        with self.assertRaises(ValueError): visual_language.require_for_output(None, 'image')

    def test_prose_does_not_require_drawing_choices(self):
        visual_language.require_for_output(None, 'text')

    def test_visual_and_nonvisual_are_not_conflated(self):
        with self.assertRaises(ValueError): visual_language.require_for_output(self.direction['visual_language'], 'audio')

    def test_selected_dimensions_and_instructions_reach_consumer(self):
        production_direction.validate(self.direction, self.task['sources'], self.task['criteria'])
        compiled = production_direction.compile_direction(self.direction, 'Authored output.', 'authored-rendition')
        self.assertEqual(compiled['visual_language']['anchor'][0]['instruction'], self.direction['decisions'][0]['options'][0]['realization'])

    def test_mixed_treatments_need_scope_coordination(self):
        self.direction['visual_language']['anchor'].append(copy.deepcopy(self.direction['visual_language']['anchor'][0]))
        with self.assertRaises(ValueError): production_direction.validate(self.direction, self.task['sources'], self.task['criteria'])

    def test_distinct_scopes_can_use_distinct_dimensions(self):
        language = self.direction['visual_language']; language['coordination'] = 'Share a muted palette across separately drawn layers.'
        second = copy.deepcopy(language['anchor'][0]); second['scope'] = 'background'; second['dimensions']['dimensional_treatment'] = 'spatially shaded'
        language['anchor'][0]['scope'] = 'foreground'; language['anchor'].append(second)
        production_direction.validate(self.direction, self.task['sources'], self.task['criteria'])

    def test_same_scope_dimension_conflict_requires_resolution(self):
        language = self.direction['visual_language']; language['coordination'] = 'Claimed coordination.'
        second = copy.deepcopy(language['anchor'][0]); second['dimensions']['dimensional_treatment'] = 'spatially shaded'; language['anchor'].append(second)
        with self.assertRaises(ValueError): production_direction.validate(self.direction, self.task['sources'], self.task['criteria'])

    def test_visual_source_changes_reach_existing_impact(self):
        self.direction['visual_language']['anchor'][0]['source'] = 'style'
        self.direction['basis'] = []
        result = production_direction.impact({'task': {**self.task, 'direction': self.direction}}, {'style.md'})
        self.assertEqual(result['applicable_basis_changed'], ['style'])

    def test_nonapplied_visual_source_cannot_be_inherited(self):
        self.direction['visual_language']['anchor'][0]['source'] = 'unread'
        with self.assertRaises(ValueError): production_direction.validate(self.direction, self.task['sources'], self.task['criteria'])


if __name__ == '__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
