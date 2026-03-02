with

source as (
    select * from {{ source('granttrack', 'active_awards') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.award_id']) }} as hk_award,
        --  ids
        cast(source.award_id as varchar) as award_id,
        cast(source.application_id as varchar) as application_id,
        cast(source.award_number as varchar) as award_number,
        --  federal appropriation reference linking to StateGov financials
        cast(source.sgf_appropriation_code as varchar) as sgf_appropriation_code,
        --  attributes
        cast(source.required_match_percentage as decimal(5, 2)) as required_match_percentage,
        --  amounts
        cast(source.award_amount as decimal(12, 2)) as award_amount,
        --  dates
        cast(source.performance_start as date) as performance_start,
        cast(source.performance_end as date) as performance_end
    from source
)

select * from final
