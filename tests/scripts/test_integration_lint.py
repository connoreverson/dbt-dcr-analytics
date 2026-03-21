# tests/scripts/test_integration_lint.py
from scripts.grain.integration_lint import (
    check_single_source,
    check_no_surrogate_key,
    check_no_cdm_mapping,
    check_no_intake_metadata,
)


def test_single_source_detected():
    depends_on = ["model.dcr_analytics.stg_vistareserve__reservations"]
    finding = check_single_source(depends_on)
    assert finding is not None
    assert finding["check"] == "single_source"


def test_multiple_sources_ok():
    depends_on = [
        "model.dcr_analytics.stg_vistareserve__reservations",
        "model.dcr_analytics.stg_emphasys_elite__bookings",
    ]
    finding = check_single_source(depends_on)
    assert finding is None


def test_no_surrogate_key_detected():
    columns = ["reservation_id", "park_name", "amount"]
    finding = check_no_surrogate_key(columns)
    assert finding is not None
    assert finding["check"] == "no_surrogate_key"


def test_surrogate_key_present():
    columns = ["reservation_sk", "reservation_id", "park_name"]
    finding = check_no_surrogate_key(columns)
    assert finding is None


def test_no_cdm_mapping_detected():
    meta = {}
    finding = check_no_cdm_mapping(meta)
    assert finding is not None


def test_cdm_mapping_present():
    meta = {"cdm_entity": "Reservation"}
    finding = check_no_cdm_mapping(meta)
    assert finding is None


def test_no_intake_metadata():
    meta = {}
    finding = check_no_intake_metadata(meta, is_pre_existing=False)
    assert finding is not None
    assert finding["severity"] == "warning"


def test_no_intake_metadata_pre_existing():
    meta = {}
    finding = check_no_intake_metadata(meta, is_pre_existing=True)
    assert finding is not None
    assert finding["severity"] == "info"
