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
