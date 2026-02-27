with

source as (
    select * from {{ source('vistareserve', 'pos_transactions') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.transaction_id']) }} as hk_pos_transactions,
        --  ids
        cast(source.customer_id as varchar) as customer_id,
        cast(source.park_id as integer) as park_id,
        cast(source.transaction_id as varchar) as transaction_id,
        --  strings
        cast(source.revenue_category as varchar) as revenue_category,
        --  numerics
        cast(source.amount as decimal(10, 2)) as transaction_amount,
        --  booleans
        cast(source.is_kiosk_entry as boolean) as is_kiosk_entry,
        --  dates/timestamps
        cast(source.transaction_date as timestamp) as transaction_created_at
    from source

)

select * from final
