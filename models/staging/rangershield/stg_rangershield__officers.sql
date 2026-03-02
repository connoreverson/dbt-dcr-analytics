with

source as (
    select * from {{ source('rangershield', 'officers') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.badge_number']) }} as hk_officer,
        cast(source.badge_number as varchar) as badge_number,
        cast(source.first_name as varchar) as first_name,
        cast(source.last_name as varchar) as last_name,
        cast(source.rank as varchar) as rank,
        cast(source.certification_status as varchar) as certification_status,
        cast(source.assigned_region as integer) as assigned_region
    from source
)

select * from final
