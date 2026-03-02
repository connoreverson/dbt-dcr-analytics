with

source as (
    select * from {{ source('legacyres', 'legacy_customers') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.legacy_cust_id']) }} as hk_customers,  -- noqa: LT05
        --  ids
        cast(source.legacy_cust_id as varchar) as legacy_customer_id,
        --  pii — name and contact
        cast(source.first_name as varchar) as first_name,
        cast(source.last_name as varchar) as last_name,
        cast(source.email as varchar) as email,
        cast(source.phone_number as varchar) as phone_number,
        --  pii — partial card mask (null for cash/check payers)
        cast(source.partial_card_mask as varchar) as partial_card_mask
    from source

)

select * from final
