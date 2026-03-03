with

source as (
    select * from {{ source('trafficcount', 'vehicle_counts') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.count_id']) }} as hk_vehicle_count,
        cast(source.count_id as varchar) as count_id,
        cast(source.sensor_id as varchar) as sensor_id,
        cast(source.timestamp_hour as timestamp) as timestamp_hour,
        cast(source.raw_vehicle_count as integer) as raw_vehicle_count,
        cast(source.is_anomaly as boolean) as is_anomaly,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
