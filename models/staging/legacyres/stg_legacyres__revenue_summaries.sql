with

source as (
    select * from {{ source('legacyres', 'legacy_revenue_summaries') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.summary_id']) }} as hk_revenue_summaries,
        --  ids
        cast(source.summary_id as varchar) as summary_id,
        cast(source.legacy_park_id as varchar) as legacy_park_id,
        --  dates
        cast(source.report_month as date) as report_month,
        --  strings
        cast(source.revenue_category as varchar) as revenue_category,
        --  numerics
        cast(source.total_revenue as decimal(10, 2)) as total_revenue
    from source

)

select * from final
