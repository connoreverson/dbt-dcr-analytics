"""Unit tests for scripts._core.selector — layer detection logic."""
import pytest

from scripts._core.selector import determine_layer


def testdetermine_layer_staging():
    assert determine_layer("stg_vistareserve__reservations") == "staging"


def testdetermine_layer_integration():
    assert determine_layer("int_parks") == "integration"


def testdetermine_layer_fact():
    assert determine_layer("fct_reservations") == "marts"


def testdetermine_layer_dimension():
    assert determine_layer("dim_parks") == "marts"


def testdetermine_layer_report():
    assert determine_layer("rpt_park_revenue_summary") == "marts"


def testdetermine_layer_base():
    assert determine_layer("base_vistareserve__deduped") == "base"


def testdetermine_layer_unknown():
    assert determine_layer("some_random_model") == "unknown"
