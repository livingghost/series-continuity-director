# Operation Logging

Operation logs record local CLI attempts and diagnostics. They are not approval, canon, selection, dispatch evidence, or a substitute for the Production receipt chain.

Project operations write under `logs/operations/<UTC-date>/<operation-id>/`. Operations without a project use the user-local SCD log directory. Logs record safe arguments, stages, related IDs, outcomes, and artifact references. Known credentials are redacted before writing.

Do not place logs inside production input hashes. Deleting diagnostic logs must not delete production evidence. A failed auxiliary log write does not erase an already preserved candidate, while inability to write required Production evidence must block an irreversible external action.
