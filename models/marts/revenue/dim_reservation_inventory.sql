with

int_customer_assets as (
    select * from {{ ref('int_customer_assets') }}
),

int_parks as (
    select * from {{ ref('int_parks') }}
),

inventory_enriched as (
    select
        int_customer_assets.customer_assets_sk,
        int_customer_assets._parent_park_sk as parks_sk,

        int_customer_assets.name as asset_name,
        int_customer_assets.asset_type,
        int_parks.name as park_assignment,
        int_customer_assets.max_occupancy as capacity,

        case
            when int_customer_assets.is_ada_accessible then 'ADA Accessible'
            else 'Standard'
        end as accessibility_status,

        concat_ws(
            ', ',
            case
                when
                    int_customer_assets.pet_policy = 'allowed'
                    then 'Pets Allowed'
            end,
            case
                when
                    int_customer_assets.utility_hookup = 'full'
                    then 'Full Hookups'
            end
        ) as amenities,

        -- enrichments
        case
            when
                int_customer_assets.asset_type in (
                    'campsite', 'tent', 'rv', 'rv_site', 'tent_site'
                )
                then 'Camping'
            when
                int_customer_assets.asset_type in ('cabin', 'yurt', 'lodge')
                then 'Lodging'
            when
                int_customer_assets.asset_type in (
                    'shelter', 'day-use', 'picnic_area'
                )
                then 'Day Use'
            else 'Other'
        end as asset_type_group,

        case
            when int_customer_assets.max_occupancy <= 4 then 'Small (1-4)'
            when
                int_customer_assets.max_occupancy between 5 and 8
                then 'Medium (5-8)'
            when int_customer_assets.max_occupancy > 8 then 'Large (9+)'
            else 'Unknown'
        end as capacity_tier

    from int_customer_assets
    left join int_parks
        on int_customer_assets._parent_park_sk = int_parks.parks_sk
)

select * from inventory_enriched
