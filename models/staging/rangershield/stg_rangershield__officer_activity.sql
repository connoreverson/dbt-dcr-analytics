with

source as (
    select * from {{ source('rangershield', 'officer_activity') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.activity_id']) }} as hk_officer_activity,
        cast(source.activity_id as varchar) as activity_id,
        cast(source.badge_number as varchar) as badge_number,
        cast(source.shift_date as date) as shift_date,
        cast(source.shift_start_time as timestamp) as shift_start_time,
        cast(source.shift_end_time as timestamp) as shift_end_time,
        cast(source.patrol_miles as decimal(5, 1)) as patrol_miles,
        cast(source.visitor_contacts as integer) as visitor_contacts,
        cast(source.resource_checks as integer) as resource_checks
    from source
)

select * from final
