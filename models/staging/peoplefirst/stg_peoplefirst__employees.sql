with

source as (
    select * from {{ source('peoplefirst', 'employees') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.employee_id']) }} as hk_employee,
        cast(source.employee_id as varchar) as employee_id,
        md5(cast(source.first_name as varchar)) as first_name_hash,
        md5(cast(source.last_name as varchar)) as last_name_hash,
        md5(cast(source.email as varchar)) as email_hash,
        md5(cast(source.phone as varchar)) as phone_hash,
        cast(source.hire_date as date) as hire_date,
        cast(source.separation_date as date) as separation_date,
        cast(source.position_id as varchar) as position_id,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
