# Board Layout

Keep planning boards, model-facing reference carriers, and delivery pages distinct. Similar-looking artifacts may have different authority and different risks.

`board_layout.py` validates panel bounds, source hashes, and annotation scope. A missing source is `planned-not-observed`; it is not a generated panel. For model-facing boards, annotations must be intentionally included rather than assumed harmless.

The SVG builder is deterministic and preserves source relationships. It is a carrier and review artifact, not proof that a model consumed any referenced image.
