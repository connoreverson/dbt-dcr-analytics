with

int_parks as (
    select * from {{ ref('int_parks') }}
),

regions as (
    select * from {{ ref('park_region_mappings') }}
),

parks_enriched as (
    select
        int_parks.parks_sk,
        int_parks.name as park_name,
        regions.region_name as region,
        cast(int_parks.total_acres as decimal(10, 2)) as acreage,
        int_parks.classification as park_type,

        cast(int_parks.address1_city as varchar) as address1_city,

        cast(int_parks.address1_stateorprovince as varchar)
            as address1_stateorprovince,
        cast(int_parks.address1_postalcode as varchar) as address1_postalcode,
        cast(int_parks.address1_latitude as decimal(10, 6))
            as address1_latitude,
        cast(int_parks.address1_longitude as decimal(10, 6))
            as address1_longitude,
        case
            when int_parks.source_system = 'DCR-GEO-01' then 'Active - Verified'
            else 'Active - Unverified'
        end as operational_status,

        case
            when
                cast(int_parks.total_acres as float) < 500
                then 'Small (< 500 acres)'
            when
                cast(int_parks.total_acres as float) between 500 and 5000
                then 'Medium (500 - 5000 acres)'
            when
                cast(int_parks.total_acres as float) > 5000
                then 'Large (> 5000 acres)'
            else 'Unknown'
        end as acreage_size_tier

    from int_parks
    left join regions
        on 'R' || cast(int_parks.region_id as varchar) = regions.region_code
)

select * from parks_enriched
