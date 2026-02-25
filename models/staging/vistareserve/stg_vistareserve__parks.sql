with

source as (
    select * from {{ source('vistareserve', 'parks') }}
),

final as (

    select
        --  ids
        cast(source.park_id as integer) as park_id,
        cast(source.region_id as integer) as region_id,
        --  strings
        cast(source.classification as varchar) as classification,
        cast(source.park_name as varchar) as park_name,
        --  booleans
        cast(source.has_unstaffed_kiosk as boolean) as has_unstaffed_kiosk
    from source

)

select * from final
