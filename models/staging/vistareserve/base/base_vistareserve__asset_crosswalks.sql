with

source as (
    select * from {{ source('vistareserve', 'asset_crosswalk') }}
)

select
    vista_asset_id,
    geoparks_feature_id,
    infratrak_asset_tag,
    last_verified_date,
    'vistareserve' as source_system,
    date_diff('day', last_verified_date, current_date)
        as days_since_last_update
from source
