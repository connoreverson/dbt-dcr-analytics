with

source as (
    select * from {{ ref('base_vistareserve__customer_profiles') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.customer_id']) }} as hk_customer_profiles,
        --  ids
        cast(source.customer_id as varchar) as customer_id,
        cast(source.merged_into_customer_id as varchar)
            as merged_into_customer_id,
        --  strings
        cast(source.address_state as varchar) as address_state,
        cast(source.email as varchar) as email,
        cast(source.first_name as varchar) as first_name,
        cast(source.last_name as varchar) as last_name,
        cast(source.phone as varchar) as phone,
        --  booleans
        cast(source.has_annual_pass as boolean) as has_annual_pass,
        cast(source.is_senior as boolean) as is_senior,
        cast(source.is_veteran as boolean) as is_veteran,
        --  dates/timestamps
        cast(source.created_at as timestamp) as account_created_at,
        --  semi_structured
        cast(
            json_extract_string(
                source.preferences_json, '$.equipment_type'
            ) as varchar
        ) as equipment_preference,
        cast(
            json_extract_string(
                source.preferences_json, '$.accessibility_needs'
            ) as varchar
        ) as accessibility_needs
    from source

)

select * from final
