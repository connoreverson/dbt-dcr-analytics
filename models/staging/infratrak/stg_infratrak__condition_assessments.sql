with

source as (
    select * from {{ source('infratrak', 'condition_assessments') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.assessment_id']) }} as hk_condition_assessment,
        --  ids
        cast(source.assessment_id as varchar) as assessment_id,
        cast(source.asset_tag as varchar) as asset_tag,
        cast(source.inspector_id as varchar) as inspector_id,
        --  score: Facility Condition Index — standardised 1–100 scale;
        --  higher values indicate better condition (FCI ≥ 70 = "good")
        cast(source.fci_score as integer) as fci_score,
        --  audit
        cast(source.notes as varchar) as notes,
        --  dates
        cast(source.inspection_date as date) as inspection_date
    from source
)

select * from final
