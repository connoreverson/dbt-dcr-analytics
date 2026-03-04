with

int_employees as (
    select * from {{ ref('int_employees') }}
),

final as (
    select
        employees_sk as employee_sk,
        employee_id,
        first_name_hash,
        last_name_hash,
        email_hash,
        phone_hash,
        hire_date,
        separation_date,
        position_id,
        job_classification,
        pay_grade,
        funding_source,
        position_is_active,
        org_unit_id,
        org_unit_name,
        region_id,
        source_system
    from int_employees
)

select * from final
