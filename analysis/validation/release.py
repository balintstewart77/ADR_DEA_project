"""Non-mechanical v0.14 release-category and retest-route scaffolding."""

from __future__ import annotations

RELEASE_CATEGORIES = (
    "Proceed with v1 release",
    "Release with caveats",
    "Revise prompt or model and retest",
    "Revise taxonomy and retest",
    "Report a register limitation rather than model failure",
    "Do not release the affected LLM-derived output in its current form",
)


def revision_retest_routes(
    *, affects_scratch_validation: bool, further_owner_review: bool
) -> tuple[str, ...]:
    """Keep scratch reserves and post-revision owner recruitment distinct."""

    routes: list[str] = []
    if affects_scratch_validation:
        routes.append("held_back_scratch_coder_reserve")
    if further_owner_review:
        routes.append("new_post_revision_owner_cohort")
    return tuple(routes)
