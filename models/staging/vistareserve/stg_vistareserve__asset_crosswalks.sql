with

source as (
    select * from {{ ref('base_vistareserve__asset_crosswalks') }}
),

final as (

    select
        --  ids
        cast(source.geoparks_feature_id as varchar) as geoparks_feature_id,
        cast(source.vista_asset_id as varchar) as vista_asset_id,
        --  strings
        cast(source.infratrak_asset_tag as varchar) as infratrak_asset_tag,
        cast(source.source_system as varchar) as source_system,
        --  numerics
        cast(source.days_since_last_update as integer)
            as days_since_last_update,
        --  dates/timestamps
        cast(source.last_verified_date as date) as last_verified_date
    from source

)

select * from final
