with

source as (
    select * from {{ source('biosurvey', 'flora_fauna_surveys') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.survey_id']) }} as hk_flora_fauna_survey,
        cast(source.survey_id as varchar) as survey_id,
        cast(source.site_id as varchar) as site_id,
        cast(source.species_code as varchar) as species_code,
        cast(source.survey_date as date) as survey_date,
        cast(source.observer_name as varchar) as observer_name,
        cast(source.count_estimate as integer) as count_estimate,
        cast(source.density_estimate_per_hectare as decimal(8, 2)) as density_estimate_per_hectare,
        cast(source.latitude as decimal(9, 6)) as latitude,
        cast(source.longitude as decimal(9, 6)) as longitude
    from source
)

select * from final
