#!/usr/bin/env bash
# ============================================================
# check_model.sh — Run all verifiable project standards against
#                  a single dbt model, using existing tools.
#
# Tools used:
#   1. sqlfluff          — formatting rules
#   2. dbt build         — tests, contracts, data integrity
#   3. dbt-score         — documentation quality
#   4. dbt-project-evaluator — naming, DAG, structure
#   5. Static grep       — patterns no tool covers
#   6. Layer checks      — staging/integration/mart constraints
#   7. YAML companion    — description quality, contracts, sync
#
# Usage:
#   ./scripts/check_model.sh <model_name>
#
# Examples:
#   ./scripts/check_model.sh stg_vistareserve__parks
#   ./scripts/check_model.sh int_parks
#   ./scripts/check_model.sh fct_reservations
#
# Prerequisites:
#   - Virtual environment activated
#   - dbt deps installed
#   - dbt-project-evaluator built at least once
# ============================================================

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <model_name>"
    exit 1
fi

MODEL="$1"
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
SKIP_COUNT=0

# ── Helpers ──────────────────────────────────────────────────

header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

pass() { echo "  ✅ $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  ❌ $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn() { echo "  ⚠️  $1"; WARN_COUNT=$((WARN_COUNT + 1)); }
skip() { echo "  ⏭️  $1"; SKIP_COUNT=$((SKIP_COUNT + 1)); }

# ── Resolve model via dbt ls ────────────────────────────────

echo ""
echo "Resolving model: ${MODEL}"

SQL_FILE=$(dbt ls -s "$MODEL" --output path \
    --resource-types model --quiet 2>/dev/null \
    | sed 's|\\|/|g' | grep '\.sql$' | head -1)

if [[ -z "$SQL_FILE" || ! -f "$SQL_FILE" ]]; then
    echo "ERROR: dbt ls could not resolve '${MODEL}'"
    exit 1
fi

echo "SQL file: ${SQL_FILE}"

# ── Detect model layer ──────────────────────────────────────

LAYER=""
if [[ "$MODEL" == stg_* ]]; then LAYER="staging"
elif [[ "$MODEL" == base_* ]]; then LAYER="base"
elif [[ "$MODEL" == int_* ]]; then LAYER="integration"
elif [[ "$MODEL" == fct_* ]]; then LAYER="fact"
elif [[ "$MODEL" == dim_* ]]; then LAYER="dimension"
elif [[ "$MODEL" == rpt_* ]]; then LAYER="report"
fi

echo "Layer:    ${LAYER:-unknown}"

# ── Locate companion YAML ───────────────────────────────────

SQL_DIR=$(dirname "$SQL_FILE")
YAML_FILE="${SQL_DIR}/_models.yml"

if [[ -f "$YAML_FILE" ]]; then
    echo "YAML:     ${YAML_FILE}"
else
    YAML_FILE=""
    echo "YAML:     (none found)"
fi

# ════════════════════════════════════════════════════════════
# 1. sqlfluff — formatting (ALL-FMT-*, ALL-CTE-02, etc.)
# ════════════════════════════════════════════════════════════

header "1. sqlfluff lint"

if command -v sqlfluff &>/dev/null; then
    SQLFLUFF_OUT=$(sqlfluff lint "$SQL_FILE" \
        --dialect duckdb --templater dbt 2>&1 || true)
    VIOLATION_COUNT=$(echo "$SQLFLUFF_OUT" \
        | grep -cP '(L:|FAIL)' || true)
    if [[ $VIOLATION_COUNT -eq 0 ]]; then
        pass "sqlfluff — zero violations"
    else
        fail "sqlfluff — ${VIOLATION_COUNT} violation(s)"
        echo "$SQLFLUFF_OUT" | grep -P '(L:|FAIL)' \
            | head -10 | sed 's/^/         /'
    fi
else
    skip "sqlfluff — not on PATH (activate venv)"
fi

# ════════════════════════════════════════════════════════════
# 2. dbt build — tests, contracts, compilation
# ════════════════════════════════════════════════════════════

header "2. dbt build --select ${MODEL}"

DBT_OUT=$(dbt build --select "$MODEL" 2>&1 || true)
DBT_PASS=$(echo "$DBT_OUT" | grep -c '\[PASS\]' || true)
DBT_FAIL=$(echo "$DBT_OUT" | grep -c '\[FAIL' || true)
DBT_ERROR=$(echo "$DBT_OUT" | grep -c '\[ERROR' || true)

if [[ $DBT_FAIL -eq 0 && $DBT_ERROR -eq 0 ]]; then
    pass "dbt build — ${DBT_PASS} test(s) passed"
else
    fail "dbt build — ${DBT_FAIL} fail, ${DBT_ERROR} error"
    echo "$DBT_OUT" | grep -E '\[(FAIL|ERROR)' \
        | head -10 | sed 's/^/         /'
fi

# ════════════════════════════════════════════════════════════
# 3. dbt-score — documentation quality (YML-DOC-*, ALL-TST-02)
# ════════════════════════════════════════════════════════════

header "3. dbt-score lint --select ${MODEL}"

SCORE_OUT=$(PYTHONIOENCODING=utf-8 python -m dbt_score lint \
    --select "$MODEL" 2>&1 || true)

# Show the raw output (score + individual rules)
echo "$SCORE_OUT" | grep -vP '(^$|Warning|UserWarning|warn\()' \
    | sed 's/^/  /' || true

# Parse pass/fail from score value
SCORE_VAL=$(echo "$SCORE_OUT" \
    | grep -oP '\(score: [0-9.]+\)' | head -1 \
    | grep -oP '[0-9.]+' || true)
if [[ -n "$SCORE_VAL" ]]; then
    # Compare against threshold (5.0)
    BELOW=$(python -c \
        "print('yes' if float('${SCORE_VAL}') < 5.0 else 'no')")
    if [[ "$BELOW" == "yes" ]]; then
        fail "dbt-score — ${SCORE_VAL} (below 5.0 threshold)"
    else
        pass "dbt-score — ${SCORE_VAL}"
    fi
else
    skip "dbt-score — could not parse score"
fi

# ════════════════════════════════════════════════════════════
# 4. dbt-project-evaluator — naming, DAG, test coverage
# ════════════════════════════════════════════════════════════

header "4. dbt-project-evaluator (filtered to ${MODEL})"

# Each evaluator fact table that can filter by model name
declare -A EVAL_CHECKS=(
    ["fct_model_naming_conventions"]="Naming conventions"
    ["fct_model_directories"]="Directory placement"
    ["fct_direct_join_to_source"]="Direct source joins"
    ["fct_missing_primary_key_tests"]="Primary key tests"
    ["fct_undocumented_models"]="Documentation"
)

# Column that holds the model name varies by table
declare -A EVAL_COLUMNS=(
    ["fct_model_naming_conventions"]="resource_name"
    ["fct_model_directories"]="resource_name"
    ["fct_direct_join_to_source"]="child"
    ["fct_missing_primary_key_tests"]="resource_name"
    ["fct_undocumented_models"]="resource_name"
)

for TABLE in "${!EVAL_CHECKS[@]}"; do
    LABEL="${EVAL_CHECKS[$TABLE]}"
    COL="${EVAL_COLUMNS[$TABLE]}"
    echo "  Checking: ${LABEL}..."

    RESULT=$(dbt show --inline \
        "select * from {{ ref('${TABLE}') }} where ${COL} = '${MODEL}'" \
        --limit 5 --quiet 2>&1 || true)

    if echo "$RESULT" | grep -q "$MODEL"; then
        # Directory finding on Windows is often a false positive
        if [[ "$TABLE" == "fct_model_directories" ]]; then
            warn "evaluator — ${LABEL} (likely Windows FP)"
        else
            fail "evaluator — ${LABEL}"
            echo "$RESULT" | tail -3 | sed 's/^/         /'
        fi
    else
        pass "evaluator — ${LABEL}"
    fi
done

# ════════════════════════════════════════════════════════════
# 5. Static SQL checks — patterns no tool covers
# ════════════════════════════════════════════════════════════

header "5. Static SQL checks (rules no tool covers)"

# -- ALL-PERF-03: No bare union --
BARE_UNION=$(grep -nP '^\s*union\s*$' "$SQL_FILE" || true)
if [[ -z "$BARE_UNION" ]]; then
    pass "ALL-PERF-03 — no bare 'union'"
else
    fail "ALL-PERF-03 — bare 'union' (use 'union all')"
    echo "$BARE_UNION" | sed 's/^/         /'
fi

# -- ALL-PERF-03: No select distinct --
SELECT_DISTINCT=$(grep -niP '\bselect\s+distinct\b' \
    "$SQL_FILE" || true)
if [[ -z "$SELECT_DISTINCT" ]]; then
    pass "ALL-PERF-03 — no 'select distinct'"
else
    fail "ALL-PERF-03 — 'select distinct' found"
    echo "$SELECT_DISTINCT" | sed 's/^/         /'
fi

# -- ALL-PERF-04: No subqueries --
SUBQUERY=$(grep -nP '\(\s*select\b' "$SQL_FILE" \
    | grep -v 'generate_surrogate_key' | head -3 || true)
if [[ -z "$SUBQUERY" ]]; then
    pass "ALL-PERF-04 — no subqueries"
else
    warn "ALL-PERF-04 — possible subquery"
    echo "$SUBQUERY" | sed 's/^/         /'
fi

# -- ALL-CTE-11: Simple final select --
FINAL_LINE=$(tail -20 "$SQL_FILE" \
    | grep -v '^\s*$' | grep -v '^\s*--' | tail -1 \
    | sed 's/\r$//')
if echo "$FINAL_LINE" \
    | grep -qP '^\s*select\s+\*\s+from\s+\w+\s*$'; then
    pass "ALL-CTE-11 — simple final select"
else
    fail "ALL-CTE-11 — final line is not 'select * from <cte>'"
    echo "         Found: ${FINAL_LINE}"
fi

# -- ALL-FMT-01: File length --
LINE_COUNT=$(wc -l < "$SQL_FILE" | tr -d ' ')
if [[ $LINE_COUNT -le 200 ]]; then
    pass "ALL-FMT-01 — ${LINE_COUNT} lines (≤ 200)"
else
    warn "ALL-FMT-01 — ${LINE_COUNT} lines (> 200)"
fi

# -- ALL-CTE-01: Import CTEs at top --
INLINE_JOIN=$(grep -nP '(left|right|inner|cross|full)\s+join\s+\{\{' \
    "$SQL_FILE" || true)
INLINE_ALIAS=$(grep -nP '\{\{\s*(ref|source)\s*\(.*?\}\}\s+as\s+' \
    "$SQL_FILE" || true)
if [[ -z "$INLINE_JOIN" && -z "$INLINE_ALIAS" ]]; then
    pass "ALL-CTE-01 — ref/source calls in import CTEs"
else
    fail "ALL-CTE-01 — ref/source buried in transformation logic"
    echo "${INLINE_JOIN}${INLINE_ALIAS}" | head -3 | sed 's/^/         /'
fi

# -- ALL-CTE-07: Primary key first in final CTE --
CTE07_COL=$(python -c "
import re, sys
with open(sys.argv[1]) as f:
    sql = f.read()
m = re.search(r'select\s+\*\s+from\s+(\w+)\s*$', sql, re.M)
if not m: sys.exit()
cte = m.group(1)
p = re.compile(rf'{cte}\s+as\s*\(\s*select\b(.*?)\bfrom\b', re.DOTALL|re.I)
m2 = p.search(sql)
if not m2: sys.exit()
lines = [l.strip() for l in m2.group(1).split('\n')
         if l.strip() and not l.strip().startswith('--')]
if not lines: sys.exit()
first = lines[0].rstrip(',')
parts = re.split(r'\s+as\s+', first, flags=re.I)
col = parts[-1].strip()
if '.' in col: col = col.split('.')[-1]
print(col)
" "$SQL_FILE" 2>/dev/null || true)

if [[ -z "$CTE07_COL" ]]; then
    skip "ALL-CTE-07 — could not parse final CTE"
elif echo "$CTE07_COL" | grep -qP '(^hk_|_sk$|_id$|_key$)'; then
    pass "ALL-CTE-07 — PK first in final CTE (${CTE07_COL})"
else
    warn "ALL-CTE-07 — first column '${CTE07_COL}' may not be PK"
fi

# -- ALL-CFG-02: Config block at top of file --
CONFIG_LINE=$(grep -nP '\{\{\s*config\(' "$SQL_FILE" \
    | head -1 | cut -d: -f1 || true)
if [[ -n "$CONFIG_LINE" ]]; then
    FIRST_CODE=$(grep -nP '^\s*[^-\s]' "$SQL_FILE" \
        | grep -vP '^\d+:\s*--' | head -1 | cut -d: -f1 || true)
    if [[ "$CONFIG_LINE" == "$FIRST_CODE" ]]; then
        pass "ALL-CFG-02 — config() is first statement"
    else
        fail "ALL-CFG-02 — config() not at top (line ${CONFIG_LINE})"
    fi
else
    pass "ALL-CFG-02 — no config() block (uses project defaults)"
fi

# -- ALL-PERF-02: No generate_uuid() --
UUID_CALL=$(grep -niP '\b(generate_uuid|uuid)\s*\(' "$SQL_FILE" || true)
if [[ -z "$UUID_CALL" ]]; then
    pass "ALL-PERF-02 — no generate_uuid()"
else
    fail "ALL-PERF-02 — non-reproducible key generation"
    echo "$UUID_CALL" | sed 's/^/         /'
fi

# -- ALL-PERF-01: Long CASE statements --
WHEN_COUNT=$(grep -ciP '^\s*when\b' "$SQL_FILE" || true)
if [[ $WHEN_COUNT -le 8 ]]; then
    pass "ALL-PERF-01 — CASE branches ≤ 8 (${WHEN_COUNT} found)"
else
    warn "ALL-PERF-01 — ${WHEN_COUNT} CASE branches (consider macro/seed)"
fi

# -- ALL-FMT-02: Line length ≤ 80 --
LONG_LINES=$(awk 'length > 80' "$SQL_FILE" | wc -l | tr -d ' ')
if [[ "$LONG_LINES" -eq 0 ]]; then
    pass "ALL-FMT-02 — all lines ≤ 80 characters"
else
    warn "ALL-FMT-02 — ${LONG_LINES} line(s) exceed 80 characters"
fi

# ════════════════════════════════════════════════════════════
# 6. Layer-specific checks
# ════════════════════════════════════════════════════════════

header "6. Layer-specific checks (${LAYER:-n/a})"

if [[ -z "$LAYER" ]]; then
    skip "Layer unknown — cannot run layer-specific checks"
else
    case "$LAYER" in
        staging)
            # -- SQL-STG-06: No joins, aggregations, or filtering --
            STG_JOIN=$(grep -niP \
                '^\s*(left|right|inner|cross|full)?\s*join\b' \
                "$SQL_FILE" || true)
            STG_AGG=$(grep -niP '^\s*(group\s+by|having)\b' \
                "$SQL_FILE" || true)
            STG_WHERE=$(grep -niP '^\s*where\b' "$SQL_FILE" \
                | grep -viP 'where\s+true' || true)
            if [[ -z "$STG_JOIN" && -z "$STG_AGG" \
                    && -z "$STG_WHERE" ]]; then
                pass "SQL-STG-06 — no joins, aggregations, or filtering"
            else
                fail "SQL-STG-06 — staging model has forbidden ops"
                echo "${STG_JOIN}${STG_AGG}${STG_WHERE}" \
                    | head -5 | sed 's/^/         /'
            fi

            # -- SQL-STG-07: Hash key present --
            HK_COL=$(grep -P 'hk_\w+' "$SQL_FILE" || true)
            if [[ -n "$HK_COL" ]]; then
                pass "SQL-STG-07 — hash key (hk_) present"
            else
                warn "SQL-STG-07 — no hash key (hk_) found"
            fi

            # -- SQL-STG-04: Double-underscore delimiter --
            BASENAME=$(basename "$SQL_FILE" .sql)
            if echo "$BASENAME" \
                | grep -qP '^stg_[a-z0-9]+__[a-z0-9_]+$'; then
                pass "SQL-STG-04 — double-underscore delimiter"
            else
                fail "SQL-STG-04 — filename missing '__' delimiter"
                echo "         Found: ${BASENAME}"
            fi

            # -- SQL-STG-05: Consumes source() or base model --
            HAS_SOURCE=$(grep -P '\{\{\s*source\(' \
                "$SQL_FILE" || true)
            HAS_BASE=$(grep -P "\{\{\s*ref\(\s*['\"]base_" \
                "$SQL_FILE" || true)
            if [[ -n "$HAS_SOURCE" || -n "$HAS_BASE" ]]; then
                pass "SQL-STG-05 — consumes source() or base model"
            else
                fail "SQL-STG-05 — must use source() or ref('base_')"
            fi
            ;;

        integration)
            # -- SQL-INT-06: Surrogate key named <object>_sk --
            SK_COL=$(grep -P '_sk\b' "$SQL_FILE" || true)
            if [[ -n "$SK_COL" ]]; then
                pass "SQL-INT-06 — surrogate key (_sk) present"
            else
                warn "SQL-INT-06 — no surrogate key (_sk) found"
            fi
            ;;

        fact)
            # -- SQL-FCT-05: Consume integration models --
            INT_REF=$(grep -P "ref\(\s*['\"]int_" \
                "$SQL_FILE" || true)
            if [[ -n "$INT_REF" ]]; then
                pass "SQL-FCT-05 — consumes integration model(s)"
            else
                fail "SQL-FCT-05 — must consume integration models"
            fi
            ;;

        dimension)
            # -- SQL-DIM-05: Consume integration models --
            INT_REF=$(grep -P "ref\(\s*['\"]int_" \
                "$SQL_FILE" || true)
            if [[ -n "$INT_REF" ]]; then
                pass "SQL-DIM-05 — consumes integration model(s)"
            else
                fail "SQL-DIM-05 — must consume integration models"
            fi
            ;;

        *)
            skip "No layer-specific checks for '${LAYER}'"
            ;;
    esac
