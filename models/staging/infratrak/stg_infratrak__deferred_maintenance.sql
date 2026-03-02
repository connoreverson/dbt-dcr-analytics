with

source as (
    select * from {{ source('infratrak', 'deferred_maintenance') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.backlog_id']) }} as hk_deferred_maintenance,
        --  ids
        cast(source.backlog_id as varchar) as backlog_id,
        cast(source.asset_tag as varchar) as asset_tag,
        --  amounts
        cast(source.estimated_repair_cost as decimal(12, 2)) as estimated_repair_cost,
        --  flags
        cast(source.is_funded as boolean) as is_funded,
        --  dates
        cast(source.calculation_date as date) as calculation_date
    from source
)

select * from final
