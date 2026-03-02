with

source as (
    select * from {{ source('infratrak', 'work_orders') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.wo_id']) }} as hk_work_order,
        --  ids
        cast(source.wo_id as varchar) as wo_id,
        cast(source.asset_tag as varchar) as asset_tag,
        cast(source.park_id as integer) as park_id,
        cast(source.primary_assignee as varchar) as primary_assignee,
        --  classification
        cast(source.wo_type as varchar) as wo_type,
        cast(source.status as varchar) as status,
        --  costs
        cast(source.labor_hours as decimal(6, 2)) as labor_hours,
        cast(source.material_cost as decimal(10, 2)) as material_cost,
        cast(source.total_cost as decimal(10, 2)) as total_cost,
        --  dates
        cast(source.reported_date as date) as reported_date,
        --  completed_date is null for open and in-progress work orders
        cast(source.completed_date as date) as completed_date
    from source
)

select * from final
