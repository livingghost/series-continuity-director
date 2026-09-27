# Production Graph

A production graph is a planning view over existing SCD tasks and runs. It does not own approvals, reservations, candidates, selection, or canon.

Use it when several stages depend on one another. Each node declares its operation, dependencies, external effect class, required authority scopes, and cost status. External-write nodes without explicit authority scopes are blocked. Unknown cost remains unknown rather than becoming zero.

`production_graph.py check` reports currently ready nodes from the declared states. Starting or recovering a real remote operation still goes through Production authority and dispatch.
