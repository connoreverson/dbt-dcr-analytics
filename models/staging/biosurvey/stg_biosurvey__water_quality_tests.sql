with

source as (
    select * from {{ source('biosurvey', 'water_quality_tests') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.test_id']) }} as hk_water_quality_test,
        cast(source.test_id as varchar) as test_id,
        cast(source.site_id as varchar) as site_id,
        cast(source.sample_date as date) as sample_date,
        cast(source.dissolved_oxygen_mgl as decimal(6, 2)) as dissolved_oxygen_mgl,
        cast(source.ph_level as decimal(4, 2)) as ph_level,
        cast(source.ecoli_cfu_100ml as integer) as ecoli_cfu_100ml,
        cast(source.turbidity_ntu as decimal(6, 2)) as turbidity_ntu,
        cast(source.temperature_celsius as decimal(5, 2)) as temperature_celsius,
        cast(source.nitrogen_mgl as decimal(6, 2)) as nitrogen_mgl,
        cast(source.phosphorus_mgl as decimal(6, 2)) as phosphorus_mgl,
        cast(source.protocol_era as varchar) as protocol_era
    from source
)

select * from final
