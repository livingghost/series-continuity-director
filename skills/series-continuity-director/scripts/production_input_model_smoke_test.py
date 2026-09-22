#!/usr/bin/env python3
"""Assemble local submission evidence using a synthetic, non-network interface."""
from __future__ import annotations
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import execution_contract as c
from input_evidence import InputEvidence
import production_inputs as inputs
import reading_fixtures
import production_test_support as support
import request_validation


class ModelInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Use the declared public shape as test data. Nothing contacts its provider.
        profiles = inputs.ROOT / 'protocols/target/profiles'
        self.profile = next(value for value in (c.load(path) for path in sorted(profiles.glob('*.json')))
                            if 'image' in value['media_kind'] and value.get('offerings'))
        offering = self.profile['offerings'][0]
        self.target = {'service': offering['service'], 'model_identifier': offering['model_identifier'],
                       'operation': 'imageInference'}
        self.spec = {'submission_id': 'synthetic-input-test', 'kind': 'asset',
                     'target': self.profile['target_id'], 'service': self.target['service'],
                     'model': self.target['model_identifier'], 'operation': self.target['operation'],
                     'text': 'Synthetic isolated study.', 'text_form': 'natural-language',
                     'output_kind': 'image', 'inputs': [], 'parameters': {'numberResults': 1}}
        self.write('submission-source.json', self.spec)
        self.write('profile.json', self.profile)
        self.write('services.json', {'services': {self.target['service']: {
            'operations': {'imageInference': {}},
            'endpoint': {'base_url': 'https://example.invalid/synthetic-interface'}}}})
        (self.root / 'basis.txt').write_text('Synthetic single-subject exploration. Not an author approval.\n')
        (self.root / 'delivery.txt').write_text(self.spec['text'])
        schema = {'type': 'object'}
        response = self.write('response.json', {'schema': schema, 'synthetic': True})
        self.write('acquisition.json', {'artifact_type': 'schema-acquisition', 'target': self.target,
            'source': {'kind': 'document', 'identifier': 'Synthetic offline interface', 'locator': 'schema member'},
            'acquired_at': '2000-01-01T00:00:00Z', 'response': response,
            'status': {'document_status': 'schema-provided'}})
        self.write('contract.json', {'artifact_type': 'model-schema-contract', 'target': self.target,
            'schema': schema, 'schema_sha256': c.content_id(schema), 'response_pointer': '/schema',
            'local_overlay': None})
        self.task = {'task_id': 'synthetic-input-task', 'route': 'media', 'features': [],
                     'sources': [{'id': 'submission', 'path': 'submission-source.json', 'role': 'configuration',
                                  'disposition': 'applied', 'locator': 'whole', 'reason': 'Synthetic input source.'}],
                     'delivery': {'path': 'delivery.txt', 'transport': 'authored-rendition',
                                  'translation_notes': 'Retain the synthetic statement.'},
                     'criteria': [{'id': 'output', 'text': 'Inspect the synthetic output.', 'strength': 'hard', 'evidence': 'text'}],
                     'sequence_plan': None}
        self.task['direction'] = support.direction(self.task, self.spec['text'])
        reading_fixtures.task_reading(self.root, self.task)
        reading = c.load(self.root / self.task['route_reading'])
        self.write('task.json', self.task)
        visual = {'purpose': 'image', 'basis': {'path': 'basis.txt', 'locator': 'whole'},
                  'subjects': {'subject-1': {'continuity': 'undecided', 'character_id': None, 'identity_refs': []}},
                  'shot_camera': None, 'shot_request': None, 'reference_activation': None,
                  'submission': 'submission-source.json'}
        self.choices = {'reading': {'snapshot_id': None, 'reading_key': reading['reading_key'], 'applied': reading['applied']},
                        'visual': visual, 'validation': {'mode': 'target-schema', 'submission': 'submission-source.json',
                            'target_profile': 'profile.json', 'service_profiles': 'services.json',
                            'contract': 'contract.json', 'evidence': 'acquisition.json', 'execution_policy': None},
                        'source_run': None}
        self.write('choices.json', self.choices)

    def write(self, path, value):
        raw = c.encoded(value)
        (self.root / path).write_bytes(raw)
        return {'path': path, 'sha256': c.digest(raw)}

    def build(self):
        self.write('choices.json', self.choices)
        return inputs.build_inputs(self.root, 'task.json', 'choices.json', 'built')

    def test_full_input_assembly_binds_submission(self):
        before = c.read(self.root / 'submission-source.json')
        result = self.build()
        self.assertTrue(result['ok'])
        spec = c.load(self.root / result['inputs']['submission']['path'])
        self.assertEqual(spec['text'], self.spec['text'])
        self.assertEqual(spec['visual_continuity']['subjects'], self.choices['visual']['subjects'])
        self.assertEqual(spec['visual_continuity_sha256'], c.content_id(spec['visual_continuity']))
        request_validation.require(spec['request_validation'], InputEvidence(None, snapshots=spec['input_snapshots'], live=False))
        self.assertEqual(c.read(self.root / 'submission-source.json'), before)
        task = c.load(self.root / 'built/production-task.json')
        self.assertEqual(task['sources'][0]['path'], 'built/submission.json')
        self.assertFalse((self.root / 'production').exists())

    def test_target_profile_identity_is_exact(self):
        self.spec['target'] = 'synthetic-unrelated-target'
        self.write('submission-source.json', self.spec)
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse((self.root / 'built').exists())

    def test_profile_content_integrity_is_checked(self):
        self.profile['profile_sha256'] = '0' * 64
        self.write('profile.json', self.profile)
        with self.assertRaises(ValueError):
            self.build()

    def test_unmeasured_statements_are_not_a_choice(self):
        self.choices['validation']['unmeasured'] = []
        with self.assertRaises(ValueError):
            self.build()

    def test_different_submissions_cannot_be_combined(self):
        self.write('different-submission.json', dict(self.spec, text='Changed synthetic statement.'))
        self.choices['validation']['submission'] = 'different-submission.json'
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse((self.root / 'built').exists())

    def test_undecided_pair_is_refused_before_publication(self):
        self.choices['visual']['subjects']['subject-2'] = copy.deepcopy(self.choices['visual']['subjects']['subject-1'])
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse((self.root / 'built').exists())

    def test_nonvisual_cannot_hide_image_output(self):
        self.choices['visual'].update(purpose='nonvisual', basis=None, subjects={})
        with self.assertRaises(ValueError):
            self.build()

    def test_acquisition_target_is_not_overwritten(self):
        evidence = c.load(self.root / 'acquisition.json')
        evidence['target'] = dict(self.target, model_identifier='unrelated-synthetic-model')
        self.write('acquisition.json', evidence)
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(c.load(self.root / 'acquisition.json')['target'], evidence['target'])

    def test_derived_basis_hash_is_rejected_as_a_choice(self):
        self.choices['visual']['basis']['sha256'] = 'f' * 64
        with self.assertRaises(ValueError):
            self.build()

    def test_build_does_not_authorize_or_send(self):
        import production_workflow
        with (patch.object(production_workflow, 'prepare', side_effect=AssertionError('prepare')),
              patch.object(production_workflow, 'authorize', side_effect=AssertionError('authorize'))):
            self.assertTrue(self.build()['ok'])


class SelectionInputTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'owner_path': 'assets.md', 'asset_id': 'ASSET-1', 'role': 'identity'}
        self.choice = {'kind': 'production-selection', 'run': 'synthetic-run', 'selection': 'a' * 64}
        self.row = {'event': 'selection', 'sha256': 'a' * 64,
                    'data': {'selection': {'candidate': 'c' * 64, 'scope': 'registry-adoption',
                        'adoption': self.registry, 'influence': 'identity'}}}

    def resolve(self, rows):
        import production_workflow
        from visual_continuity import selection_choice
        with patch.object(production_workflow, 'load_run', return_value=(Path('.'), {}, {}, rows)):
            return selection_choice(Path('.'), self.choice, self.registry)

    def test_hash_is_derived_from_verified_selection(self):
        result = self.resolve([self.row])
        self.assertEqual(result['selection_sha256'], self.row['sha256'])
        self.assertNotIn('selection_sha256', self.choice)

    def test_caller_hash_is_not_a_choice(self):
        self.choice['selection_sha256'] = 'a' * 64
        with self.assertRaises(ValueError):
            self.resolve([self.row])

    def test_missing_selection_is_not_invented(self):
        with self.assertRaises(ValueError):
            self.resolve([])

    def test_ambiguous_selection_is_not_first_match(self):
        with self.assertRaises(ValueError):
            self.resolve([self.row, copy.deepcopy(self.row)])

    def test_selection_identifier_is_matched_exactly(self):
        self.choice['selection'] = 'd' * 64
        with self.assertRaises(ValueError):
            self.resolve([self.row])

    def test_registry_is_matched_exactly(self):
        self.row['data']['selection']['adoption'] = dict(self.registry, asset_id='ASSET-2')
        with self.assertRaises(ValueError):
            self.resolve([self.row])

    def test_outfit_permission_does_not_become_identity(self):
        self.row['data']['selection']['influence'] = 'outfit'
        with self.assertRaises(ValueError):
            self.resolve([self.row])

    def test_delivery_selection_does_not_become_adoption(self):
        self.row['data']['selection']['scope'] = 'delivery-only'
        with self.assertRaises(ValueError):
            self.resolve([self.row])


if __name__ == '__main__':
    unittest.main()
