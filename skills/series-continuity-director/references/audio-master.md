# Audio Master

Treat source integrity, encoded-stream preservation, decoded-sample preservation, a single controlled lossy encode, and an approved mix as different claims.

Use `audio_master.py check` on actual source and output bytes. `encoded-stream-preserve` allows remux only and compares encoded essence. `decoded-samples-preserve` compares the decoded sample sequence. `single-encode-from-master` checks the SCD-controlled processing graph and never infers encode history before the declared source. `approved-mix` records that the output is intentionally different.

A codec name alone never proves that audio was encoded once or that it is unchanged. An unchanged source-file hash does not prove the final output audio is unchanged.
