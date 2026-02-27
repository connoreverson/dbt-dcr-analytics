-- depends_on: {{ ref('int_cdm_columns') }}
-- depends_on: {{ ref('cdm_crosswalk') }}

with

source_geo as (
    select * from {{ ref('stg_geoparks__parks_master') }}
),

source_vista as (
    select * from {{ ref('stg_vistareserve__parks') }}
),

cdm_geo as (
    {{ generate_cdm_projection(
        integration_model='int_parks',
        source_model='stg_geoparks__parks_master',
        cte_name='source_geo',
        sk_source_columns=['geo_park_id'],
        pass_through_columns=[
            'total_acres',
            'cast(null as varchar) as classification',
            'cast(null as integer) as region_id',
            'null as address1_city',
            'null as address1_stateorprovince',
            'null as address1_postalcode',
            'null as address1_latitude',
            'null as address1_longitude',
            generate_source_system_tag('DCR-GEO-01') ~ " as source_system"
        ]
    ) }}
),

cdm_vista as (
    {{ generate_cdm_projection(
        integration_model='int_parks',
        source_model='stg_vistareserve__parks',
        cte_name='source_vista',
        sk_source_columns=['park_id'],
        pass_through_columns=[
            'null as description',
            'cast(null as decimal(10, 2)) as total_acres',
            'classification',
            'region_id',
            'null as address1_city',
            'null as address1_stateorprovince',
            'null as address1_postalcode',
            'null as address1_latitude',
            'null as address1_longitude',
            generate_source_system_tag('DCR-REV-01') ~ " as source_system"
        ]
    ) }}
),

union_sources as (
    select * from cdm_geo
    union all
    select * from cdm_vista
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
        combined_region_id as region_id
    from dedup_sources
    where rn = 1
)

select * from final