fi

# ════════════════════════════════════════════════════════════
# 7. YAML companion checks
# ════════════════════════════════════════════════════════════

header "7. YAML companion checks"

if [[ -z "$YAML_FILE" ]]; then
    skip "No _models.yml found — skipping YAML checks"
else
    # -- ALL-TST-02: Red-flag words in descriptions --
    RED_FLAGS=$(python -c "
import yaml, re, sys
try:
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    flags = r'\b(unique|not_null|fan.out|deduplication'
    flags += r'|protecting against|tests verify|collision'
    flags += r'|ensures that|guards against)\b'
    for m in data.get('models', []):
        if m.get('name') == sys.argv[2]:
            desc = m.get('description', '')
            for hit in re.finditer(flags, desc, re.I):
                print(f'model desc: \"{hit.group()}\"')
            for c in m.get('columns', []):
                cd = c.get('description', '')
                for hit in re.finditer(flags, cd, re.I):
                    print(f'{c[\"name\"]}: \"{hit.group()}\"')
except Exception:
    pass
" "$YAML_FILE" "$MODEL" 2>/dev/null || true)

    if [[ -z "$RED_FLAGS" ]]; then
        pass "ALL-TST-02 — no red-flag words in descriptions"
    else
        fail "ALL-TST-02 — test rationale in description (move to meta:)"
        echo "$RED_FLAGS" | head -5 | sed 's/^/         /'
    fi

    # -- MRT-YML-04 + MRT-YML-05: Contract and data_type --
    if [[ "$LAYER" == "fact" || "$LAYER" == "dimension" ]]; then
        CONTRACT_INFO=$(python -c "
import yaml, sys
try:
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    for m in data.get('models', []):
        if m.get('name') == sys.argv[2]:
            cfg = m.get('config', {})
            ct = cfg.get('contract', {})
            enforced = ct.get('enforced', False)
            cols = m.get('columns', [])
            total = len(cols)
            typed = sum(1 for c in cols if 'data_type' in c)
            print(f'enforced={enforced}')
            print(f'cols={total}')
            print(f'typed={typed}')
except Exception:
    pass
" "$YAML_FILE" "$MODEL" 2>/dev/null || true)

        IS_ENFORCED=$(echo "$CONTRACT_INFO" \
            | grep -oP 'enforced=\K.*' || true)
        COL_TOTAL=$(echo "$CONTRACT_INFO" \
            | grep -oP 'cols=\K.*' || true)
        COL_TYPED=$(echo "$CONTRACT_INFO" \
            | grep -oP 'typed=\K.*' || true)

        if [[ "$IS_ENFORCED" == "True" ]]; then
            pass "MRT-YML-04 — contract enforced"
        else
            fail "MRT-YML-04 — mart needs contract: { enforced: true }"
        fi

        if [[ "$IS_ENFORCED" == "True" ]]; then
            if [[ "$COL_TYPED" == "$COL_TOTAL" \
                    && "$COL_TOTAL" -gt 0 ]]; then
                pass "MRT-YML-05 — data_type on all ${COL_TOTAL} columns"
            else
                fail "MRT-YML-05 — ${COL_TYPED}/${COL_TOTAL} columns have data_type"
            fi
        fi
    fi

    # -- YML-SYNC-01: YAML columns present in SQL --
    SYNC_RESULT=$(python -c "
import yaml, sys
try:
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    with open(sys.argv[2]) as f:
        sql = f.read()
    for m in data.get('models', []):
        if m.get('name') == sys.argv[3]:
            yaml_cols = [c['name'] for c in m.get('columns', [])]
            missing = [c for c in yaml_cols if c not in sql]
            if not yaml_cols:
                print('EMPTY')
            elif missing:
                for c in missing:
                    print(f'MISSING:{c}')
            else:
                print('ALIGNED')
            break
except Exception:
    pass
" "$YAML_FILE" "$SQL_FILE" "$MODEL" 2>/dev/null || true)

    if [[ "$SYNC_RESULT" == "ALIGNED" ]]; then
        pass "YML-SYNC-01 — YAML columns found in SQL"
    elif [[ "$SYNC_RESULT" == "EMPTY" ]]; then
        skip "YML-SYNC-01 — no columns defined in YAML"
    elif echo "$SYNC_RESULT" | grep -q "MISSING"; then
        warn "YML-SYNC-01 — YAML columns not found in SQL"
        echo "$SYNC_RESULT" | grep 'MISSING:' \
            | sed 's/MISSING://' | head -5 \
            | sed 's/^/         /'
    else
        skip "YML-SYNC-01 — could not parse for comparison"
    fi

    # -- STG/INT/MRT-YML-02: No per-model YAML files --
    if [[ -f "${SQL_DIR}/${MODEL}.yml" ]]; then
        fail "YML-02 — per-model YAML file '${MODEL}.yml' not permitted"
    else
        pass "YML-02 — no per-model YAML file"
    fi

    # -- MRT-YML-06: Exposure defined for mart models --
    if [[ "$LAYER" == "fact" || "$LAYER" == "dimension" \
            || "$LAYER" == "report" ]]; then
        if [[ -f "${SQL_DIR}/_exposures.yml" ]]; then
            pass "MRT-YML-06 — exposures file exists"
        else
            warn "MRT-YML-06 — no _exposures.yml in mart directory"
        fi
    fi
fi

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

header "SUMMARY: ${MODEL}"

TOTAL=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT + SKIP_COUNT))

echo ""
echo "  ✅ Passed:   ${PASS_COUNT}"
echo "  ❌ Failed:   ${FAIL_COUNT}"
echo "  ⚠️  Warnings: ${WARN_COUNT}"
echo "  ⏭️  Skipped:  ${SKIP_COUNT}"
echo "  ──────────────"
echo "  Total:      ${TOTAL} checks"
echo ""

if [[ $FAIL_COUNT -gt 0 ]]; then
    echo "  Result: FAIL (${FAIL_COUNT} rule violation(s))"
    exit 1
else
    echo "  Result: PASS (${WARN_COUNT} warning(s) to review)"
    exit 0
fi
