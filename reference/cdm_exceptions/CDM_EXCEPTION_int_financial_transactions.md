# CDM Entity Exception Request

## Form: Custom Entity Justification for Integration Model

**Model:** `int_financial_transactions`
**Date:** 2026-03-03
**Requested by:** Engineering (dbt implementation team)
**Standards impacted:** SQL-INT-03 (Entity Name Word Choice), SQL-INT-05 (CDM Column Conformance)

---

## 1. Business Entity Being Modeled

**Entity name:** FinancialTransaction (a general ledger entry in the DCR operating budget)
**Grain:** One row per GL entry from the StateGov Financials (SGF) mainframe, enriched with chart of accounts labels and optional grant attribution where the entry's fund code matches an active federal award
**Source systems:** StateGov Financials (DCR-FIN-01: general ledger, chart of accounts), GrantTrack (DCR-FIN-02: active awards, award budget by fiscal year)
**Business definition:** A financial transaction represents a single posting to DCR's general ledger as recorded by the statewide COBOL mainframe. Each entry carries a compound account identifier (fund–division–program–object), a fiscal year and accounting month, an entry type (Expenditure or Revenue), and a monetary amount. Where the entry's fund code matches a federal grant award in GrantTrack, the entry is enriched with award metadata and fiscal-year budget context. This entity is the atomic unit for expenditure analysis, object-code trending, and grant-to-spending reconciliation.

---

## 2. Candidate CDM Entities Evaluated

Coverage analysis via `dbt run-operation identify_candidate_cdm --args '{model_name: "int_financial_transactions"}'` produced the following top candidates:

| CDM Entity | Matched / Total | Coverage % |
|---|---|---|
| Park (DCR extension) | 1 / 14 | 7.1% |
| DisbursementDistribution | 1 / 30 | 3.3% |
| Transaction | 1 / 48 | 2.1% |
| IndicatorValue | 1 / 51 | 2.0% |
| DesignatedCredit | 1 / 80 | 1.3% |
| Disbursement | 1 / 220 | 0.5% |

Only `source_system` matched across candidates (a project-wide infrastructure column). No business-content columns matched any CDM entity.

### 2a. Transaction (applicationCommon 1.5)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 48 columns. The single match is `amount`. |
| **Semantic fit** | Partial. CDM Transaction represents a "financial transaction between a buyer and a seller" — it covers CRM payment events (invoice, payment, credit memo). It does not model government fund accounting with hierarchical account codes (fund/division/program/object), fiscal-year periodicity, appropriation-level control, or the batch-aggregate structure of mainframe GL exports. |
| **Unmappable attributes** | `fiscal_year`, `accounting_month`, `entry_type`, `account_fund_code`, `account_division_code`, `account_program_code`, `account_object_code`, `fund_description`, `division_description`, `program_description`, `object_description`, `batch_reference`, `batch_detail_text`, `batch_entry_count` have no semantic equivalent in Transaction. Grant attribution columns (`award_number`, `required_match_percentage`, `performance_start`, `performance_end`, budget/actual) also lack equivalents. |
| **Verdict** | Rejected. One column match out of 23 business columns (4%) is not semantic coverage. The entity is designed for commercial transaction processing, not government fund accounting. |

### 2b. DisbursementDistribution (nonProfitCore)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 30 columns. No business columns matched; the single match is `source_system`. |
| **Semantic fit** | Poor. DisbursementDistribution represents the allocation of a nonprofit payment disbursement across designated funds. While DCR grants involve disbursements, `int_financial_transactions` is built at the GL entry grain — not the disbursement allocation grain. DCR is the grant recipient, not the disburser. |
| **Unmappable attributes** | All 23 business columns (fiscal_year, account hierarchy, entry_type, batch fields, grant attribution) are unmappable. |
| **Verdict** | Rejected. Wrong perspective (disburser vs. recipient), wrong grain, and zero business column overlap. |

### 2c. Disbursement (nonProfitCore)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 220 columns. The single match is `source_system`. |
| **Semantic fit** | Poor. Disbursement in the CDM NonProfit context represents a payment issued by a foundation or granting agency to a recipient. DCR is the recipient; the disbursements to DCR are recorded in GrantTrack as award draws, not in the SGF general ledger as first-class entities. The GL records the expenditure side — what DCR spends the funds on — not the receipt of grant proceeds. |
| **Unmappable attributes** | All 23 business columns are unmappable. |
| **Verdict** | Rejected. Models the grantor-side payment event; DCR is on the recipient side. The GL is an expenditure ledger, not a disbursement register. |

