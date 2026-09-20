#!/usr/bin/env python3
"""Exercise responsibility boundaries with current synthetic public data.

These checks concern data, approval flags, scoped state and explicit inputs.
They do not judge a work's meaning, prove consent or call a generation service.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import integration_contract as interchange
import protocol_contract as contract
import protocol_exchange as exchange
import temporal_state

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'examples/protocol-exchange/fixtures'


def fixture(kind: str) -> dict:
    return contract.load_json(FIXTURES / (kind + '.json'))


def event(*, approved: bool, scene: str | None = None) -> dict:
    value = fixture('state-event')
    value.update(
        event_id='EV-LAMP', timeline_id='main', event_scope='environment-state',
        targets=['room'], effective_order=2, effective_from='story:2',
        canon_status='approved' if approved else 'proposed', atomic=False,
        preconditions=[], supersedes_event_ids=[], occurrence='offscreen',
        cause={'type': 'synthetic fixture', 'reference': 'not user approval'},
        evidence=[{'type': 'synthetic fixture', 'reference': 'not user approval'}],
        changes=[{'entity_type': 'environment', 'entity_id': 'room', 'path': '/light',
                  'operation': 'set', 'value': 'bright',
                  'persistence': 'scene-local' if scene else 'persistent-until-superseded'}],
    )
    value.pop('scene_context_id', None)
    if scene:
        value['scene_context_id'] = scene
    return value


def world(events: list[dict], *, scene: str = 'A', order: int = 5) -> dict:
    return temporal_state.resolve_world(
        base_state={'environments': {'room': {'light': 'dim'}}}, events=events,
        processes=[], timeline_id='main', story_order=order, story_time=f'story:{order}',
        snapshot_id=f'world-{scene}-{order}', scene_context_id=scene,
    )


class LayerBoundaries(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='responsibility-boundaries-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.caps = interchange.load_capabilities(ROOT)

    def save(self, relative: str, value: dict) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(exchange.encoded(value))
        return path

    def envelope(self, data: dict) -> dict:
        raw = exchange.encoded(data)
        (self.root / 'artifact.json').write_bytes(raw)
        profile = interchange.find_interface(self.caps, 'produces', 'shot-request')
        self.assertIsNotNone(profile)
        return interchange.finalize({
            'artifact_type': 'interchange-envelope', 'envelope_id': 'IE-fixture',
            'contract_profile': profile['profile'], 'profile_sha256': profile['profile_sha256'],
            'origin': {'capability_manifest_sha256': self.caps['manifest_sha256']},
            'payload': {'artifact_type': data['artifact_type'],
                        'artifact_id': interchange.payload_identity(data),
                        'media_type': 'application/json', 'path': 'artifact.json',
                        'sha256': hashlib.sha256(raw).hexdigest()},
            'required_features': profile['required_features'], 'optional_features': [],
            'extensions': {},
        }, 'envelope_sha256')

    def test_valid_proposal_is_not_an_approved_event(self):
        proposal = event(approved=False)
        self.assertTrue(contract.validate_artifact(proposal)['ok'])
        self.save('state/event.json', proposal)
        exchange.export(self.root, 'state/event.json', 'outgoing')
        report = exchange.verify_bundle(self.root, 'outgoing')
        self.assertFalse(report['canonical_adoption'])
        received = contract.load_json(self.root / 'outgoing/artifact.json')
        self.assertEqual(received['canon_status'], 'proposed')
        self.assertEqual(world([received])['entities']['environments']['room']['light'], 'dim')

    def test_approved_event_and_its_story_range_are_effective(self):
        approved = event(approved=True)
        self.assertEqual(world([approved], order=1)['entities']['environments']['room']['light'], 'dim')
        self.assertEqual(world([approved], order=5)['entities']['environments']['room']['light'], 'bright')

    def test_scene_scope_is_not_storage_scope(self):
        scoped = event(approved=True, scene='A')
        self.save('directory-one/event.json', scoped)
        self.save('directory-two/event.json', scoped)
        for relative in ('directory-one/event.json', 'directory-two/event.json'):
            loaded = contract.load_json(self.root / relative)
            self.assertEqual(world([loaded], scene='A')['entities']['environments']['room']['light'], 'bright')
            self.assertEqual(world([loaded], scene='B')['entities']['environments']['room']['light'], 'dim')

    def test_presenting_a_later_state_does_not_advance_an_earlier_one(self):
        approved = event(approved=True)
        self.assertEqual([world([approved], order=i)['entities']['environments']['room']['light']
                          for i in (5, 1, 6)], ['bright', 'dim', 'bright'])

    def test_content_identity_survives_relocation_without_adding_authority(self):
        self.save('authored.json', fixture('character-identity-contract'))
        exchange.export(self.root, 'authored.json', 'bundle-a')
        shutil.copytree(self.root / 'bundle-a', self.root / 'other-workspace/bundle-b')
        a = exchange.verify_bundle(self.root, 'bundle-a')
        b = exchange.verify_bundle(self.root / 'other-workspace', 'bundle-b')
        self.assertEqual(a, b)
        self.assertFalse(b['canonical_adoption'])
        self.assertFalse(b['referenced_media_verified'])

    def test_export_and_verification_leave_owning_records_untouched(self):
        originals = {
            'narrative/narrative.json': b'{"test_note":"synthetic owner sentinel"}\n',
            'state/events.jsonl': b'\n', 'asset-registry.md': b'# Synthetic registry\n',
            'production-state.md': b'# Synthetic observations\n',
        }
        for name, raw in originals.items():
            p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
        self.save('authored.json', fixture('shot-request'))
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('urllib.request.urlopen', side_effect=AssertionError('unexpected network retrieval')):
            exchange.export(self.root, 'authored.json', 'outgoing')
            report = exchange.verify_bundle(self.root, 'outgoing')
        for name, raw in before.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
        added = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()} - {p.as_posix() for p in before}
        self.assertEqual(added, {'outgoing/artifact.json', 'outgoing/manifest.json', 'outgoing/contract.json'})
        self.assertFalse(report['canonical_adoption'])

    def test_reference_source_is_provenance_not_an_implicit_fetch(self):
        data = fixture('state-aware-reference-binding')
        data['source'] = {'kind': 'supplied-file', 'reference_id': 'unacquired',
                          'resolved_path': 'https://example.invalid/not-retrieved.png',
                          'media_type': 'image/png', 'sha256': 'b' * 64}
        data = contract.finalize_artifact(data)
        self.save('reference.json', data)
        with patch('urllib.request.urlopen', side_effect=AssertionError('unexpected network retrieval')):
            exchange.export(self.root, 'reference.json', 'bundle')
            report = exchange.verify_bundle(self.root, 'bundle')
        self.assertFalse(report['referenced_media_verified'])
        self.assertFalse(report['canonical_adoption'])

    def test_equal_declarations_do_not_choose_the_operation_direction(self):
        value = self.envelope(fixture('shot-request'))
        for direction in ('produces', 'consumes'):
            report = interchange.validate_envelope(value, capabilities=self.caps, direction=direction,
                declaration=self.caps if direction == 'consumes' else None, payload_root=self.root)
            self.assertTrue(report['ok'], report)
            self.assertEqual(report['interface_role'], direction)
            self.assertFalse(report['canonical_adoption'])

    def test_missing_operation_support_is_reported_as_a_profile_issue(self):
        value = self.envelope(fixture('shot-request'))
        receiver = copy.deepcopy(self.caps)
        receiver['interfaces']['consumes'] = []
        receiver = interchange.finalize(receiver, 'manifest_sha256')
        report = interchange.validate_envelope(value, capabilities=receiver, direction='consumes',
            declaration=self.caps, payload_root=self.root)
        self.assertFalse(report['ok'])
        self.assertIn('capability declaration does not support the requested operation/profile', report['errors'])

    def test_bound_path_resolves_relative_to_the_declared_root(self):
        self.save('evidence/input.json', {'test_note': 'synthetic fixture'})
        self.assertEqual(interchange.contained_path(self.root, 'evidence/input.json'), self.root / 'evidence/input.json')
        with self.assertRaises(ValueError):
            interchange.contained_path(self.root, '../outside.json')

    def test_registered_schema_references_do_not_trigger_network_retrieval(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('unexpected network retrieval')):
            with self.assertRaises(ValueError):
                contract._resolve_ref('https://example.invalid/schema.json', {})

    def test_cli_reports_the_declaration_it_actually_validated(self):
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_integration.py')],
            cwd=self.root, env=env, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['declaration_validation']['ok'])
        self.assertTrue(report['self_test']['ok'])


if __name__ == '__main__':
    buffer = io.StringIO()
    result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(LayerBoundaries))
    sys.stderr.write(buffer.getvalue())
    print(json.dumps({'ok': result.wasSuccessful(), 'tests': result.testsRun,
                      'failures': len(result.failures), 'errors': len(result.errors),
                      'skipped': len(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
