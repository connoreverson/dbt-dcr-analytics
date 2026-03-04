with

work_orders as (
    select * from {{ ref('int_work_orders') }}
),

officer_shifts as (
    select * from {{ ref('int_officer_shifts') }}
),

work_order_events as (
    select
        work_orders_sk as event_sk,
        wo_id as source_record_id,
        cast(parks_sk as varchar) as parks_sk,
        cast(null as varchar) as assigned_region,
        reported_date as start_date,
        completed_date as end_date,
        'Maintenance Work Order' as event_category,
        wo_type as event_type,
        status as event_status,
        labor_hours,
        total_cost as financial_cost,
        cast(null as integer) as visitor_contacts,
        cast(null as integer) as resource_checks,
        cast(null as decimal(10, 2)) as patrol_miles,
        source_system
    from work_orders
),

officer_shift_events as (
    select
        officer_shifts_sk as event_sk,
        activity_id as source_record_id,
        cast(null as varchar) as parks_sk,
        cast(assigned_region as varchar) as assigned_region,
        shift_date as start_date,
        shift_date as end_date,
        'Law Enforcement Shift' as event_category,
        'Patrol' as event_type,
        'Completed' as event_status,
        cast(null as decimal(6, 2)) as labor_hours,
        cast(null as decimal(10, 2)) as financial_cost,
        cast(visitor_contacts as integer) as visitor_contacts,
        cast(resource_checks as integer) as resource_checks,
        cast(patrol_miles as decimal(10, 2)) as patrol_miles,
        source_system
    from officer_shifts
),

unioned_events as (
    select * from work_order_events
    union all
    select * from officer_shift_events
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['event_sk', 'event_category']) }} as incidents_and_maintenance_sk,
        event_sk,
        source_record_id,
        parks_sk,
        assigned_region,
        start_date,
        end_date,
        event_category,
        event_type,
        event_status,
        labor_hours,
        financial_cost,
        visitor_contacts,
        resource_checks,
        patrol_miles,
        source_system,
        coalesce(start_date, end_date) as event_date
    from unioned_events
)

select * from final
