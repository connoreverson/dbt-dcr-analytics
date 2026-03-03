with

source as (
    select * from {{ source('trafficcount', 'derived_visitor_metrics') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.metric_id']) }} as hk_visitor_metric,
        cast(source.metric_id as varchar) as metric_id,
        cast(source.sensor_id as varchar) as sensor_id,
        cast(source.target_date as date) as target_date,
        cast(source.estimated_total_visitors as integer) as estimated_total_visitors,
        cast(source.vehicle_multiplier_used as decimal(3, 2)) as vehicle_multiplier_used,
        cast(source.calculation_timestamp as timestamp) as calculation_timestamp,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
