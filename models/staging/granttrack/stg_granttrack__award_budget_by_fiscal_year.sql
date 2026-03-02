with

source as (
    select * from {{ source('granttrack', 'award_budget_by_fiscal_year') }}
),

--  three awards have exact duplicate rows in the source Excel export
--  (copy-paste artefact); retain one row per award_id using row_number
deduped as (
    select *
    from source
    qualify row_number() over (
        partition by award_id
        order by award_id
    ) = 1
),

--  unpivot Excel-pivoted FY columns to long format (one row per award × fiscal year)
--  mixed amount formats normalised: '$509,891.46', '509891.46', 'TBD' → DECIMAL or NULL
unpivoted as (
    select
        award_id,
        award_number,
        notes,
        2020 as fiscal_year,
        fy2020_budgeted as raw_budgeted,
        fy2020_actual as raw_actual
    from deduped
    union all
    select
        award_id,
        award_number,
        notes,
        2021 as fiscal_year,
        fy2021_budgeted as raw_budgeted,
        fy2021_actual as raw_actual
    from deduped
    union all
    select
        award_id,
        award_number,
        notes,
        2022 as fiscal_year,
        fy2022_budgeted as raw_budgeted,
        fy2022_actual as raw_actual
    from deduped
    union all
    select
        award_id,
        award_number,
        notes,
        2023 as fiscal_year,
        fy2023_budgeted as raw_budgeted,
        fy2023_actual as raw_actual
    from deduped
    union all
    select
        award_id,
        award_number,
        notes,
        2024 as fiscal_year,
        fy2024_budgeted as raw_budgeted,
        fy2024_actual as raw_actual
    from deduped
    union all
    select
        award_id,
        award_number,
        notes,
        2025 as fiscal_year,
        fy2025_budgeted as raw_budgeted,
        fy2025_actual as raw_actual
    from deduped
),

final as (
    select
        --  hash key — grain is one row per award per fiscal year
        {{ dbt_utils.generate_surrogate_key(['award_id', 'fiscal_year']) }} as hk_award_budget,
        --  ids
        cast(award_id as varchar) as award_id,
        cast(award_number as varchar) as award_number,
        --  period
        cast(fiscal_year as integer) as fiscal_year,
        --  amounts: strip dollar signs and commas; non-numeric text (e.g. 'TBD') yields null
        try_cast(
            regexp_replace(raw_budgeted, '[$,]', '', 'g') as decimal(14, 2)
        ) as budgeted_amount,
        try_cast(
            regexp_replace(raw_actual, '[$,]', '', 'g') as decimal(14, 2)
        ) as actual_amount,
        --  free-text notes carried from the award row
        cast(notes as varchar) as notes
    from unpivoted
    where raw_budgeted is not null or raw_actual is not null
)

select * from final
