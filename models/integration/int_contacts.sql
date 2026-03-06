with

source as (
    select * from {{ ref('stg_vistareserve__customer_profiles') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as contacts_sk,
        customer_id as contact_id,
        first_name,
        last_name,
        email as e_mail_address1,
        phone as mobile_phone,
        address_state,
        account_created_at,
        has_annual_pass,
        is_senior,
        is_veteran,
        (merged_into_customer_id is not null) as is_merged_duplicate
    from source
)

select * from final