### 2d. DesignatedCredit (nonProfitCore)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 80 columns. The single match is `source_system`. |
| **Semantic fit** | Poor. DesignatedCredit represents a donor's designation of a gift to a specific nonprofit fund. DCR's federal grants are not donor-designated gifts; they are performance-based awards with matching requirements and compliance deadlines. |
| **Unmappable attributes** | All 23 business columns are unmappable. |
| **Verdict** | Rejected. Designed for donor fund management, not government grant expenditure tracking. |

---

## 3. Conclusion: No Standard CDM Entity Is Appropriate

No entity in the curated CDM manifests (applicationCommon, nonProfitCore, Asset, Visits, cdmfoundation) provides both semantic correctness and adequate column coverage for a government general ledger entry. The core mismatch is structural: the Microsoft CDM was designed for commercial CRM, healthcare, and nonprofit fundraising. Government fund accounting — with its hierarchical account codes, appropriation-period controls, and regulatory reporting requirements — is not represented in any standard manifest.

The closest candidate, `Transaction`, covers the abstract concept of a financial event but omits the entire fund accounting apparatus: the chart of accounts hierarchy, fiscal-year periodicity, appropriation/allotment/expenditure/revenue entry types, and the encumbrance-to-reimbursement-to-award linkage required to reconcile SGF spending against GrantTrack award activity.

---

## 4. Proposed Custom Entity: `FinancialTransaction`

### 4a. Entity Definition

| Property | Value |
|---|---|
| **Entity name** | `FinancialTransaction` |
| **Extends** | `Transaction` (applicationCommon) — inherits the abstract financial event concept |
| **Manifest context** | Custom extension (`dcr/FinancialTransaction.1.0`) within the applicationCommon family |
| **Integration model** | `int_financial_transactions` |
| **Description** | A general ledger entry in the DCR state operating budget, classified by fund accounting hierarchy (fund, division, program, object code), attributed to a federal grant award where applicable, and enriched with GrantTrack budget context for grant-funded entries. |

### 4b. Column Definitions

| Column | Data Type | Source | CDM Lineage | Role |
|---|---|---|---|---|
| `financials_sk` | `VARCHAR` | Generated | Surrogate key (SQL-INT-06) | PK |
| `gl_entry_id` | `VARCHAR` | SGF: `general_ledger.gl_entry_id` | Business key — natural identifier from the mainframe | BK |
| `fiscal_year` | `INTEGER` | SGF: `general_ledger.fiscal_year` | **Custom extension** — state fiscal year (e.g., 2024 = FY ending June 30, 2024) | Temporal |
| `accounting_month` | `INTEGER` | SGF: `general_ledger.accounting_month` | **Custom extension** — accounting period within the fiscal year (1–12) | Temporal |
| `entry_type` | `VARCHAR` | SGF: `general_ledger.entry_type` | **Custom extension** — classification of the GL posting (Expenditure or Revenue) | Classification |
| `amount` | `DECIMAL(12,2)` | SGF: `general_ledger.amount` | Modeled after `Transaction.amount` — the monetary value of the GL posting | Measure |
| `account_id` | `VARCHAR` | SGF: `general_ledger.account_id` | **Custom extension** — compound account code in {fund}-DIV-{div}-PRG-{prog}-OBJ-{obj} format | Account |
| `account_fund_code` | `VARCHAR` | SGF: parsed from `account_id` | **Custom extension** — fund component of the compound account; links to grant awards | Account |
| `account_division_code` | `VARCHAR` | SGF: parsed from `account_id` | **Custom extension** — division component of the compound account | Account |
| `account_program_code` | `VARCHAR` | SGF: parsed from `account_id` | **Custom extension** — program component of the compound account | Account |
| `account_object_code` | `VARCHAR` | SGF: parsed from `account_id` | **Custom extension** — object code classifying the expenditure/revenue type | Account |
| `fund_description` | `VARCHAR` | SGF: `chart_of_accounts.fund_description` | **Custom extension** — human-readable fund label from the chart of accounts | Label |
| `division_description` | `VARCHAR` | SGF: `chart_of_accounts.division_description` | **Custom extension** — human-readable division label | Label |
| `program_description` | `VARCHAR` | SGF: `chart_of_accounts.program_description` | **Custom extension** — human-readable program label | Label |
| `object_description` | `VARCHAR` | SGF: `chart_of_accounts.object_description` | **Custom extension** — human-readable object code label | Label |
| `batch_reference` | `VARCHAR` | SGF: `general_ledger.batch_reference` | **Custom extension** — mainframe batch identifier for audit traceability | Audit |
| `batch_detail_text` | `VARCHAR` | SGF: `general_ledger.batch_detail_text` | **Custom extension** — raw pipe-delimited invoice memo (INV|amount|description|date) | Audit |
| `batch_entry_count` | `INTEGER` | SGF: derived | **Custom extension** — count of embedded invoice records in the batch memo | Audit |
| `award_id` | `VARCHAR` | GrantTrack: `active_awards.award_id` | **Custom extension** — GrantTrack award identifier; null for non-grant entries | Grant |
| `award_number` | `VARCHAR` | GrantTrack: `active_awards.award_number` | **Custom extension** — official federal award number; null for non-grant entries | Grant |
| `award_amount` | `DECIMAL(12,2)` | GrantTrack: `active_awards.award_amount` | **Custom extension** — total ceiling amount of the federal award | Grant |
| `required_match_percentage` | `DECIMAL(5,2)` | GrantTrack: `active_awards.required_match_percentage` | **Custom extension** — minimum non-federal match contribution required | Grant |
| `performance_start` | `DATE` | GrantTrack: `active_awards.performance_start` | **Custom extension** — start of the award performance period | Grant |
| `performance_end` | `DATE` | GrantTrack: `active_awards.performance_end` | **Custom extension** — end of the award performance period | Grant |
| `award_fiscal_year_budget` | `DECIMAL(14,2)` | GrantTrack: `award_budget_by_fiscal_year.budgeted_amount` | **Custom extension** — GrantTrack budgeted amount for this award × fiscal year | Grant Budget |
| `award_fiscal_year_actual` | `DECIMAL(14,2)` | GrantTrack: `award_budget_by_fiscal_year.actual_amount` | **Custom extension** — GrantTrack actual spending for this award × fiscal year (note: 2–5% reconciliation gap vs. SGF is a known quality issue) | Grant Budget |
| `source_system` | `VARCHAR` | Generated | Infrastructure column — always DCR-FIN-01 (SGF is the authoritative base grain) | Audit |

