# Phase 5: `reviewer/` — Connor's Review Tooling — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `check_model.py`, `review_model.py`, and `summarize_reviews.py` into the `reviewer/` package with a new `--branch` mode for PR-level batch review.

**Architecture:** Three modules migrated from existing scripts plus a CLI that adds `--branch` mode. The existing logic is moved as-is, then adapted to use `_core/` where appropriate. New `--branch` mode uses `git diff` to find changed models and runs the full suite on each.

**Tech Stack:** Python 3.10+, dbt-core (dbtRunner), rich, git

**Spec:** `docs/superpowers/specs/2026-03-20-scripts-redesign-design.md` (section: "Phase 5: `reviewer/`")

**Depends on:** Phase 0 (`_core/`)

---

### Task 1: Create `reviewer/` package and migrate `check_model.py` → `automated.py`

**Files:**
- Create: `scripts/reviewer/__init__.py`
- Create: `scripts/reviewer/cli.py`
- Create: `scripts/reviewer/automated.py` (from `scripts/check_model.py`)
- Test: `tests/scripts/test_reviewer_cli.py`

- [ ] **Step 1: Write test for CLI parsing**

```python
# tests/scripts/test_reviewer_cli.py
from scripts.reviewer.cli import parse_args


def test_parse_select():
    args = parse_args(["--select", "int_parks"])
    assert args.select == "int_parks"
    assert args.branch is None


def test_parse_branch():
    args = parse_args(["--branch", "feature/grant-models"])
    assert args.branch == "feature/grant-models"
    assert args.select is None


def test_parse_summarize():
    args = parse_args(["summarize", "--input", "tmp/reviews/"])
    assert args.subcommand == "summarize"
    assert args.input == "tmp/reviews/"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_reviewer_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create package structure and CLI**

```python
# scripts/reviewer/__init__.py
```

```python
# scripts/reviewer/cli.py
"""Connor's review tooling — automated checks, qualitative review, branch review.

Usage:
    python -m scripts.reviewer --select int_grant_applications
    python -m scripts.reviewer --branch feature/grant-models
    python -m scripts.reviewer summarize --input tmp/reviews/
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review tooling: automated checks, qualitative review, branch review.",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # Default mode (no subcommand) — review a model or branch
    parser.add_argument("--select", "-s", help="dbt model selector")
    parser.add_argument("--branch", "-b", help="Git branch to review (all changed models)")
    parser.add_argument("--output", "-o", default="terminal", help="Output mode")
    parser.add_argument("--agent", action="store_true", help="Agent-friendly output (suppress dbt noise)")

    # Summarize subcommand
    sub_sum = subparsers.add_parser("summarize", help="Summarize review findings")
    sub_sum.add_argument("--input", "-i", required=True, help="Directory with review files")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if getattr(args, "subcommand", None) == "summarize":
        from scripts.reviewer.summarize import run_summarize
        return run_summarize(args.input)

    if args.branch:
        from scripts.reviewer.automated import run_branch_review
        return run_branch_review(args.branch, agent=args.agent)

    if args.select:
        from scripts.reviewer.automated import run_model_review
        return run_model_review(args.select, agent=args.agent)

    print("Error: provide --select or --branch", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_reviewer_cli.py -v`
Expected: PASS

- [ ] **Step 5: Migrate `check_model.py` to `automated.py`**

Copy the contents of `scripts/check_model.py` to `scripts/reviewer/automated.py`. Update imports to use `scripts._core` where appropriate. Add these entry point functions:

```python
def run_model_review(selector: str, agent: bool = False) -> tuple[int, dict]:
    """Run all automated checks for a single model.

    Returns (exit_code, summary_dict) where summary_dict has:
        {"model": str, "passed": int, "failed": int, "warnings": int, "details": list[CheckResult]}
    """
    # ... existing check_model.py logic adapted to return structured results ...


def run_branch_review(branch: str, agent: bool = False) -> int:
    """Review all changed models in a branch vs main.

    Produces a structured markdown summary suitable for PR comments.
    """
    import subprocess
    result = subprocess.run(
        ["git", "diff", f"main..{branch}", "--name-only"],
        capture_output=True, text=True,
    )
    changed_files = result.stdout.strip().split("\n")

    # Filter to SQL model files and YAML, extract model names
    model_names = []
    for f in changed_files:
        if f.endswith(".sql") and "models/" in f:
            name = f.split("/")[-1].removesuffix(".sql")
            model_names.append(name)

    if not model_names:
        print(f"No changed models found in branch {branch}")
        return 0

    # Run reviews and collect structured results
    all_results: list[dict] = []
    exit_code = 0
    for model_name in model_names:
        code, summary = run_model_review(model_name, agent=agent)
        all_results.append(summary)
        if code != 0:
            exit_code = 1

    # Produce PR-comment-ready markdown summary
    _print_branch_summary_markdown(branch, all_results)
    return exit_code


def _print_branch_summary_markdown(branch: str, results: list[dict]) -> None:
    """Print a structured markdown summary suitable for pasting into a PR comment."""
    print(f"## Branch Review: `{branch}`\n")
    print(f"| Model | Passed | Failed | Warnings |")
    print(f"|---|---|---|---|")
    for r in results:
        model = r["model"]
        icon = "✓" if r["failed"] == 0 else "✗"
        print(f"| {icon} `{model}` | {r['passed']} | {r['failed']} | {r['warnings']} |")

    total_pass = sum(r["passed"] for r in results)
    total_fail = sum(r["failed"] for r in results)
    total_warn = sum(r["warnings"] for r in results)
    print(f"\n**Total:** {total_pass} passed, {total_fail} failed, {total_warn} warnings")

    # Detail section for failures
    failures = [r for r in results if r["failed"] > 0]
    if failures:
        print(f"\n### Failures\n")
        for r in failures:
            print(f"**{r['model']}:**")
            for detail in r.get("details", []):
                if not detail.passed:
                    print(f"- ✗ {detail.name}: {detail.message}")
                    if detail.fix_command:
                        print(f"  - Fix: `{detail.fix_command}`")
```

- [ ] **Step 6: Commit**

```bash
git add scripts/reviewer/ tests/scripts/test_reviewer_cli.py
git commit -m "feat(reviewer): create package, migrate check_model.py to automated.py"
```

---

### Task 2: Migrate `review_model.py` → `qualitative.py`

**Files:**
- Create: `scripts/reviewer/qualitative.py` (from `scripts/review_model.py`)

- [ ] **Step 1: Copy `scripts/review_model.py` to `scripts/reviewer/qualitative.py`**

Update imports to use `scripts.reviewer.automated` instead of `scripts.check_model`. Preserve all existing functionality.

- [ ] **Step 2: Verify existing tests still pass (if any)**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/ -v -k "review" --timeout=60`

- [ ] **Step 3: Commit**

```bash
git add scripts/reviewer/qualitative.py
git commit -m "feat(reviewer): migrate review_model.py to qualitative.py"
```

---

### Task 3: Migrate `summarize_reviews.py` → `summarize.py`

**Files:**
- Create: `scripts/reviewer/summarize.py` (from `scripts/summarize_reviews.py`)

- [ ] **Step 1: Copy `scripts/summarize_reviews.py` to `scripts/reviewer/summarize.py`**

Add `run_summarize(input_dir: str) -> int` entry point. Preserve existing functionality.

- [ ] **Step 2: Verify the module imports correctly**

Run: `source .venv/Scripts/activate && python -c "from scripts.reviewer.summarize import run_summarize; print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add scripts/reviewer/summarize.py
git commit -m "feat(reviewer): migrate summarize_reviews.py to summarize.py"
```

---

### Task 4: Update old script imports and add deprecation wrappers

**Files:**
- Modify: `scripts/check_model.py` — add import redirect
- Modify: `scripts/review_model.py` — add import redirect
- Modify: `scripts/summarize_reviews.py` — add import redirect

- [ ] **Step 1: Add deprecation wrappers to old scripts**

In each old script, replace the body with a redirect:

```python
# scripts/check_model.py (top of file, after existing imports)
import warnings
warnings.warn(
    "scripts/check_model.py is deprecated. Use: python -m scripts.reviewer --select <model>",
    DeprecationWarning,
    stacklevel=2,
)
# Keep existing code for backward compatibility during transition
```

The old scripts continue to work but print a deprecation warning. They will be removed in Phase 7.

- [ ] **Step 2: Verify backward compatibility**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python scripts/review_model.py --help`
Expected: Help text prints (with deprecation warning).

- [ ] **Step 3: Commit**

```bash
git add scripts/check_model.py scripts/review_model.py scripts/summarize_reviews.py
git commit -m "refactor(reviewer): add deprecation warnings to old script entry points"
```
