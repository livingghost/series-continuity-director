# work

The open task and the trail of tasks.

- `current.json`: the one task that is open: its goal, the steps planned, which of them are done, what comes next, and what it is blocked on. A session reads this first and continues from `next`.
- `ledger.jsonl`: every task opened, every step done, every note, every finish or abandonment, appended and never rewritten.

`scripts/work_ledger.py` writes both. Open a task before work that takes more than one step, mark each step as it is done, and finish or abandon the task when it ends.
