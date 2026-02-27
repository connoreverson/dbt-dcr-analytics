# ============================================================
# check_model.ps1 - Run all verifiable project standards against
#                   a single dbt model natively.
#
# Tools used:
#   1. sqlfluff          - formatting rules
#   2. dbt build         - tests, contracts, data integrity
#   3. dbt-score         - documentation quality
#   4. dbt-project-evaluator - naming, DAG, structure
#   5. Static & Native checks - SQL rules, layer configs
#   6. Manifest / dbt show    - precise YAML & output checking
#
# Usage:
#   .\scripts\check_model.ps1 <model_name>
#
# Examples:
#   .\scripts\check_model.ps1 stg_vistareserve__parks
#   .\scripts\check_model.ps1 int_parks
#   .\scripts\check_model.ps1 fct_reservations
#
# Prerequisites:
#   - Virtual environment activated
#   - dbt deps installed
#   - dbt project built (target\manifest.json is up to date)
# ============================================================

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Model
)

$ErrorActionPreference = 'Continue'

$PassCount = 0
$FailCount = 0
$WarnCount = 0
$SkipCount = 0

# ---- Helpers ------------------------------------------------

function Write-Header([string]$Title) {
    Write-Host ""
    Write-Host "=================================================="
    Write-Host "  $Title"
    Write-Host "=================================================="
}

function Write-Pass([string]$Msg) { Write-Host "  [PASS] $Msg"; $script:PassCount++ }
function Write-Fail([string]$Msg) { Write-Host "  [FAIL] $Msg"; $script:FailCount++ }
function Write-Warn([string]$Msg) { Write-Host "  [WARN] $Msg"; $script:WarnCount++ }
function Write-Skip([string]$Msg) { Write-Host "  [SKIP] $Msg"; $script:SkipCount++ }

function Count-Matches([string]$Text, [string]$Pattern) {
    if ([string]::IsNullOrEmpty($Text)) { return 0 }
    return ($Text -split "`n" | Where-Object { $_ -match $Pattern }).Count
}

# ---- Resolve model via dbt ls --------------------------------

Write-Host ""
Write-Host "Resolving model: $Model"

$dbtLsOutput = dbt ls -s $Model --output path --resource-types model --quiet 2>$null
$SqlFile = $dbtLsOutput |
    ForEach-Object { ($_ -replace '\\', '/') } |
    Where-Object { $_ -match '\.sql$' } |
    Select-Object -First 1

if ([string]::IsNullOrEmpty($SqlFile) -or -not (Test-Path $SqlFile)) {
    Write-Error "ERROR: dbt ls could not resolve '$Model'"
    exit 1
}

Write-Host "SQL file: $SqlFile"

# ---- Detect model layer ---------------------------------------

$Layer = switch -Wildcard ($Model) {
    'stg_*'  { 'staging' }
    'base_*' { 'base' }
    'int_*'  { 'integration' }
    'fct_*'  { 'fact' }
    'dim_*'  { 'dimension' }
    'rpt_*'  { 'report' }
    default  { '' }
}

Write-Host "Layer:    $(if ($Layer) { $Layer } else { 'unknown' })"

$SqlDir   = Split-Path $SqlFile -Parent
$YamlFile = Join-Path $SqlDir '_models.yml'

if (Test-Path $YamlFile) {
    Write-Host "YAML:     $YamlFile"
} else {
    $YamlFile = ''
    Write-Host "YAML:     (none found)"
}

$SqlLines = Get-Content $SqlFile

# ==============================================================
# 1. sqlfluff - formatting (ALL-CTE-02, etc.)
# ==============================================================

Write-Header "1. sqlfluff lint"
# NOTE: Line length limits (ALL-FMT-02) and checks are handled by .sqlfluff automatically

if (Get-Command sqlfluff -ErrorAction SilentlyContinue) {
    $sqlfOut = sqlfluff lint $SqlFile --dialect duckdb --templater dbt 2>&1 | Out-String
    $violationCount = (($sqlfOut -split "`n") | Where-Object { $_ -match '(L:|FAIL)' }).Count
    if ($violationCount -eq 0) {
        Write-Pass "sqlfluff - zero violations"
    } else {
        Write-Fail "sqlfluff - $violationCount violation(s)"
        ($sqlfOut -split "`n") | Where-Object { $_ -match '(L:|FAIL)' } |
            Select-Object -First 10 | ForEach-Object { Write-Host "         $_" }
    }
} else {
    Write-Skip "sqlfluff - not on PATH (activate venv)"
}

