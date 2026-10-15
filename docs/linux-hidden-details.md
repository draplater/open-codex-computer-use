# Add opt-in lightweight details for hidden Linux nodes

With `OPEN_COMPUTER_USE_LINUX_LIGHTWEIGHT_HIDDEN=1`, snapshot rendering retains every node, index, runtime path, role and name, but skips geometry/value/action/toolkit/automation-ID reads for nodes explicitly reported as non-SHOWING by AT-SPI. Such rows are marked `[hidden details omitted]`.

This option is disabled by default. Unknown or failing state queries keep full details. The renderer never prunes a hidden parent's descendants: visible menu children retain their full properties and original numbering. Geometry alone is not evidence that a node is hidden, so off-window/negative coordinates are not used as a filtering rule.

Validation: Python bridge tests (13 passed), including skipped property calls, unchanged default output, unknown state fallback, visible children of hidden parents and index/path preservation. No live desktop benchmark or claim that all offscreen nodes are optimized.
