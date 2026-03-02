with

source as (
    select * from {{ source('infratrak', 'employees') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.employee_id']) }} as hk_employee,
        --  ids
        cast(source.employee_id as varchar) as employee_id,
        cast(source.assigned_region as integer) as assigned_region,
        --  attributes
        cast(source.first_name as varchar) as first_name,
        cast(source.last_name as varchar) as last_name,
        cast(source.title as varchar) as title
    from source
)

select * from final
