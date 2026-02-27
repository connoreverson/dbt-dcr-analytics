with

source as (
    select * from {{ source('vistareserve', 'parks') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.park_id']) }} as hk_parks,
        --  ids
        {{ cast_park_id_to_varchar('source.park_id') }} as park_id,
        cast(source.region_id as integer) as region_id,
        --  strings
        cast(source.classification as varchar) as classification,
        cast(source.park_name as varchar) as park_name,
        --  booleans
        cast(source.has_unstaffed_kiosk as boolean) as has_unstaffed_kiosk
    from source

)

select * from final
