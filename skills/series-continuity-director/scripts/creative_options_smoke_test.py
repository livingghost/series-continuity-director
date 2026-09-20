#!/usr/bin/env python3
"""Synthetic source-bound alternatives; not a writing-quality benchmark."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import creative_options as o
import execution_contract as c


class CreativeOptionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'source.txt').write_text('An unpeopled abstract sequence with an intentional hold.')
        (self.root / 'plan.txt').write_text('Hold the established interval. No character or dramatic change is needed.')
        (self.root / 'author-choice.txt').write_text('SYNTHETIC TEST CHOICE, NOT HUMAN CONSENT.')
        (self.root / 'canon.txt').write_text('UNCHANGED ACCEPTED RECORD')
        self.spec = {'purpose': 'Explore a treatment without adopting it.',
                     'intent': {'durable': 'Preserve the declared effect.', 'focus': 'Compare only this treatment.'},
                     'sources': [{'id': 'premise', 'path': 'source.txt', 'role': 'authorial-intent'}],
                     'alternatives': [{'id': 'hold', 'title': 'Intentional hold', 'plan': 'plan.txt',
                                       'rationale': 'An intentional hold is a valid treatment.', 'preserves': ['Established condition'],
                                       'changes': [], 'uncertainties': [],
                                       'trace': [{'source': 'premise', 'locator': 'whole', 'target': 'whole',
                                                  'treatment': 'hold', 'reason': 'No invented event.'}]}]}

    def prepare(self):
        (self.root / 'options.json').write_bytes(c.encoded(self.spec))
        return o.prepare(self.root, 'options.json')['workspace']

    def choose(self, identifier, alternative='hold'):
        return o.select(self.root, identifier, alternative, 'synthetic test operator',
                        'Select a planning artifact only.', 'author-choice.txt')

    def test_one_no_cast_no_change_option_is_valid(self):
        identifier = self.prepare()
        self.assertTrue(o.status(self.root, identifier)['current'])
        self.assertIsNone(o.status(self.root, identifier)['selection'])

    def test_no_source_requirement_for_an_original_abstract_plan(self):
        self.spec['sources'] = []
        self.spec['alternatives'][0]['trace'] = []
        self.assertTrue(o.status(self.root, self.prepare())['current'])

    def test_many_options_have_no_genre_based_count_cap(self):
        self.spec['alternatives'] = [{**copy.deepcopy(self.spec['alternatives'][0]), 'id': str(i)} for i in range(17)]
        self.assertEqual(len(o.status(self.root, self.prepare())['spec']['alternatives']), 17)

    def test_selection_does_not_modify_canon_or_sources(self):
        identifier = self.prepare()
        before = {p: p.read_bytes() for p in self.root.iterdir() if p.is_file() and not p.name.startswith('.')}
        result = self.choose(identifier)
        self.assertFalse(result['canonical_changes'])
        self.assertEqual(Path(result['plan_object']).read_bytes(), (self.root / 'plan.txt').read_bytes())
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertFalse((self.root / 'production').exists())

    def test_repeated_same_choice_is_idempotent(self):
        identifier = self.prepare()
        a, b = self.choose(identifier), self.choose(identifier)
        self.assertEqual(a['selection_sha256'], b['selection_sha256'])

    def test_changed_source_marks_stale_and_blocks_choice(self):
        identifier = self.prepare()
        (self.root / 'source.txt').write_text('Changed intention.')
        self.assertFalse(o.status(self.root, identifier)['current'])
        with self.assertRaisesRegex(ValueError, 'source content changed'):
            self.choose(identifier)

    def test_changed_plan_marks_stale(self):
        identifier = self.prepare()
        self.choose(identifier)
        (self.root / 'plan.txt').write_text('An unreviewed change.')
        self.assertFalse(o.status(self.root, identifier)['current'])

    def test_deleted_source_is_not_silently_ignored(self):
        identifier = self.prepare()
        (self.root / 'source.txt').unlink()
        self.assertFalse(o.status(self.root, identifier)['current'])

    def test_snapshot_tampering_refused(self):
        identifier = self.prepare()
        folder = o.directory(self.root, identifier)
        first = next((folder / 'objects').iterdir())
        first.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            o.status(self.root, identifier)

    def test_unknown_choice_cannot_be_added_at_selection_time(self):
        identifier = self.prepare()
        with self.assertRaises(ValueError):
            self.choose(identifier, 'invented')

    def test_missing_selection_evidence_refused(self):
        identifier = self.prepare()
        (self.root / 'author-choice.txt').unlink()
        with self.assertRaises(ValueError):
            self.choose(identifier)

    def test_empty_plan_refused_before_publication(self):
        (self.root / 'plan.txt').write_text(' ')
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse((self.root / 'creative-options').exists())

    def test_invalid_trace_refused_before_publication(self):
        self.spec['alternatives'][0]['trace'][0]['source'] = 'missing'
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse((self.root / 'creative-options').exists())

    def test_duplicate_ids_refused(self):
        self.spec['alternatives'].append(copy.deepcopy(self.spec['alternatives'][0]))
        with self.assertRaises(ValueError):
            self.prepare()

    def test_path_escape_refused(self):
        self.spec['alternatives'][0]['plan'] = '../outside'
        with self.assertRaises(ValueError):
            self.prepare()

    def test_source_symlink_refused(self):
        (self.root / 'alias').symlink_to(self.root / 'source.txt')
        self.spec['sources'][0]['path'] = 'alias'
        with self.assertRaises(ValueError):
            self.prepare()

    def test_workspace_id_does_not_accept_path(self):
        with self.assertRaises(ValueError):
            o.status(self.root, '../outside')

    def test_failed_atomic_publication_leaves_no_partial_workspace(self):
        (self.root / 'options.json').write_bytes(c.encoded(self.spec))
        with patch.object(o.os, 'rename', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                o.prepare(self.root, 'options.json')
        self.assertEqual(list((self.root / 'creative-options').iterdir()), [])

    def test_export_escapes_authored_plan_and_reports_staleness(self):
        (self.root / 'plan.txt').write_text('</pre><script>bad()</script>')
        identifier = self.prepare()
        (self.root / 'source.txt').write_text('Changed')
        result = o.export(self.root, identifier, 'reviews/options')
        output = (Path(result['output']) / 'index.html').read_text()
        self.assertIn('STALE', output)
        self.assertNotIn('<script>', output)
        self.assertIn('&lt;script&gt;', output)


if __name__ == '__main__':
    import io
    import json
    buffer = io.StringIO()
    result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(__import__('sys').modules[__name__]))
    errors = [str(test) + ': ' + detail for test, detail in result.failures + result.errors]
    print(json.dumps({'ok': result.wasSuccessful(), 'checks': result.testsRun,
                      'passed': result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
                      'skipped': len(result.skipped), 'errors': errors,
                      'scope': 'constructed correctness tests; no model-quality claim',
                      'details': buffer.getvalue()}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
