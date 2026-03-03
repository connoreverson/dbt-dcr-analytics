with

source_gl as (
    select * from {{ ref('stg_stategov__general_ledger') }}
),

source_coa as (
    select * from {{ ref('stg_stategov__chart_of_accounts') }}
),

/*
    GrantTrack active awards carry an SGF appropriation code that links a
    federal grant to a StateGov fund code. Multiple awards may reference the
    same fund code across overlapping performance periods; we retain the most
    recently active award (latest performance_end) to prevent fan-out on the GL join.
*/
source_awards as (
    select
        sgf_appropriation_code,
        award_id,
        award_number,
        award_amount,
        required_match_percentage,
        performance_start,
        performance_end,
        row_number() over (
            partition by sgf_appropriation_code
            order by performance_end desc nulls last, award_id asc
        ) as rn
    from {{ ref('stg_granttrack__active_awards') }}
),

dedup_awards as (
    select * from source_awards
    where rn = 1
),

/*
    Grant budget context: GrantTrack records budgeted vs. actual spending
    by award and fiscal year. Joined to provide budget context for grant-funded
    GL entries. NULL for GL entries that are not grant-funded.
*/
source_award_budget as (
    select * from {{ ref('stg_granttrack__award_budget_by_fiscal_year') }}
),

/*
    Enrich each GL entry with:
    1. Chart of accounts labels — fund, division, program, and object code descriptions
       sourced from the StateGov financial hierarchy.
    2. Grant attribution — the active GrantTrack award whose SGF appropriation code
       matches the GL entry's account fund code. NULL for general-fund entries.
    3. Award budget context — GrantTrack's budgeted and actual amounts for the
       matching award × fiscal year. Supports budget-vs-actual analysis in the mart layer.

    The batch_detail_text column (pipe-delimited invoice memo) is carried raw;
    unpacking its embedded invoice records to rows is a mart-layer responsibility.
*/
final as (
    select
        {{ dbt_utils.generate_surrogate_key(['gl.gl_entry_id']) }} as financials_sk,
        gl.gl_entry_id,
        gl.fiscal_year,
        gl.accounting_month,
        gl.entry_type,
        gl.amount,
        -- Account classification (compound account code and parsed components)
        gl.account_id,
        gl.account_fund_code,
        gl.account_division_code,
        gl.account_program_code,
        gl.account_object_code,
        -- Descriptive labels from the StateGov chart of accounts
        coa.fund_description,
        coa.division_description,
        coa.program_description,
        coa.object_description,
        -- Batch audit fields
        gl.batch_reference,
        gl.batch_detail_text,
        gl.batch_entry_count,
        -- Grant attribution (null for non-grant-funded GL entries)
        awards.award_id,
        awards.award_number,
        awards.award_amount,
        awards.required_match_percentage,
        awards.performance_start,
        awards.performance_end,
        -- Grant budget context for the matching award × fiscal year
        award_budget.budgeted_amount as award_fiscal_year_budget,
        award_budget.actual_amount as award_fiscal_year_actual,
        {{ generate_source_system_tag('DCR-FIN-01') }} as source_system
    from source_gl as gl
    left join source_coa as coa
        on gl.account_id = coa.account_id
    left join dedup_awards as awards
        on gl.account_fund_code = awards.sgf_appropriation_code
    left join source_award_budget as award_budget
        on
            awards.award_id = award_budget.award_id
            and gl.fiscal_year = award_budget.fiscal_year
)

select * from final
