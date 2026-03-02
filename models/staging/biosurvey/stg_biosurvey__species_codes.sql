with

source as (
    select * from {{ source('biosurvey', 'species_codes') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.species_code']) }} as hk_species,
        cast(source.species_code as varchar) as species_code,
        cast(source.common_name as varchar) as common_name,
        cast(source.scientific_name as varchar) as scientific_name,
        cast(source.category as varchar) as category,
        cast(source.is_endangered as boolean) as is_endangered,
        cast(source.is_invasive as boolean) as is_invasive,
        cast(source.alternate_names as varchar) as alternate_names
    from source
)

select * from final
