from __future__ import annotations

from scripts.preflight.checks import CheckResult, summarize_results


def test_check_result_pass():
    r = CheckResult(name="Compile", passed=True)
    assert r.passed
    assert r.critical is False


def test_check_result_critical_failure():
    r = CheckResult(name="Build", passed=False, critical=True, message="SQL error")
    assert not r.passed
    assert r.critical


def test_summarize_all_pass():
    results = [
        CheckResult(name="Compile", passed=True),
        CheckResult(name="Build", passed=True),
        CheckResult(name="Grain", passed=True),
    ]
    passed, failed, warnings = summarize_results(results)
    assert passed == 3
    assert failed == 0


def test_summarize_with_failures():
    results = [
        CheckResult(name="Compile", passed=True),
        CheckResult(name="Build", passed=False, critical=True),
        CheckResult(name="Grain", passed=True, warnings=["No PK test"]),
    ]
    passed, failed, warnings = summarize_results(results)
    assert passed == 2
    assert failed == 1
    assert warnings == 1
