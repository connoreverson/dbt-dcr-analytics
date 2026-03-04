with

source as (
    select * from {{ source('biosurvey', 'endangered_species_monitoring') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.monitoring_id']) }} as hk_endangered_monitoring,
        cast(source.monitoring_id as varchar) as monitoring_id,
        cast(source.site_id as varchar) as site_id,
        cast(source.species_code as varchar) as species_code,
        cast(source.monitoring_year as integer) as monitoring_year,
        cast(source.population_count as integer) as population_count,
        cast(source.nesting_pairs as integer) as nesting_pairs,
        cast(source.reproductive_success_rate as decimal(5, 2)) as reproductive_success_rate,
        cast(source.compliance_reported as boolean) as compliance_reported
    from source
)

select * from final
