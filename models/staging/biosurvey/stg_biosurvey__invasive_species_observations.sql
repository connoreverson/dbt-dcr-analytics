with

source as (
    select * from {{ source('biosurvey', 'invasive_species_observations') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.observation_id']) }} as hk_invasive_observation,
        cast(source.observation_id as varchar) as observation_id,
        cast(source.site_id as varchar) as site_id,
        cast(source.species_code as varchar) as species_code,
        cast(source.observation_date as date) as observation_date,
        cast(source.extent_square_meters as decimal(10, 2)) as extent_square_meters,
        cast(source.treatment_applied as varchar) as treatment_applied,
        cast(source.treatment_date as date) as treatment_date,
        cast(source.latitude as decimal(9, 6)) as latitude,
        cast(source.longitude as decimal(9, 6)) as longitude
    from source
)

select * from final