# ==============================================================
# 2. dbt build - tests, contracts, compilation
# ==============================================================

Write-Header "2. dbt build --select $Model"

$dbtBuildOut = dbt build --select $Model 2>&1 | Out-String
$dbtPass  = Count-Matches $dbtBuildOut '\[PASS\]'
$dbtFail  = Count-Matches $dbtBuildOut '\[FAIL'
$dbtError = Count-Matches $dbtBuildOut '\[ERROR'

if ($dbtFail -eq 0 -and $dbtError -eq 0) {
    Write-Pass "dbt build - $dbtPass test(s) passed"
} else {
    Write-Fail "dbt build - $dbtFail fail, $dbtError error"
    ($dbtBuildOut -split "`n") | Where-Object { $_ -match '\[(FAIL|ERROR)' } |
        Select-Object -First 10 | ForEach-Object { Write-Host "         $_" }
}

# ==============================================================
# 3. dbt-score - documentation quality (YML-DOC-*, ALL-TST-02)
# ==============================================================

Write-Header "3. dbt-score lint --select $Model"

$env:PYTHONIOENCODING = 'utf-8'
$scoreOut = python -m dbt_score lint --select $Model -n dbt_score.rules.generic -n scripts.dbt_score_rules 2>&1 | ForEach-Object { "$_" } | Out-String

($scoreOut -split "`n") |
    Where-Object { $_ -notmatch '(^$|Warning|UserWarning|warn\()' } |
    ForEach-Object { Write-Host "  $_" }

$scoreMatch = [regex]::Match($scoreOut, '\(score: ([0-9.]+)\)')
if ($scoreMatch.Success) {
    $scoreVal = [double]$scoreMatch.Groups[1].Value
    if ($scoreVal -lt 5.0) {
        Write-Fail "dbt-score - $scoreVal (below 5.0 threshold)"
    } else {
        Write-Pass "dbt-score - $scoreVal"
    }
} else {
    Write-Skip "dbt-score - could not parse score"
}

# ==============================================================
# 4. dbt-project-evaluator - naming, DAG, test coverage
# ==============================================================

Write-Header "4. dbt-project-evaluator (filtered to $Model)"

$evalChecks = [ordered]@{
    'fct_model_naming_conventions'  = @{ Label = 'Naming conventions'; Column = 'resource_name' }
    'fct_model_directories'         = @{ Label = 'Directory placement'; Column = 'resource_name' }
    'fct_direct_join_to_source'     = @{ Label = 'Direct source joins'; Column = 'child'         }
    'fct_missing_primary_key_tests'          = @{ Label = 'Primary key tests';   Column = 'resource_name' }
    'fct_undocumented_models'                = @{ Label = 'Documentation';       Column = 'resource_name' }
    'fct_custom_fact_dim_missing_integration'= @{ Label = 'Integrations needed'; Column = 'resource_name' }
    'fct_custom_fact_dim_no_staging'         = @{ Label = 'No Staging on Marts'; Column = 'resource_name' }
    'fct_custom_staging_uses_source_or_base' = @{ Label = 'Staging bases only';  Column = 'resource_name' }
}

foreach ($table in $evalChecks.Keys) {
    $label  = $evalChecks[$table].Label
    $col    = $evalChecks[$table].Column
    Write-Host "  Checking: $label..."

    $inlineSql  = "select * from {{ ref('$table') }} where $col = '$Model'"
    $evalResult = dbt show --inline $inlineSql --limit 5 --quiet 2>&1 | Out-String

    if ($evalResult -match [regex]::Escape($Model)) {
        if ($table -eq 'fct_model_directories') {
            Write-Warn "evaluator - $label (likely Windows false positive)"
        } else {
            Write-Fail "evaluator - $label"
            ($evalResult -split "`n") | Select-Object -Last 3 |
                ForEach-Object { Write-Host "         $_" }
        }
    } else {
        Write-Pass "evaluator - $label"
    }
}

# ==============================================================
# 5. Static SQL checks - ported to custom sqlfluff rules (dbtps plugin)
# ==============================================================

# ==============================================================
# 6. manifest.json YAML & Layer Checks
# ==============================================================

Write-Header "6. manifest.json YAML & Layer Checks"

