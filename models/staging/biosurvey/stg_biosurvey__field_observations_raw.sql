with

source as (
    select * from {{ source('biosurvey', 'field_observations_raw') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['cast(source.raw_id as varchar)']) }} as hk_observation,
        cast(source.raw_id as bigint) as raw_id,
        cast(source.observation_type as varchar) as observation_type,
        cast(source.site_id as varchar) as site_id,
        cast(source.species_code as varchar) as species_code,
        cast(source.observation_date as date) as observation_date,
        cast(source.observer_name as varchar) as observer_name,
        cast(source.count_estimate as integer) as count_estimate,
        cast(source.density_estimate_per_hectare as decimal(8, 2)) as density_estimate_per_hectare,
        nullif(cast(source.nesting_status as varchar), 'None') as nesting_status,
        cast(source.ph_level as decimal(4, 2)) as ph_level,
        try_cast(source.ecoli_count as integer) as ecoli_count,
        cast(source.turbidity_ntu as decimal(6, 2)) as turbidity_ntu,
        cast(source.temperature_celsius as decimal(5, 2)) as temperature_celsius,
        cast(source.gps_latitude as decimal(9, 6)) as gps_latitude,
        cast(source.gps_longitude as decimal(9, 6)) as gps_longitude,
        cast(source.notes as varchar) as notes
    from source
)

select * from final
