"""Build explicit synthetic submission evidence for tests and executable examples."""
from __future__ import annotations

import copy
from pathlib import Path

import execution_contract as c
from protocol_contract import finalize_artifact, validate_artifact
from reading_fixtures import fixture_reading

ROOT = Path(__file__).resolve().parents[1]


def _save(root: Path, path: str, value) -> dict:
    raw = value.encode('utf-8') if isinstance(value, str) else c.encoded(value)
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return {'path': path, 'sha256': c.digest(raw)}


def camera_request(root: Path, scene: str, shot: str, characters: list[str]) -> tuple[dict, dict]:
    """Create complete public artifacts with explicit synthetic reference hashes."""
    templates = ROOT / 'protocols/viewpoint/templates'
    camera = c.load(templates / 'shot-camera-spec.template.json')
    camera.update(scene_id=scene, shot_id=shot, focal_character_ids=characters,
                  visible_subjects=characters,
                  visible_body_regions={key: ['full body'] for key in characters},
                  prop_ownership={},
                  state_snapshot_sha256_by_character={key: c.content_id({'synthetic_state': key}) for key in characters})
    camera = finalize_artifact(camera)
    request = c.load(templates / 'shot-request.template.json')
    request.update(request_id='SR-' + shot, scene_id=scene, shot_id=shot,
                   camera_spec_sha256=camera['camera_spec_sha256'])
    for key in ('species_profile_sha256_by_character', 'individual_morphology_sha256_by_character',
                'identity_contract_sha256_by_character', 'state_snapshot_sha256_by_character'):
        request[key] = {character: c.content_id({'synthetic': key, 'character': character}) for character in characters}
    request['state_snapshot_sha256_by_character'] = camera['state_snapshot_sha256_by_character']
    for key in ('scene_context_sha256', 'shot_projection_sha256', 'scene_plot_sha256', 'narrative_sha256'):
        request[key] = c.content_id({'synthetic': key, 'scene': scene})
    request['visible_morphology_feature_refs_by_character'] = {key: ['body.core'] for key in characters}
    request['visible_identity_obligations'] = [key + ' silhouette' for key in characters]
    request['visible_state_obligations'] = ['Inspect the explicitly declared fixture state.']
    request['selected_reference_candidates'] = []
    request = finalize_artifact(request)
    for value in (camera, request):
        report = validate_artifact(value)
        if not report['ok']:
            raise ValueError('invalid synthetic public artifact: ' + '; '.join(report['errors']))
    prefix = 'fixtures/contracts/' + c.content_id({'scene': scene, 'shot': shot, 'characters': characters})[:16]
    return _save(root, prefix + '/camera.json', camera), _save(root, prefix + '/request.json', request)


def current_submission(value, root: Path, profiles: Path) -> object:
    """Supply independent declared evidence while retaining each tested field."""
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    result = copy.deepcopy(value)
    result['route_reading'] = fixture_reading(route='media', project=root)
    basis = {**_save(root, 'fixtures/submission-basis.txt',
        'Synthetic tests declare one-off subjects and inspect mechanical request constraints.\n'), 'locator': 'whole'}
    from submission_gate import load_profile
    profile = load_profile(str(result.get('target') or ''), profiles)
    kinds = (profile or {}).get('media_kind', [])
    purpose = 'video' if 'video' in kinds or 'video-with-audio' in kinds else 'image'
    characters = result.get('characters')
    characters = characters if isinstance(characters, list) and all(isinstance(x, str) for x in characters) else ['C01']
    camera, request = None, None
    if result.get('kind') == 'shot':
        scene = result.get('scene_id', 'SUBMISSION-GATE-FIXTURE')
        result['scene_id'] = scene
        shot = result.get('shot_id', 'SYNTHETIC-SHOT')
        camera, request = camera_request(root, scene, shot, characters)
    visual = {'purpose': purpose, 'basis': basis,
              'subjects': {key: {'character_id': key, 'continuity': 'one-off', 'identity_refs': []} for key in characters},
              'shot_camera': camera, 'shot_request': request, 'reference_activation': None}
    result['visual_continuity'] = visual
    result['visual_continuity_sha256'] = c.content_id(visual)
    return result
