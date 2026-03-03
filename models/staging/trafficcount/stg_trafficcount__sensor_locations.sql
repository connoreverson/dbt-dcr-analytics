with

source as (
    select * from {{ source('trafficcount', 'sensor_locations') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.sensor_id']) }} as hk_sensor,
        cast(source.sensor_id as varchar) as sensor_id,
        cast(source.park_id as varchar) as park_id,
        cast(source.installation_date as date) as installation_date,
        cast(source.sensor_type as varchar) as sensor_type,
        cast(source.location_description as varchar) as location_description,
        cast(source.status as varchar) as status,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
