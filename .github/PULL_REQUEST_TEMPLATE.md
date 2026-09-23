## Observable change

Describe which real file, field, setting, exact submitted text, evidence requirement, or review observation changes.

## Deletion/contrast test

Explain why the new label or distinction cannot be removed without changing the submission package. Include a minimal contrast pair when applicable.

## Evidence

- [ ] Target-specific facts include a dated official source or direct observation.
- [ ] Behavioral claims include a real run record and all returned variants.
- [ ] Documentation-only examples say `not run`.
- [ ] Exact submitted text contains no internal IDs or unresolved references.

## Validation

Run from the repository root. The first regenerates what the second checks, and
`validate_skill.py` runs every protocol validator, host manifest check, and smoke
test. `build_release.py` runs `validate_skill.py` once on the staged tree, so the
last item also covers the second. Use `python3` where `python` is not on
the path, which is the default on macOS and on Debian and Ubuntu.

- [ ] `python skills/series-continuity-director/scripts/build_derived.py`
- [ ] `python skills/series-continuity-director/scripts/validate_skill.py`
- [ ] `python skills/series-continuity-director/scripts/build_release.py --out dist/series-continuity-director-<version>.zip --reports-dir dist/reports`
