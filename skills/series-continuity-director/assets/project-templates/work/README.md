# work

The open task and the trail of tasks.

- `current.json`: the one task that is open: its goal, the steps planned, which of them are done, what comes next, and what it is blocked on. A session reads this first and continues from `next`.
- `ledger.jsonl`: every task opened, every step done, every note, every finish or abandonment, appended and never rewritten.

`scripts/work_ledger.py` writes both. Open a task before work that takes more than one step, mark each step as it is done, and finish or abandon the task when it ends.

The other files here are working inputs a command reads, such as the reading applications a submission quotes and the state requests under `state-inputs/`. They carry no artifact type.

## Checkpoints

A checkpoint is a `note` or a `step` written at a boundary where loss would cost work: after a relevant instruction or correction arrives, when a draft or decision is ready and before it is presented, before a switch of task, and before and after an external operation such as a dispatch. It records what was decided, where it was written, and the next safe operation; a question that waits on the author is recorded with `block`. Written is not saved: read the files back before a cumulative reply claims them. A checkpoint is neither an accepted take nor an approval nor permission to send.

## Resuming

Resume in this order: find the project, read the open task and the trail, read the applicable records for the next operation, compare any new instruction with what is saved, then take the next safe operation. Do not repeat an answered question, revive a rejected idea, resend a completed submission, or treat a pending proposal as approved. Report what is saved by its actual guarantee: a local checkpoint read back, an export verified, a remote write with an unknown outcome, or a stale trail. When writing is unavailable, say what is unsaved and hand over a recoverable export instead of continuing as if it were safe.
