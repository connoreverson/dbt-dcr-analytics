with

source_infratrak as (
    select * from {{ ref('stg_infratrak__assets') }}
),

source_geoparks as (
    select * from {{ ref('stg_geoparks__infrastructure_features') }}
),

/*
    int_parks is the authoritative park dimension and resolves cross-system park IDs.
    InfraTrak assets use integer park_id; GeoParks features use varchar geo_park_id.
    Both can be joined to int_parks to obtain parks_sk.
*/
source_parks as (
    select
        parks_sk,
        infratrak_park_id,
        accountnumber as geo_park_id
    from {{ ref('int_parks') }}
),

/*
    InfraTrak EAM assets: the authoritative source for lifecycle, cost, and
    condition data on physical infrastructure in Regions 1 and 2. Each asset
    record carries a unique asset tag, geographic point coordinates,
    construction date, estimated replacement value, and design lifespan.
    Regions 3 and 4 have not been onboarded; their assets are covered only
    by the GeoParks geometry records below.

    NOTE: The VistaReserve cross-system crosswalk nominally links InfraTrak
    asset tags to GeoParks feature IDs, but the crosswalk was built against
    legacy identifier formats that predate the current INF-* and AST-*
    naming schemes. It cannot be used to match current records. No row-level
    join between InfraTrak assets and GeoParks features is therefore possible;
    both source populations are preserved as distinct rows.
*/
cdm_infratrak as (
    select
        {{ dbt_utils.generate_surrogate_key(['it.asset_tag']) }} as physical_assets_sk,
        it.asset_tag as asset_id,
        parks.parks_sk,
        it.asset_category as feature_class,
        it.asset_category as sub_type,
        it.description,
        it.construction_year as installation_year,
        it.replacement_value,
        it.expected_lifespan_years,
        it.latitude as point_latitude,
        it.longitude as point_longitude,
        cast(null as varchar) as geometry_wkt,
        cast(null as decimal(5, 2)) as positional_accuracy_meters,
        cast(null as date) as last_updated,
        cast(null as varchar) as status,
        it.is_visible_in_survey,
        {{ generate_source_system_tag('DCR-AST-01') }} as source_system
    from source_infratrak as it
    left join source_parks as parks
        on it.park_id = parks.infratrak_park_id
),

/*
    GeoParks infrastructure features: the authoritative source for geometry
    and GIS classification of all physical features across all 50 parks.
    These records carry WKT geometry (including linear features such as trails
    and roads that InfraTrak represents only as point coordinates).

    GeoParks has no equivalent of InfraTrak's lifecycle attributes (replacement
    value, lifespan, condition assessment). Those columns are NULL for this
    source population.
*/
cdm_geoparks as (
    select
        {{ dbt_utils.generate_surrogate_key(['gp.feature_id']) }} as physical_assets_sk,
        gp.feature_id as asset_id,
        parks.parks_sk,
        gp.feature_class,
        gp.sub_type,
        cast(null as varchar) as description,
        gp.installation_year,
        cast(null as decimal(12, 2)) as replacement_value,
        cast(null as integer) as expected_lifespan_years,
        cast(null as decimal(9, 6)) as point_latitude,
        cast(null as decimal(9, 6)) as point_longitude,
        gp.geometry_wkt,
        gp.positional_accuracy_meters,
        gp.last_updated,
        gp.status,
        cast(null as boolean) as is_visible_in_survey,
        {{ generate_source_system_tag('DCR-GEO-01') }} as source_system
    from source_geoparks as gp
    left join source_parks as parks
        on gp.geo_park_id = parks.geo_park_id
),

/*
    No deduplication is applied. InfraTrak and GeoParks maintain separate
    asset registries with incompatible identifier schemes; the VistaReserve
    crosswalk that nominally linked them uses legacy IDs and cannot be applied
    to current records. Downstream mart models (dim_assets) should filter by
    source_system when a single-system view is required, or use parks_sk to
    aggregate both populations to the park level.
*/
final as (
    select * from cdm_infratrak
    union all
    select * from cdm_geoparks
)

select * from final
