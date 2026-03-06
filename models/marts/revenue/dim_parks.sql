with

int_parks as (
    select * from {{ ref('int_parks') }}
),

regions as (
    select * from {{ ref('park_region_mappings') }}
),

parks_joined as (
    select
        int_parks.parks_sk,
        int_parks.name as park_name,
        int_parks.total_acres,
        int_parks.classification as park_type,
        int_parks.address1_city,
        int_parks.address1_stateorprovince,
        int_parks.address1_postalcode,
        int_parks.address1_latitude,
        int_parks.address1_longitude,
        int_parks.source_system,
        int_parks.infratrak_park_id,
        regions.region_name as region
    from int_parks
    left join regions
        on 'R' || cast(int_parks.region_id as varchar) = regions.region_code
),

parks_enriched as (
    select
        parks_sk,
        park_name,
        region,
        park_type,
        infratrak_park_id,

        cast(total_acres as decimal(10, 2)) as acreage,
        cast(address1_city as varchar) as address1_city,
        cast(address1_stateorprovince as varchar)
            as address1_stateorprovince,
        cast(address1_postalcode as varchar) as address1_postalcode,
        cast(address1_latitude as decimal(10, 6))
            as address1_latitude,
        cast(address1_longitude as decimal(10, 6))
            as address1_longitude,

        case
            when source_system = 'DCR-GEO-01' then 'Active - Verified'
            else 'Active - Unverified'
        end as operational_status,

        case
            when
                cast(total_acres as float) < 500
                then 'Small (< 500 acres)'
            when
                cast(total_acres as float) between 500 and 5000
                then 'Medium (500 - 5000 acres)'
            when
                cast(total_acres as float) > 5000
                then 'Large (> 5000 acres)'
            else 'Unknown'
        end as acreage_size_tier
    from parks_joined
)

select * from parks_enriched
