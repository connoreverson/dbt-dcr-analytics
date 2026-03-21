"""Unit tests for scripts._core.selector — layer detection logic."""
import pytest

from scripts._core.selector import _determine_layer


def test_determine_layer_staging():
    assert _determine_layer("stg_vistareserve__reservations") == "staging"


def test_determine_layer_integration():
    assert _determine_layer("int_parks") == "integration"


def test_determine_layer_fact():
    assert _determine_layer("fct_reservations") == "marts"


def test_determine_layer_dimension():
    assert _determine_layer("dim_parks") == "marts"


def test_determine_layer_report():
    assert _determine_layer("rpt_park_revenue_summary") == "marts"


def test_determine_layer_base():
    assert _determine_layer("base_vistareserve__deduped") == "base"


def test_determine_layer_unknown():
    assert _determine_layer("some_random_model") == "unknown"
