## [2026-10-15 20:23] | Task: Add opt-in selective Linux observation

### Execution Context
- Agent: Codex
- Runtime: Linux development environment

### User Request
Offer cheaper explicit observation as a compatibility-preserving option, following the existing lightweight app binding approach.

### Changes
- Add optional Linux `get_app_state` booleans `include_ax` and `include_screenshot`, both defaulting to true.
- Skip AX tree, focus and selection collection for screenshot-only reads; skip capture/PNG encoding for AX-only reads.
- Forward optional REPL `includeAX` and `includeScreenshot` without changing legacy calls.
- Explicitly invalidate prior AX indexes and their aliases after screenshot-only reads, retain current window geometry for coordinate actions, and report the invalidation.
- Add Python collection-path tests, Go protocol/cache/schema tests, Node compatibility tests, usage documentation and release notes.

### Design Intent
Changing `getScreenshot()` defaults would also change its implicit index refresh. Keep existing behavior and make selective observation opt-in. A screenshot cannot validate old indexes, including after a window/process switch, so clear them rather than guessing from matching titles. A fresh AX observation restores indexes.

### Validation
- Linux Go suite and Python bridge unit tests.
- Node REPL regression tests, including unchanged legacy request arguments.
- REPL tests: 23 passed. Full Node suite: 36/37 passed; the staged npm packaging test requires macOS `lipo` and fails identically on the unmodified base checkout on Linux.
- Documentation and whitespace checks.
- No live desktop timing, macOS runtime or Windows runtime validation is claimed. This change is independent of the action read-back fix and does not change input delivery or bridge process lifetime.

### Files Modified
- `apps/OpenComputerUseLinux/main.go`
- `apps/OpenComputerUseLinux/main_test.go`
- `apps/OpenComputerUseLinux/runtime.py`
- `apps/OpenComputerUseLinux/runtime_test.py`
- `scripts/node-repl/open-computer-use-repl.mjs`
- `scripts/node-repl/open-computer-use-repl.test.mjs`
- `skills/open-computer-use/references/usage.md`
- `docs/ARCHITECTURE.md`
- `docs/releases/feature-release-notes.md`
