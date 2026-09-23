#!/usr/bin/env python3
"""Exercise local tactic consultation, source selection and review questions."""
from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import execution_contract as c
import tactic_consultation as tool
import production_inputs
import production_workflow as workflow
import production_workflow_smoke_test as fixtures
import reading_fixtures


class TacticConsultationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ProductionTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root; self.task = self.fixture.task
        reading_fixtures.task_reading(self.root, self.task)
        self.write('task.json', self.task)
        self.text = '# Synthetic tactics\n\n## A scoped light\nKeep the shadow side readable with a restrained fill.\nPreserve the declared identity and stage geometry.\n'
        self.write('production-state.md', self.text)
        self.result = tool.consult(self.root, 'task.json', 'over the shoulder', 'consulted')
        self.report = c.load(self.root / self.result['consultation'])
        self.choices = {'source_id': 'light-study', 'reason': 'Adapt a scoped local light tactic.',
            'uses': [{'source': {'kind': 'passage', 'path': 'production-state.md', 'start_line': 4, 'end_line': 5},
                      'borrowed': 'A restrained fill preserves readable details.',
                      'preserved': 'Retain stage geometry and existing identity.', 'changed': 'Use the tactic in this declared local condition.',
                      'target_source': '@delivery', 'target_locator': 'The complete authored delivery.',
                      'review_criteria': ['condition'], 'review_question': 'Does the actual output retain the declared condition?'}],
            'not_used': []}
        self.write('decisions.json', self.choices)

    def write(self, name, value):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value.encode('utf-8') if isinstance(value, str) else c.encoded(value))

    def apply(self):
        return tool.apply(self.root, 'task.json', 'consulted/consultation.json', 'decisions.json', 'applied')

    def test_consultation_returns_entire_project_source(self):
        self.assertEqual(self.report['sources'][0]['text'], self.text)
        self.assertEqual(self.report['sources'][0]['line_count'], 5)
        self.assertFalse(self.report['external_effect'])
        self.assertFalse((self.root / 'production').exists())

    def test_vocabulary_result_retains_the_complete_entry(self):
        self.assertTrue(self.report['vocabulary']['results'])
        row = self.report['vocabulary']['results'][0]
        self.assertIn('description', row['record'])
        self.assertEqual(row['record']['term'], row['term'])

    def test_empty_vocabulary_still_returns_tactics(self):
        result = tool.consult(self.root, 'task.json', 'synthetic-qzxpv', 'empty')
        self.assertEqual(result['vocabulary']['results'], [])
        self.assertEqual(result['sources'][0]['text'], self.text)
        self.assertIn('not proof', result['empty_result'])

    def test_explicit_extra_source_is_read_without_classifying(self):
        self.write('observations.txt', 'Scoped observation from a separate, explicit source.\n')
        result = tool.consult(self.root, 'task.json', 'camera', 'extra', sources=['observations.txt'])
        self.assertEqual({row['file']['path'] for row in result['sources']}, {'production-state.md', 'observations.txt'})

    def test_application_derives_hash_and_selected_passage(self):
        result = self.apply(); record = c.load(self.root / result['application'])
        source = record['applications'][0]['source_evidence']
        self.assertEqual(source['quote'], ''.join(self.text.splitlines(keepends=True)[3:5]))
        self.assertEqual(source['file']['sha256'], c.digest(self.text.encode()))
        self.assertEqual(record['applications'][0]['target_file']['sha256'], c.digest((self.root / 'delivery.txt').read_bytes()))

    def test_original_task_and_delivery_are_unchanged(self):
        task = (self.root / 'task.json').read_bytes(); delivery = (self.root / 'delivery.txt').read_bytes()
        result = self.apply()
        self.assertEqual((self.root / 'task.json').read_bytes(), task)
        self.assertEqual((self.root / 'delivery.txt').read_bytes(), delivery)
        self.assertFalse(result['execution_ready'])
        workflow.validate_task(c.load(self.root / result['task']))

    def test_dictionary_selection_uses_exact_category_and_term(self):
        row = self.report['vocabulary']['results'][0]
        self.choices['uses'][0]['source'] = {'kind': 'vocabulary', 'category': row['category'], 'term': row['term']}
        self.write('decisions.json', self.choices)
        result = self.apply(); source = c.load(self.root / result['application'])['applications'][0]['source_evidence']
        self.assertEqual(source['record'], row['record'])

    def test_unconsulted_passage_cannot_be_selected(self):
        self.write('other.txt', self.text)
        self.choices['uses'][0]['source']['path'] = 'other.txt'; self.write('decisions.json', self.choices)
        with self.assertRaises(ValueError): self.apply()
        self.assertFalse((self.root / 'applied').exists())

    def test_stale_source_is_rejected(self):
        self.write('production-state.md', self.text + 'New scope.\n')
        with self.assertRaises(ValueError): self.apply()

    def test_stale_task_is_rejected(self):
        self.task['delivery']['translation_notes'] += ' Changed.'; self.write('task.json', self.task)
        with self.assertRaises(ValueError): self.apply()

    def test_unknown_target_and_criterion_are_rejected(self):
        for key, value in [('target_source', 'missing'), ('review_criteria', ['missing'])]:
            changed = copy.deepcopy(self.choices); changed['uses'][0][key] = value
            self.write('decisions.json', changed)
            with self.assertRaises(ValueError): self.apply()
        self.assertFalse((self.root / 'applied').exists())

    def test_line_range_is_structural_not_semantic(self):
        self.choices['uses'][0]['source']['start_line'] = 99; self.write('decisions.json', self.choices)
        with self.assertRaises(ValueError): self.apply()

    def test_missing_judgment_is_not_filled(self):
        self.choices['uses'][0]['preserved'] = None; self.write('decisions.json', self.choices)
        with self.assertRaises(ValueError): self.apply()

    def test_nonuse_is_a_complete_valid_outcome(self):
        self.choices['not_used'] = [{'source': self.choices['uses'][0]['source'], 'reason': 'This output needs a different treatment.'}]
        self.choices['uses'] = []; self.write('decisions.json', self.choices)
        result = self.apply(); task = c.load(self.root / result['task'])
        self.assertEqual(task['sources'][-1]['disposition'], 'considered-not-used')

    def test_duplicate_and_opposed_decisions_are_rejected(self):
        self.choices['not_used'] = [{'source': self.choices['uses'][0]['source'], 'reason': 'Another judgment.'}]
        self.write('decisions.json', self.choices)
        with self.assertRaises(ValueError): self.apply()

    def test_existing_output_is_preserved(self):
        self.apply(); original = (self.root / 'applied/tactic-application.json').read_bytes()
        with self.assertRaises(FileExistsError): self.apply()
        self.assertEqual((self.root / 'applied/tactic-application.json').read_bytes(), original)

    def test_concurrent_source_change_prevents_partial_publication(self):
        original = production_inputs._publish
        def altered(*args, **kwargs):
            self.write('production-state.md', self.text + 'Changed while building.\n')
            return original(*args, **kwargs)
        with patch.object(production_inputs, '_publish', side_effect=altered):
            with self.assertRaises(ValueError): self.apply()
        self.assertFalse((self.root / 'applied').exists())

    def test_review_questions_reach_a_real_run_without_a_verdict(self):
        result = self.apply(); run = workflow.prepare(self.root, result['task'])['run']
        workflow.handoff(self.root, run, 'synthetic operator', 'manual')
        self.write('result.txt', 'The declared condition is held.')
        candidate = workflow.capture(self.root, run, 'result.txt', 'Synthetic local text.')
        review = workflow.draft_review(self.root, run, candidate['sha256'])
        self.assertIn('declared condition', review['checks'][0]['reason'])
        self.assertEqual(review['checks'][0]['verdict'], 'not-assessed')
        self.assertEqual(review['checks'][0]['observation_indices'], [])
        self.assertEqual(review['conclusion'], '')

    def test_review_reads_prepared_source_not_later_workspace_text(self):
        result = self.apply(); run = workflow.prepare(self.root, result['task'])['run']
        workflow.handoff(self.root, run, 'synthetic operator', 'manual')
        self.write('result.txt', 'The declared condition is held.')
        candidate = workflow.capture(self.root, run, 'result.txt', 'Synthetic local text.')
        original = workflow.assert_current
        def changed_after_check(*args, **kwargs):
            snapshot = original(*args, **kwargs)
            app = c.load(self.root / result['application'])
            app['applications'][0]['review_question'] = 'Changed after freshness check.'
            self.write(result['application'], app)
            return snapshot
        with patch.object(workflow, 'assert_current', side_effect=changed_after_check):
            review = workflow.draft_review(self.root, run, candidate['sha256'])
        self.assertIn('declared condition', review['checks'][0]['reason'])
        self.assertNotIn('Changed after', review['checks'][0]['reason'])
        with self.assertRaises(ValueError): workflow.draft_review(self.root, run, candidate['sha256'])

    def test_repeated_consultation_lists_prior_uses_without_recursive_copying(self):
        result = self.apply()
        consulted = tool.consult(self.root, result['task'], 'camera', 'second-consultation')
        self.assertEqual([row['file']['path'] for row in consulted['sources']], ['production-state.md'])
        self.assertEqual(consulted['prior_applications'][0]['path'], result['application'])
        self.assertNotIn('consultation', consulted['prior_applications'][0])

    def test_prior_application_can_be_explicitly_read_in_full(self):
        result = self.apply()
        consulted = tool.consult(self.root, result['task'], 'camera', 'explicit-prior', sources=[result['application']])
        source = next(row for row in consulted['sources'] if row['file']['path'] == result['application'])
        self.assertEqual(source['text'].encode(), (self.root / result['application']).read_bytes())

    def test_input_inspection_exposes_local_tactic_sources(self):
        result = production_inputs.inspect_inputs(self.root, 'task.json')
        self.assertEqual(result['craft_lookup']['sources'], ['production-state.md'])
        self.assertEqual(result['craft_lookup']['next_actions'][0]['args']['task'], 'task.json')


if __name__ == '__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main()
