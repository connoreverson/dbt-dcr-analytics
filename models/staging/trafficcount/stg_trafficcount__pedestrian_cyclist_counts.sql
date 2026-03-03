with

source as (
    select * from {{ source('trafficcount', 'pedestrian_cyclist_counts') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.count_id']) }} as hk_pedestrian_cyclist_count,
        cast(source.count_id as varchar) as count_id,
        cast(source.sensor_id as varchar) as sensor_id,
        cast(source.timestamp_hour as timestamp) as timestamp_hour,
        cast(source.raw_pedestrian_count as integer) as raw_pedestrian_count,
        cast(source.raw_cyclist_count as integer) as raw_cyclist_count,
        cast(source.is_anomaly as boolean) as is_anomaly,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
