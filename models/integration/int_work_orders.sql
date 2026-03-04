with

source_work_orders as (
    select * from {{ ref('stg_infratrak__work_orders') }}
),

source_parks as (
    select * from {{ ref('int_parks') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['wo.wo_id']) }} as work_orders_sk,
        wo.wo_id,
        wo.asset_tag,
        parks.parks_sk,
        wo.primary_assignee,
        wo.wo_type,
        wo.status,
        wo.labor_hours,
        wo.material_cost,
        wo.total_cost,
        wo.reported_date,
        wo.completed_date,
        {{ generate_source_system_tag('DCR-AST-01') }} as source_system
    from source_work_orders as wo
    left join source_parks as parks
        on wo.park_id = parks.infratrak_park_id
)

select * from final
