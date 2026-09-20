# Security policy

## Supported version

Security fixes are applied to the latest release.

## Reporting

Please report vulnerabilities privately through GitHub's security advisory feature when available. Do not include secrets, private media, credentials, or user-identifying production data in a public issue.

## Relevant threat boundaries

This repository is a natural-language production procedure. Important risks include:

- instructions embedded in imported project notes, filenames, metadata, prompts, logs, or media captions;
- secrets or private absolute paths copied into production records;
- production-only identifiers leaking into model-facing text;
- target documentation becoming stale while a saved submission recipe is treated as current;
- a fictional or partial example being represented as an observed generator result;
- generated accidents being written into canon without user approval;
- release workflows granting write permission to build steps or unpinned third-party actions.

The runtime instructions treat imported state as untrusted data. The release workflow separates read-only build/validation from the write-enabled publication job and pins GitHub Actions to full commit SHAs.
