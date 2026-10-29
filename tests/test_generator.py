from src.hiringflow.generator import build_dataset, validate_dataset


def test_fixed_seed_is_reproducible():
    first = build_dataset("starter", 20261022)
    second = build_dataset("starter", 20261022)
    assert set(first) == set(second)
    for name in first:
        assert first[name].equals(second[name]), name


def test_starter_volume_and_required_entities():
    tables = build_dataset("starter", 20261022)
    assert len(tables["requisitions"]) == 12
    assert len(tables["candidates"]) == 120
    assert len(tables["applications"]) == 190
    assert len(tables["interviews"]) == 60
    for name in ["hiring_managers", "requisitions", "candidates", "applications", "skill_requirements", "interview_panels", "availability", "interviews", "scorecards", "offers", "approvals", "ground_truth"]:
        assert name in tables


def test_ground_truth_contains_five_required_exception_types():
    tables = build_dataset("starter", 20261022)
    found = set(tables["ground_truth"]["issue_type"])
    assert found == {
        "ADVANCED_WITHOUT_REQUIRED_REVIEW",
        "INTERVIEWER_DOUBLE_BOOKED",
        "OFFER_EXCEEDS_BAND",
        "WITHDRAWN_CANDIDATE_STILL_SCHEDULED",
        "IRRELEVANT_EVALUATION_CRITERION",
    }


def test_structural_keys_and_score_reconciliation():
    tables = build_dataset("starter", 20261022)
    checks = validate_dataset(tables)
    structural = [c for c in checks if c["check"] in {"PRIMARY_KEY_UNIQUENESS", "FOREIGN_KEY_INTEGRITY", "COMPENSATION_BAND_ARITHMETIC", "SCORE_RECONCILIATION", "ALLOWED_STAGE_ENUM"}]
    assert all(c["status"] == "PASS" for c in structural), structural
