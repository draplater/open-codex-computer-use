# Bound Linux focus lookup and reuse its result

Agent: Codex; runtime: Linux.

User request: submit scoped improvements for the remaining Linux performance paths.

Linux snapshots currently enumerate the app/window twice and recursively locate the focused element separately for its summary and selected text. This PR resolves focus once in the window already selected for the snapshot and applies the snapshot's node/depth budgets. If traversal ends before focus is found, the returned text explicitly reports an incomplete search rather than claiming focus is absent.

Full AX tree/index and screenshot behavior is unchanged. The focus summary and selection come from the same element. A very deep or large focus search may now return incomplete metadata; callers can explicitly raise the existing tree budgets. This is a cooperative traversal budget, not a way to interrupt a blocking AT-SPI call.

Validation: Python bridge tests (14 passed), including shared focus lookup, node/depth bounds, complete absence and explicit truncation reporting. No live desktop benchmark is claimed.

Changed files: `apps/OpenComputerUseLinux/runtime.py`, `apps/OpenComputerUseLinux/runtime_test.py`, `docs/linux-bounded-focus.md`, architecture and release notes.
