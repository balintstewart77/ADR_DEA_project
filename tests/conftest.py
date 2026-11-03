import pytest


HISTORICAL_OWNER_TESTS = {
    "test_participant_documents_are_version_1_and_manifestable_without_exact_case",
    "test_candidate_0_1_controlled_artefacts_are_byte_identical",
}


def pytest_collection_modifyitems(items):
    for item in items:
        if item.path.name == "test_project_owner_redcap_candidate_0_2.py" and item.name in HISTORICAL_OWNER_TESTS:
            item.add_marker(pytest.mark.git_history)


@pytest.fixture(autouse=True)
def historical_owner_contract(request, monkeypatch):
    if request.path.name != "test_project_owner_redcap_candidate_0_2.py" or request.node.name not in HISTORICAL_OWNER_TESTS:
        return
    snapshot = request.getfixturevalue("git_snapshot")("4d4e45c9f1d92d37b328a9f279b8a660c09a5779")
    for relative in (
        "preregistration/package/06_redcap/project_owner_redcap_branching_specification_candidate_0.1.yaml",
        "tests/fixtures/project_owner_candidate_0_1_synthetic_submissions.yaml",
    ):
        path = snapshot / relative
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    monkeypatch.setattr(request.module, "ROOT", snapshot)
