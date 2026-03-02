with

source_parks as (
    select * from {{ ref('int_parks') }}
),

source_assets as (
    select * from {{ ref('stg_vistareserve__inventory_assets') }}
),

joined_assets as (
    select
        source_assets.*,
        source_assets.asset_id as name,  -- noqa: RF04
        source_parks.parks_sk as _parent_park_sk
    from source_assets
    left join
        source_parks
        on
            {{ get_geoparks_account_number('source_assets.park_id') }}
            = source_parks.accountnumber
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['asset_id']) }} as customer_assets_sk,
        asset_id as customerasset_id,
        _parent_park_sk,
        name
    from joined_assets
)

select * from final
