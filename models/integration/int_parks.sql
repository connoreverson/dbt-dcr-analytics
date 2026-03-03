with

source_geo as (
    select * from {{ ref('stg_geoparks__parks_master') }}
),

source_vista as (
    select * from {{ ref('stg_vistareserve__parks') }}
),

/*
    InfraTrak covers Regions 1 & 2 only (28 of 50 parks). Regions 3 & 4 remain
    on paper-based processes and will not appear in this source until full rollout.
*/
source_infratrak as (
    select * from {{ ref('stg_infratrak__parks') }}
),

cdm_geo as (
    select
        {{ dbt_utils.generate_surrogate_key(['geo_park_id']) }} as parks_sk,
        geo_park_id as accountnumber,
        park_name as name,  -- noqa: RF04
        gis_steward as description,
        total_acres,
        cast(null as varchar) as classification,
        cast(null as integer) as region_id,
        null as address1_city,
        null as address1_stateorprovince,
        null as address1_postalcode,
        null as address1_latitude,
        null as address1_longitude,
        cast(null as integer) as infratrak_park_id,
        {{ generate_source_system_tag('DCR-GEO-01') }} as source_system
    from source_geo
),

cdm_vista as (
    select
        {{ dbt_utils.generate_surrogate_key(['park_id']) }} as parks_sk,
        park_id as accountnumber,
        park_name as name,  -- noqa: RF04
        null as description,
        cast(null as decimal(10, 2)) as total_acres,
        classification,
        region_id,
        null as address1_city,
        null as address1_stateorprovince,
        null as address1_postalcode,
        null as address1_latitude,
        null as address1_longitude,
        cast(null as integer) as infratrak_park_id,
        {{ generate_source_system_tag('DCR-REV-01') }} as source_system
    from source_vista
),

/*
    Open Question #2: InfraTrak–GeoParks Park ID Reconciliation
    InfraTrak uses a separate integer park_id namespace from GeoParks (geo_park_id)
    and VistaReserve (park_id). The VistaReserve asset-level crosswalk
    (stg_vistareserve__asset_crosswalks) maps asset tags between systems but
    provides no park-level ID mapping. The crosswalk has also been unmaintained
    since 2022 (see days_since_last_update in the crosswalk staging model).
    InfraTrak park records are reconciled via the same fuzzy name matching used
    for GeoParks/VistaReserve deduplication. The infratrak_park_id column
    preserves the original ID to support downstream joins to InfraTrak work orders
    and condition assessments.
*/
cdm_infratrak as (
    select
        {{ dbt_utils.generate_surrogate_key(['park_id']) }} as parks_sk,
        cast(park_id as varchar) as accountnumber,
        park_name as name,  -- noqa: RF04
        null as description,
        cast(null as decimal(10, 2)) as total_acres,
        classification,
        region_id,
        null as address1_city,
        null as address1_stateorprovince,
        null as address1_postalcode,
        null as address1_latitude,
        null as address1_longitude,
        park_id as infratrak_park_id,
        {{ generate_source_system_tag('DCR-AST-01') }} as source_system
    from source_infratrak
),

union_sources as (
    select * from cdm_geo
    union all
    select * from cdm_vista
    union all
    select * from cdm_infratrak
),

/*
    Open Question #1: Park ID Reconciliation
    Due to the lack of a unified crosswalk ID between GeoParks and
    VistaReserve, we are heuristically deduplicating based on fuzzy
    string matching of the park names (stripping punctuation/casing).
    GeoParks is designated the system of record, so its attributes win
    in the event of a tie.
*/
dedup_sources as (
    select
        *,
        max(total_acres) over (
            partition by {{ clean_string('name') }}
        ) as combined_total_acres,
        max(classification) over (
            partition by {{ clean_string('name') }}
        ) as combined_classification,
        max(region_id) over (
            partition by {{ clean_string('name') }}
        ) as combined_region_id,
        max(infratrak_park_id) over (
            partition by {{ clean_string('name') }}
        ) as combined_infratrak_park_id,
        row_number() over (
            partition by {{ clean_string('name') }}
            order by
                case when source_system = 'DCR-GEO-01' then 1 else 2 end,
                parks_sk
        ) as rn
    from union_sources
),

final as (
    select
        parks_sk,
        accountnumber,
        name,
        description,
        address1_city,
        address1_stateorprovince,
        address1_postalcode,
        address1_latitude,
        address1_longitude,
        source_system,
        combined_total_acres as total_acres,
        combined_classification as classification,
        combined_region_id as region_id,
        combined_infratrak_park_id as infratrak_park_id
    from dedup_sources
    where rn = 1
)

select * from final
