"""Resolve local input witnesses from the selected project and this skill."""
from pathlib import Path
from input_evidence import InputEvidence


def reader(root:Path|None,*,snapshots:dict|None=None,live:bool=True)->InputEvidence:
    return InputEvidence(root,snapshots=snapshots,live=live,named_roots={'@skill':Path(__file__).resolve().parents[1]})
