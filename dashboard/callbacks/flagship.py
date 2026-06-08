"""Deprecated cross-domain linked dataset callbacks.

The old Dataset Demand breakdown used the stale ADR UK flagship dataset list.
Recreate this view from the deterministic record-linkage layer before exposing
it again.
"""


def register(app):
    """No-op callback registration retained for the existing app bootstrap."""
    return
