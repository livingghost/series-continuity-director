#!/usr/bin/env python3
"""Build a two-character shot's state chain from synthetic sources, and refuse a chain that disagrees."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import shot_chain  # noqa: E402
from protocol_contract import ZERO_SHA256, artifact_hash  # noqa: E402
from scene_plot import content_sha256  # noqa: E402

EXAMPLE = ROOT / "examples" / "mixed-viewpoint-workshop"
FIXTURES = ROOT / "examples" / "submission-gate" / "fixtures"
SCENE = "SC-WORKSHOP-01"
SHOT = "SC-WORKSHOP-01-SH01"
CAST = ("C01", "C02")
HASH_MAPS = ("species_profile_sha256_by_character", "individual_morphology_sha256_by_character",
             "identity_contract_sha256_by_character", "state_snapshot_sha256_by_character")


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def unbound(value: dict) -> dict:
    """A shot record as the author writes it, before any hash it binds is known."""
    value = copy.deepcopy(value)
    for key in HASH_MAPS:
        if key in value:
            value[key] = {cid: ZERO_SHA256 for cid in CAST}
    for key in ("scene_context_sha256", "camera_spec_sha256", "shot_projection_sha256",
                "scene_plot_sha256", "narrative_sha256"):
        if key in value:
            value[key] = ZERO_SHA256
    return value


class ShotChainTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="scd-shot-chain-")
        self.project = Path(self.temporary.name) / "project"
        made = subprocess.run([sys.executable, str(ROOT / "scripts" / "init_project.py"), "--out", str(self.project),
                               "--series-id", "FIXTURE-SERIES", "--title", "Fixture", "--json"],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(made.returncode, 0, made.stderr)
        shutil.copyfile(FIXTURES / "narrative.json", self.project / "narrative" / "narrative.json")
        plot = json.loads((FIXTURES / "scene-plot.json").read_text(encoding="utf-8"))
        plot.pop("approved")
        plot.update(scene_id=SCENE, characters=list(CAST))
        plot["realization"]["units"] = [dict(plot["realization"]["units"][0], id=SHOT)]
        plot["approved"] = {"by": "the fixture author", "at": "2026-09-23T00:00:00Z",
                            "content_sha256": content_sha256(plot)}
        save(self.project / "narrative" / "scenes" / f"{SCENE}-plot.json", plot)

        source, generated = EXAMPLE / "source", EXAMPLE / "generated"
        contracts = self.project / "state" / "contracts"
        contracts.mkdir()
        characters = {}
        for cid in CAST:
            names = {"species_profile": f"species-morphology-{cid}.json",
                     "individual_morphology": f"individual-morphology-{cid}.json",
                     "identity_contract": f"character-identity-{cid}.json"}
            for name in names.values():
                shutil.copyfile(source / name, contracts / name)
            shutil.copyfile(generated / f"character-state-schema-{cid}.json", contracts / f"state-schema-{cid}.json")
            characters[cid] = {**{key: f"state/contracts/{name}" for key, name in names.items()},
                               "state_schema": f"state/contracts/state-schema-{cid}.json"}
            shutil.copyfile(source / f"projection-request-{cid}.json",
                            self.project / "work" / f"projection-request-{cid}.json")
        shutil.copyfile(source / "events.jsonl", self.project / "state" / "events.jsonl")
        shutil.copyfile(source / "world-state-base.json", self.project / "work" / "world-state-base.json")
        shutil.copyfile(source / "scene-context-request.json", self.project / "work" / "scene-context-request.json")
        shots = self.project / "shots" / SCENE
        for kind, folder in (("camera", "shots"), ("projection", "shot-projections"), ("request", "shot-requests")):
            save(shots / f"SH01.{kind}.json", unbound(json.loads((generated / folder / f"{SHOT}.json").read_text(encoding="utf-8"))))
        self.chain = {
            "scene_plot": f"narrative/scenes/{SCENE}-plot.json", "timeline_id": "main", "story_order": 10,
            "story_time": "story:EP01-SC03-start", "world_base": "work/world-state-base.json",
            "scene_context_request": "work/scene-context-request.json", "characters": characters,
            "shots": {SHOT: {"camera": f"shots/{SCENE}/SH01.camera.json", "projection": f"shots/{SCENE}/SH01.projection.json",
                             "request": f"shots/{SCENE}/SH01.request.json",
                             "character_projections": {cid: f"work/projection-request-{cid}.json" for cid in CAST}}},
        }

    def tearDown(self):
        self.temporary.cleanup()

    def run_chain(self, chain: dict) -> dict:
        path = self.project / "work" / "chain.json"
        save(path, chain)
        try:
            return shot_chain.run(self.project, path)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    def test_the_chain_binds_every_record_of_the_shot(self):
        result = self.run_chain(self.chain)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["shots"][SHOT], {"complete": True, "errors": []})
        request = json.loads((self.project / "shots" / SCENE / "SH01.request.json").read_text(encoding="utf-8"))
        for cid in CAST:
            snapshot = json.loads((self.project / "state" / "snapshots" / f"{SCENE}-10-{cid}.json").read_text(encoding="utf-8"))
            self.assertEqual(request["state_snapshot_sha256_by_character"][cid], artifact_hash(snapshot))
        plot = json.loads((self.project / "narrative" / "scenes" / f"{SCENE}-plot.json").read_text(encoding="utf-8"))
        self.assertEqual(request["scene_plot_sha256"], plot["approved"]["content_sha256"])
        # A second run over the same sources writes the same bytes.
        before = {path: path.read_bytes() for path in (self.project / "shots").rglob("*.json")}
        self.assertTrue(self.run_chain(self.chain)["ok"])
        self.assertEqual(before, {path: path.read_bytes() for path in (self.project / "shots").rglob("*.json")})

    def test_the_scene_context_takes_the_scene_id(self):
        request = json.loads((self.project / "work" / "scene-context-request.json").read_text(encoding="utf-8"))
        save(self.project / "work" / "scene-context-request.json", dict(request, scene_context_id="SC-OTHER"))
        result = self.run_chain(self.chain)
        self.assertFalse(result["ok"])
        self.assertIn(f"a scene context takes its scene's id, {SCENE!r}", result["error"])

    def test_refusals_name_what_disagrees(self):
        cases = [
            ("a shot the plot does not declare",
             dict(self.chain, shots={"SH99": self.chain["shots"][SHOT]}), "the scene plot declares shots"),
            ("a character the plot does not name",
             dict(self.chain, characters={**self.chain["characters"], "C09": self.chain["characters"]["C01"]}),
             "the scene plot's characters are"),
            ("a shot showing a character the chain does not name",
             dict(self.chain, shots={SHOT: dict(self.chain["shots"][SHOT], character_projections={"C09": "work/x.json"})}),
             "which the chain's characters do not name"),
            ("a field the chain does not have", dict(self.chain, notes="x"), "unexpected notes"),
        ]
        for name, chain, fragment in cases:
            with self.subTest(name):
                result = self.run_chain(chain)
                self.assertFalse(result["ok"])
                self.assertIn(fragment, result["error"])

    def test_a_camera_of_another_scene_is_refused(self):
        camera = self.project / "shots" / SCENE / "SH01.camera.json"
        save(camera, dict(json.loads(camera.read_text(encoding="utf-8")), scene_id="SC-OTHER"))
        result = self.run_chain(self.chain)
        self.assertFalse(result["ok"])
        self.assertIn("names scene_id 'SC-OTHER'", result["error"])


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
