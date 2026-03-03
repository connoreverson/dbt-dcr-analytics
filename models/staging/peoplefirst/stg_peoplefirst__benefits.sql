with

source as (
    select * from {{ source('peoplefirst', 'benefits') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.employee_id']) }} as hk_benefit,
        cast(source.employee_id as varchar) as employee_id,
        cast(source.health_plan_type as varchar) as health_plan_type,
        cast(source.retirement_tier as varchar) as retirement_tier,
        cast(source.annual_leave_hours as decimal(6, 2)) as annual_leave_hours,
        cast(source.sick_leave_hours as decimal(6, 2)) as sick_leave_hours,
        cast(source.comp_time_hours as decimal(6, 2)) as comp_time_hours,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
