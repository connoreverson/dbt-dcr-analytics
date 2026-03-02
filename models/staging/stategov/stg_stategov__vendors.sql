with

source as (
    select * from {{ source('stategov', 'vendors') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.vendor_id']) }} as hk_vendors,
        --  ids
        cast(source.vendor_id as varchar) as vendor_id,
        --  vendor attributes
        cast(source.vendor_name as varchar) as vendor_name,
        cast(source.vendor_type as varchar) as vendor_type,
        cast(source.is_active as boolean) as is_active,
        --  pii — masked taxpayer identification number (confidential per state data governance policy)
        cast(source.tin_masked as varchar) as tin_masked
    from source

)

select * from final