### 4c. Normalization and Relationships

The `FinancialTransaction` entity is in **third normal form**. The chart of accounts labels (`fund_description`, `division_description`, etc.) are denormalized from the COA dimension for analytical convenience; they are functionally dependent on the account code components (`account_fund_code`, `account_object_code`, etc.) which are in turn components of `gl_entry_id`. This is an intentional integration-layer choice to avoid requiring all mart consumers to re-join the COA dimension.

**Known data quality notes:**
- The `batch_detail_text` field contains raw pipe-delimited invoice data that is unpacked in the mart layer.
- `award_fiscal_year_actual` from GrantTrack carries a known 2–5% reconciliation gap versus SGF actuals (see `reference/data_inventory_summary.md`, DCR-FIN-02). Do not sum both in the same aggregation without adjustment.
- Multiple active awards may target the same SGF fund code over overlapping periods; `int_financial_transactions` retains the most recently active award (latest `performance_end`) to maintain GL entry grain. Historical multi-award analysis should join directly to the staging layer.

**Relationship to other integration models:**
- `int_financial_transactions` currently has no FK references to other integration models. The account hierarchy is self-contained within SGF. The `award_id` links back to GrantTrack staging; a future `int_grants` model could absorb the GrantTrack grant application and compliance data and establish a formal FK here.

---

## 5. Implementation Path

1. **Add `FinancialTransaction` entity rows to CDM catalog seed.** Add column definitions to `seeds/cdm_catalogs/column_catalog_dcr_extensions.csv` with `cdm_entity_name = 'FinancialTransaction'`.
2. **Update `seeds/cdm_crosswalk.csv`.** Add rows mapping `int_financial_transactions` to the `FinancialTransaction` entity for each SGF and GrantTrack source column.
3. **Update `models/integration/_models.yml`.** Already done: `meta: cdm_entity: FinancialTransaction` and `meta: cdm_entity_rationale:` referencing this document.
4. **No SQL changes required.** The model's column names, logic, and tests are correct as-built.
5. **Run `check_model.py` to verify conformance.** The checker validates `int_financial_transactions` columns against the `FinancialTransaction` entity definition in the seeds.

---

## 6. Precedent and Governance Note

This exception follows the same pattern established by `CDM_EXCEPTION_int_parks.md`. The CDM's nonProfitCore manifest includes grant/disbursement entities, but they model the *grantor* perspective (foundations, federal agencies). DCR is a *grant recipient* whose financial data lives in a state government general ledger. The mismatch is fundamental, not incidental.

The `FinancialTransaction` custom entity is designed to support the `fct_expenditures` mart (Task 3.3): summarizing GL spending by object code, attributing grant-funded entries to awards, and enabling the budget-vs.-actual reconciliation between SGF and GrantTrack. Future integration models for accounts payable (`int_accounts_payable`), encumbrances (`int_encumbrances`), or vendor payments would likely extend this entity or define companion custom entities within the same `dcr/FinancialTransaction` family.
