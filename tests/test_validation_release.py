from analysis.validation.release import RELEASE_CATEGORIES, revision_retest_routes


def test_release_categories_are_prespecified_but_not_automated():
    assert len(RELEASE_CATEGORIES) == 6
    assert RELEASE_CATEGORIES[-1].startswith("Do not release")


def test_owner_retest_is_not_a_fixed_reserve():
    assert revision_retest_routes(
        affects_scratch_validation=True, further_owner_review=True
    ) == ("held_back_scratch_coder_reserve", "new_post_revision_owner_cohort")
