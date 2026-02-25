with

int_transactions as (
    select * from {{ ref('int_transactions') }}
),

fct_pos_transactions as (
    select
        cast(transactions_sk as varchar) as transactions_sk,
        
        -- Dimension Keys
        cast(_contact_sk as varchar) as contacts_sk,
        cast(_park_sk as varchar) as parks_sk,
        
        -- Measures
        cast(transaction_amount as decimal(10,2)) as transaction_amount,
        cast(1 as integer) as quantity,
        cast(revenue_category as varchar) as revenue_category,
        cast(transaction_created_at as timestamp) as transaction_created_at,
        cast(is_kiosk_entry as boolean) as is_kiosk_entry

    from int_transactions
)

select * from fct_pos_transactions
