with

source as (
    select * from {{ source('peoplefirst', 'leave_balances') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.leave_balance_id']) }} as hk_leave_balance,
        cast(source.leave_balance_id as varchar) as leave_balance_id,
        cast(source.employee_id as varchar) as employee_id,
        cast(source.leave_type as varchar) as leave_type,
        cast(source.balance_amount as decimal(6, 2)) as balance_amount,
        cast(source.as_of_date as date) as as_of_date,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
