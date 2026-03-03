with

source as (
    select * from {{ source('peoplefirst', 'payroll') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.payroll_id']) }} as hk_payroll,
        cast(source.payroll_id as varchar) as payroll_id,
        cast(source.employee_id as varchar) as employee_id,
        cast(source.pay_period_start as date) as pay_period_start,
        cast(source.pay_period_end as date) as pay_period_end,
        cast(source.gross_pay as decimal(10, 2)) as gross_pay,
        cast(source.deductions as decimal(10, 2)) as deductions,
        cast(source.taxes_withheld as decimal(10, 2)) as taxes_withheld,
        cast(source.net_pay as decimal(10, 2)) as net_pay,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