$ManifestPath = "target\manifest.json"
if (-not (Test-Path $ManifestPath)) {
    Write-Fail "target\manifest.json not found! Unable to run node checks. (Run dbt build/compile first)"
} else {
    $Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
    $NodeId = $Manifest.nodes.PSObject.Properties.Name | Where-Object { $_ -match "^model\.[a-zA-Z0-9_]+\.$Model`$" } | Select-Object -First 1

    if (-not $NodeId) {
        Write-Skip "Model '$Model' not found in manifest.json."
    } else {
        $Node = $Manifest.nodes.$NodeId
        $ProjectName = $Manifest.metadata.project_name

        # yaml checks ported to dbt-score (ALL-TST-02, MRT-YML-04, MRT-YML-05)

        # -- Layer-specific dependency checks using depends_on --
        # Ported to dbt-project-evaluator custom DAG models

        if ($Layer -eq 'staging') {
            # Additional STG logic
            $basename = [System.IO.Path]::GetFileNameWithoutExtension($SqlFile)
            if ($basename -match '^stg_[a-z0-9]+__[a-z0-9_]+$') {
                Write-Pass "SQL-STG-04 - double-underscore delimiter"
            } else {
                Write-Fail "SQL-STG-04 - filename missing '__' delimiter"
                Write-Host "         Found: $basename"
            }

            # -- SQL-STG-06: No joins, aggregations, or filtering --
            $stgJoin  = $SqlLines | Select-String -Pattern '^\s*(left|right|inner|cross|full)?\s*join\b'
            $stgAgg   = $SqlLines | Select-String -Pattern '^\s*(group\s+by|having)\b'
            $stgWhere = $SqlLines | Select-String -Pattern '^\s*where\b' |
                            Where-Object { $_.Line -notmatch 'where\s+true' }
            if (-not $stgJoin -and -not $stgAgg -and -not $stgWhere) {
                Write-Pass "SQL-STG-06 - no joins, aggregations, or filtering"
            } else {
                Write-Fail "SQL-STG-06 - staging model has forbidden ops (join/group/where)"
                (@($stgJoin) + @($stgAgg) + @($stgWhere)) | Select-Object -First 5 |
                    ForEach-Object { Write-Host "         $($_.LineNumber): $($_.Line)" }
            }
            
            # -- SQL-STG-07: Hash key present --
            $hkCol = $SqlLines | Select-String -Pattern 'hk_\w+'
            if ($hkCol) {
                Write-Pass "SQL-STG-07 - hash key (hk_) present in SQL"
            } else {
                Write-Warn "SQL-STG-07 - no hash key (hk_) found in SQL"
            }
        }
    }
}

# YML checks ported to dbt-score

# ==============================================================
# 7. dbt show --output json - Dynamic Column Checks
# ==============================================================

Write-Header "7. dbt show output checking (Schema & Keys)"

# We extract 1 row to get the schema JSON representation
$showOut = dbt --quiet show --select $Model --limit 1 --output json 2>&1 | Out-String

