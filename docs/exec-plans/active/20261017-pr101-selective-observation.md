# PR #101: selective Linux observation

## Goal

Integrate current main, review and fix selective AX/screenshot collection and cache semantics, verify on real GTK/AT-SPI and through the current JS entry, then push follow-up commits to the original PR. Do not merge.

## Scope and decisions

- Preserve legacy/default calls. Explicit Linux include_ax/include_screenshot flags select collection; at least one channel is required.
- Retain upstream bounded-focus, hidden-node and action-read-back behavior. Screenshot-only observation invalidates previous AX indexes and aliases; AX-only refresh restores usable indexes.
- Use real GTK in an isolated container/Xvfb/D-Bus session, without a desktop VM or personal applications. No Wayland or whole-task performance claim.
- Explain the user's screenshot/token concern: JS already suppresses automatic action read-back and getAXState image emission, while native collection can still be wasted. This Linux-only PR enables explicit selection; cross-platform support and unchanged-image suppression are distinct follow-up work, not silently added here.

## Progress

- [x] Merge current main and retain both test groups, focus handling and release entries.
- [x] Review protocol, collection paths, cache aliases and JS compatibility; fix older aliases surviving PID replacement.
- [x] Add repeatable real GTK and JS/native tests for all observation modes, stale-index refusal and recovery.
- [x] Run relevant suites/builds, synchronize docs and existing history, clean up the test container.
- [x] Synchronize remotes and prepare tested follow-up commits for #101.

## Validation

Check full/AX-only/screenshot-only results and skipped production collection helpers on real GTK; current geometry, alias invalidation across observations/windows/processes, explicit AX recovery and real actions; both JS session adapters; error/default compatibility; existing focus, hidden-node and read-back smoke. Run Linux Go/Python, Node, cross-build/vet, docs and syntax checks.

## Outcome

- Integrated main `7cb8bb7`, preserving the original contribution and current hidden-details, bounded-focus and action-read-back behavior.
- A regression first failed because an older query alias retained AX indexes after PID replacement; invalidation now clears every snapshot for both previous/new PIDs while preserving unrelated apps.
- JS rejects both channels disabled before native RPC; Persistent and Worker parameter/default/error behavior passed.
- Python 35/35, Linux Go 30/30 and Node 44/44 passed. Linux ARM64/AMD64 builds, targeted vet, syntax, docs and whitespace checks passed.
- Real GTK 3/AT-SPI on Debian 12 ARM64 in private Xvfb/D-Bus passed production-helper collection checks, valid PNG output, Unicode selection, stale name/PID indexes refused, coordinate click and AX recovery. Worker JS/native/GTK and existing default read-back, focus and hidden-details smokes passed.
- Temporary container and build artifacts removed. No desktop VM, Wayland/other-toolkit performance claim or version bump.
- User's unchanged-image concern is documented separately: this PR selects collection on Linux; exact image comparison, cross-platform support, first/reset/forced output and session/window scoping remain follow-up design items in the debt tracker. No automatic deduplication is claimed.

## Cross-platform extension (requested follow-up)

The user explicitly requested macOS and Windows parity across CLI/MCP/JS. The earlier Linux-only scope is superseded for selective collection; automatic image deduplication remains separate.

- [ ] Add shared macOS observation options, real/fixture collection gates, schema/dispatcher, cache/query-index invalidation and app-agent forwarding.
- [ ] Add Windows Go/PowerShell selection, request/schema/cache behavior and executable bridge tests.
- [ ] Expose matching snapshot --include-ax/--include-screenshot true|false flags on all platforms; preserve legacy defaults.
- [ ] Make explicit AX-only observations reject screenshot-coordinate input on all platforms, while preserving element actions.
- [ ] Validate macOS with a normally signed release and isolated real window; Linux with real GTK; Windows with Go/PowerShell tests and builds, stating any unavailable Windows desktop validation.
- [ ] Update current docs/history/PR around the final cross-platform behavior, sync remotes, push.

### Hosted Windows validation

Local native/GTK/macOS checks passed. A focused read-only-permissions Windows Actions job is being added to run a disposable WinForms fixture against the actual Windows binary. It covers explicit channels, stale indexes, real UIA set_value, coordinate refusal and normal/1x1/minimized/cloaked image handling. This provides the Windows desktop verification required by RELIABILITY without starting a local VM. Until the hosted job passes, Windows UIA validation is pending and is not claimed.
