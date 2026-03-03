with

source_flora_fauna as (
    select * from {{ ref('stg_biosurvey__flora_fauna_surveys') }}
),

source_water_quality as (
    select * from {{ ref('stg_biosurvey__water_quality_tests') }}
),

source_invasive_species as (
    select * from {{ ref('stg_biosurvey__invasive_species_observations') }}
),

source_survey_sites as (
    select * from {{ ref('stg_biosurvey__survey_sites') }}
),

/*
    int_parks is the authoritative park dimension. BioSurvey survey sites
    carry integer park_ids (1–50) that correspond to InfraTrak park_ids,
    resolved via infratrak_park_id in int_parks.
*/
source_parks as (
    select
        parks_sk,
        infratrak_park_id
    from {{ ref('int_parks') }}
),

/*
    Flora and fauna field surveys: point-in-time species presence and
    abundance records tied to a named survey site. Each row represents one
    species observed during one field visit, with count and density
    estimates. Coordinates reflect the exact observation point, not the
    site centroid.
*/
cdm_flora_fauna as (
    select
        {{ dbt_utils.generate_surrogate_key(["'flora_fauna'", 'ff.survey_id']) }} as ecological_surveys_sk,
        ff.survey_id as observation_id,
        ff.site_id,
        parks.parks_sk,
        'flora_fauna' as observation_type,
        ff.survey_date as observation_date,
        ff.species_code,
        ff.observer_name,
        ff.latitude,
        ff.longitude,
        ff.count_estimate,
        ff.density_estimate_per_hectare,
        cast(null as decimal(10, 2)) as extent_square_meters,
        cast(null as varchar) as treatment_applied,
        cast(null as date) as treatment_date,
        cast(null as decimal(6, 2)) as dissolved_oxygen_mgl,
        cast(null as decimal(4, 2)) as ph_level,
        cast(null as integer) as ecoli_cfu_100ml,
        cast(null as decimal(6, 2)) as turbidity_ntu,
        cast(null as decimal(5, 2)) as temperature_celsius,
        cast(null as decimal(6, 2)) as nitrogen_mgl,
        cast(null as decimal(6, 2)) as phosphorus_mgl,
        cast(null as varchar) as protocol_era
    from source_flora_fauna as ff
    left join source_survey_sites as ss
        on ff.site_id = ss.site_id
    left join source_parks as parks
        on ss.park_id = parks.infratrak_park_id
),

/*
    Water quality field tests: laboratory parameter measurements collected
    at named survey sites. Each row represents one sampling event at one
    site, with measurements for up to seven parameters. Protocol era
    documents the testing methodology version (pre-2005, 2005-2018, 2018+).
    No observation-level coordinates — location is inherited from the site.
*/
cdm_water_quality as (
    select
        {{ dbt_utils.generate_surrogate_key(["'water_quality'", 'wq.test_id']) }} as ecological_surveys_sk,
        wq.test_id as observation_id,
        wq.site_id,
        parks.parks_sk,
        'water_quality' as observation_type,
        wq.sample_date as observation_date,
        cast(null as varchar) as species_code,
        cast(null as varchar) as observer_name,
        cast(null as decimal(9, 6)) as latitude,
        cast(null as decimal(9, 6)) as longitude,
        cast(null as integer) as count_estimate,
        cast(null as decimal(8, 2)) as density_estimate_per_hectare,
        cast(null as decimal(10, 2)) as extent_square_meters,
        cast(null as varchar) as treatment_applied,
        cast(null as date) as treatment_date,
        wq.dissolved_oxygen_mgl,
        wq.ph_level,
        wq.ecoli_cfu_100ml,
        wq.turbidity_ntu,
        wq.temperature_celsius,
        wq.nitrogen_mgl,
        wq.phosphorus_mgl,
        wq.protocol_era
    from source_water_quality as wq
    left join source_survey_sites as ss
        on wq.site_id = ss.site_id
    left join source_parks as parks
        on ss.park_id = parks.infratrak_park_id
),

/*
    Invasive species field observations: occurrence and treatment records
    for regulated invasive flora and fauna. Each row represents one field
    observation of an invasive species at a site, including measured
    spatial extent and any applied treatment. Coordinates are
    observation-specific, not site centroids.
*/
cdm_invasive_species as (
    select
        {{ dbt_utils.generate_surrogate_key(["'invasive_species'", 'inv.observation_id']) }} as ecological_surveys_sk,
        inv.observation_id,
        inv.site_id,
        parks.parks_sk,
        'invasive_species' as observation_type,
        inv.observation_date,
        inv.species_code,
        cast(null as varchar) as observer_name,
        inv.latitude,
        inv.longitude,
        cast(null as integer) as count_estimate,
        cast(null as decimal(8, 2)) as density_estimate_per_hectare,
        inv.extent_square_meters,
        inv.treatment_applied,
        inv.treatment_date,
        cast(null as decimal(6, 2)) as dissolved_oxygen_mgl,
        cast(null as decimal(4, 2)) as ph_level,
        cast(null as integer) as ecoli_cfu_100ml,
        cast(null as decimal(6, 2)) as turbidity_ntu,
        cast(null as decimal(5, 2)) as temperature_celsius,
        cast(null as decimal(6, 2)) as nitrogen_mgl,
        cast(null as decimal(6, 2)) as phosphorus_mgl,
        cast(null as varchar) as protocol_era
    from source_invasive_species as inv
    left join source_survey_sites as ss
        on inv.site_id = ss.site_id
    left join source_parks as parks
        on ss.park_id = parks.infratrak_park_id
),

/*
    All three observation types share a survey-site grain and a parks_sk
    FK. Observation-type-specific columns are NULL for the other types.
    Downstream models should filter on observation_type when they require
    a single-type view.
*/
final as (
    select * from cdm_flora_fauna
    union all
    select * from cdm_water_quality
    union all
    select * from cdm_invasive_species
)

select * from final
