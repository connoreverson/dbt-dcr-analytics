with

int_contacts as (
    select * from {{ ref('int_contacts') }}
),

customers_enriched as (
    select
        contacts_sk,
        
        -- combine first and last
        concat_ws(' ', firstname, lastname) as customer_name,
        
        emailaddress1 as email,
        mobilephone as phone,
        address_state,
        account_created_at as customer_since_date,

        -- enrichments
        case
            when address_state in ('MA', 'CT', 'RI', 'NH', 'VT', 'ME', 'NY', 'NJ') then 'Northeast'
            when address_state in ('PA', 'OH', 'MI', 'IN', 'IL', 'WI') then 'Midwest'
            when address_state in ('CA', 'OR', 'WA', 'NV', 'ID') then 'West'
            when address_state in ('TX', 'FL', 'GA', 'NC', 'SC', 'VA') then 'South'
            else 'Other'
        end as geographic_region,

        case
            when date_diff('year', cast(account_created_at as date), current_date) < 1 then 'New (< 1 year)'
            when date_diff('year', cast(account_created_at as date), current_date) between 1 and 3 then 'Established (1-3 years)'
            when date_diff('year', cast(account_created_at as date), current_date) > 3 then 'Loyal (> 3 years)'
            else 'Unknown'
        end as customer_tenure_tier,

        has_annual_pass,
        is_senior,
        is_veteran

    from int_contacts
)

select * from customers_enriched
