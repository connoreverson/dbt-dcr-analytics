with

source as (
    select * from {{ source('biosurvey', 'survey_sites') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.site_id']) }} as hk_survey_site,
        cast(source.site_id as varchar) as site_id,
        cast(source.park_id as integer) as park_id,
        cast(source.site_name as varchar) as site_name,
        cast(source.site_description as varchar) as site_description
    from source
)

select * from final
