with

int_transactions as (
    select * from {{ ref('int_transactions') }}
),

stg_transactions as (
    select * from {{ ref('stg_vistareserve__pos_transactions') }}
),

fct_pos_transactions as (
    select
        cast(transactions_sk as varchar) as transactions_sk,

        -- Dimension Keys
        cast(_contact_sk as varchar) as contacts_sk,
        cast(_park_sk as varchar) as parks_sk,

        -- Measures
        cast(int_transactions.amount as decimal(10, 2)) as transaction_amount,
        cast(1 as integer) as quantity,
        cast(stg_transactions.revenue_category as varchar) as revenue_category,
        cast(int_transactions.book_date as timestamp) as transaction_created_at,
        cast(stg_transactions.is_kiosk_entry as boolean) as is_kiosk_entry

    from int_transactions
    left join stg_transactions
        on cast(int_transactions.transaction_id as varchar) = cast(stg_transactions.transaction_id as varchar)
)

select * from fct_pos_transactions