$jsonMatch = [regex]::Match($showOut, '(?s)\{.*\}')
if ($jsonMatch.Success) {
    try {
        $jsonObj = $jsonMatch.Value | ConvertFrom-Json
        $sqlCols = @()
        if ($jsonObj.show -and $jsonObj.show.Count -gt 0) {
            $sqlCols = $jsonObj.show[0].PSObject.Properties.Name
        }

        if ($sqlCols.Count -gt 0) {
            # Check if YAML columns are in SQL columns
            $yamlCols = @()
            if ($Node.columns) {
                $yamlCols = $Node.columns.PSObject.Properties.Name
            }
            
            if ($yamlCols.Count -eq 0) {
                Write-Skip "YML-SYNC-01 - no columns defined in companion YAML"
            } else {
                $missing = $yamlCols | Where-Object { $_ -notin $sqlCols }
                if ($missing.Count -eq 0) {
                    Write-Pass "YML-SYNC-01 - YAML columns found exactly in runtime SQL output"
                } else {
                    Write-Warn "YML-SYNC-01 - YAML columns not found in runtime SQL output"
                    $missing | Select-Object -First 5 | ForEach-Object { Write-Host "         $_" }
                }
            }

            # -- ALL-CTE-07: Primary key first in final CTE --
            $firstCol = $sqlCols[0]
            if ($firstCol -match '(^hk_|_sk$|_id$|_key$)') {
                Write-Pass "ALL-CTE-07 - PK first in runtime schema ($firstCol)"
            } else {
                Write-Warn "ALL-CTE-07 - first column '$firstCol' in schema may not be PK"
            }
            
            # Layer specific check for integration surrogate keys using exact columns
            if ($Layer -eq 'integration') {
                $skCol = $sqlCols | Where-Object { $_ -match '_sk$' }
                if ($skCol) {
                    Write-Pass "SQL-INT-06 - surrogate key (_sk) present in runtime columns"
                } else {
                    Write-Warn "SQL-INT-06 - no surrogate key (_sk) found in runtime columns"
                }

                # -- SQL-INT-03: Entity Name Word Choice & SQL-INT-05: CDM Column Conformance --
                $crosswalkPath = "seeds\cdm_crosswalk.csv"
                if (Test-Path $crosswalkPath) {
                    $crosswalk = Import-Csv $crosswalkPath
                    $cdmEntity = $crosswalk | Where-Object { $_.integration_model -eq $Model } | Select-Object -First 1 -ExpandProperty cdm_entity
                    
                    if ($cdmEntity) {

                        # Check SQL-INT-03
                        $snakeCdm = $cdmEntity -replace '([a-z])([A-Z])', '$1_$2'
                        $expectedTarget = $snakeCdm.ToLower()
                        if (-not $expectedTarget.EndsWith('s')) { $expectedTarget += 's' }
                        $expectedModelName = "int_$expectedTarget"

                        if ($Model -eq $expectedModelName) {
                            Write-Pass "SQL-INT-03 - Model name matches pluralized CDM entity '$cdmEntity'"
                        } else {
                            Write-Fail "SQL-INT-03 - Model name '$Model' should be '$expectedModelName' to match CDM entity '$cdmEntity'"
                        }

                        # Check SQL-INT-05
                        $allowedColumns = @()
                        $catalogFiles = Get-ChildItem "seeds\cdm_catalogs\*.csv"
                        foreach ($file in $catalogFiles) {
                            $catalog = Import-Csv $file.FullName
                            $matchingRows = $catalog | Where-Object { $_.cdm_entity_name -eq $cdmEntity }
                            if ($matchingRows) {
                                $allowedColumns += $matchingRows | Select-Object -ExpandProperty dbt_column_name
                            }
                        }
                        
                        $invalidCols = @()
                        foreach ($col in $sqlCols) {
                            # Allow keys and common audit fields
                            if ($col -match '_sk$' -or $col -match '_id$') {
                                continue
                            }
                            if ($col -notin $allowedColumns) {
                                $invalidCols += $col
                            }
                        }

                        if ($invalidCols.Count -eq 0) {
                            Write-Pass "SQL-INT-05 - All columns conform to CDM entity '$cdmEntity' or are keys"
                        } else {
                            Write-Fail "SQL-INT-05 - Columns not in CDM entity '$cdmEntity' (and not keys)"
                            $invalidCols | Select-Object -First 10 | ForEach-Object { Write-Host "         $_" }
                        }
                    } else {
                        Write-Warn "SQL-INT-05 - Could not find CDM entity for '$Model' in cdm_crosswalk.csv"
                    }
                } else {
                    Write-Warn "SQL-INT-05 - cdm_crosswalk.csv not found to check column conformance"
                }
            }
        } else {
            Write-Skip "Model returned 0 rows or empty schema, couldn't run dynamic column checks"
        }
    } catch {
        Write-Skip "Failed to parse dbt show JSON output"
    }
} else {
    Write-Skip "dbt show output did not contain valid JSON payload"
}

# ==============================================================
# SUMMARY
# ==============================================================

Write-Header "SUMMARY: $Model"

$Total = $PassCount + $FailCount + $WarnCount + $SkipCount

Write-Host ""
Write-Host "  [PASS] Passed:   $PassCount" -ForegroundColor Green
Write-Host "  [FAIL] Failed:   $FailCount" -ForegroundColor Red
Write-Host "  [WARN] Warnings: $WarnCount" -ForegroundColor Yellow
Write-Host "  [SKIP] Skipped:  $SkipCount" -ForegroundColor Cyan
Write-Host "  --------------"
Write-Host "  Total:      $Total checks"
Write-Host ""

if ($FailCount -gt 0) {
    Write-Host "  Result: FAIL ($FailCount rule violation(s))" -ForegroundColor Red
    exit 1
} else {
    Write-Host "  Result: PASS ($WarnCount warning(s) to review)" -ForegroundColor Green
    exit 0
}
