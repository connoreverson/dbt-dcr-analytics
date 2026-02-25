with

source as (
    select * from {{ source('geoparks', 'parks_master') }}
),

final as (

    select
        --  ids
        cast(source.geo_park_id as varchar) as geo_park_id,
        --  strings
        cast(source.gis_steward as varchar) as gis_steward,
        cast(source.park_name as varchar) as park_name,
        --  numerics
        cast(source.total_acres as decimal(10, 2)) as total_acres
    from source

)

select * from final
