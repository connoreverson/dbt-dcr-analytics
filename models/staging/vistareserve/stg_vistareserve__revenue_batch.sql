with

source as (
    select * from {{ source('vistareserve', 'revenue_batch') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.batch_id']) }} as hk_revenue_batch,
        --  ids
        cast(source.batch_id as varchar) as batch_id,
        cast(source.park_id as integer) as park_id,
        --  strings
        cast(source.revenue_category as varchar) as revenue_category,
        --  numerics
        cast(source.gross_revenue as decimal(12, 2)) as gross_revenue,
        cast(source.transaction_count as integer) as transaction_count,
        --  dates/timestamps
        cast(source.batch_date as date) as batch_date
    from source

)

select * from final
