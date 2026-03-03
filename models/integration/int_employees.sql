with

source_employees as (
    select * from {{ ref('stg_peoplefirst__employees') }}
    where is_deleted = false
),

/*
    Positions are joined without an is_deleted filter. A small number of active
    employees (~2%) are assigned to soft-deleted positions — slots that were abolished
    after hire but before the employee was formally separated or reassigned. Including
    all positions preserves job_classification and pay_grade context for these employees.
    The position_is_active flag reflects the current status of the position slot.
*/
source_positions as (
    select * from {{ ref('stg_peoplefirst__positions') }}
),

source_org_units as (
    select * from {{ ref('stg_peoplefirst__org_units') }}
    where is_deleted = false
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['emp.employee_id']) }} as employees_sk,
        emp.employee_id,
        emp.first_name_hash,
        emp.last_name_hash,
        emp.email_hash,
        emp.phone_hash,
        emp.hire_date,
        emp.separation_date,
        pos.position_id,
        pos.job_classification,
        pos.pay_grade,
        pos.funding_source,
        pos.is_active as position_is_active,
        ou.org_unit_id,
        ou.org_unit_name,
        ou.region_id,
        {{ generate_source_system_tag('DCR-HCM-01') }} as source_system
    from source_employees as emp
    left join source_positions as pos
        on emp.position_id = pos.position_id
    left join source_org_units as ou
        on pos.org_unit_id = ou.org_unit_id
)

select * from final
