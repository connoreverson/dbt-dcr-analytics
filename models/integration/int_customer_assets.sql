-- depends_on: {{ ref('int_cdm_columns') }}
-- depends_on: {{ ref('cdm_crosswalk') }}

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
        source_parks.parks_sk as _parent_park_sk,
        {{ generate_source_system_tag('DCR-REV-01') }} as source_system
    from source_assets
    left join
        source_parks
        on {{ get_geoparks_account_number('source_assets.park_id') }} = source_parks.accountnumber
),

final as (
    {{ generate_cdm_projection(
        integration_model='int_customer_assets', 
        source_model='stg_vistareserve__inventory_assets', 
        cte_name='joined_assets',
        sk_source_columns=['asset_id'],
        pass_through_columns=[
            '_parent_park_sk', 
            'name',
            'asset_type',
            'pet_policy',
            'utility_hookup',
            'max_occupancy',
            'is_ada_accessible',
            'source_system'
        ]
    ) }}
)

select * from final
