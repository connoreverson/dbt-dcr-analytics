with

source as (
    select * from {{ source('vistareserve', 'inventory_assets') }}
),

final as (

    select
        --  ids
        cast(source.asset_id as varchar) as asset_id,
        cast(source.park_id as integer) as park_id,
        --  strings
        cast(source.asset_type as varchar) as asset_type,
        cast(source.pet_policy as varchar) as pet_policy,
        cast(source.utility_hookup as varchar) as utility_hookup,
        --  numerics
        cast(source.max_occupancy as integer) as max_occupancy,
        --  booleans
        cast(source.ada_accessible as boolean) as is_ada_accessible
    from source

)

select * from final
