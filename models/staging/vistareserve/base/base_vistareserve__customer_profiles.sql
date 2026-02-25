with

source as (
    select * from {{ source('vistareserve', 'customer_profiles') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by customer_id
            order by created_at desc
        ) as row_num
    from source
)

select
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    address_state,
    is_veteran,
    is_senior,
    has_annual_pass,
    created_at,
    merged_into_customer_id,
    preferences_json
from ranked
where row_num = 1
