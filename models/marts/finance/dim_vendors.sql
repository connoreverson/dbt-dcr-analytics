with

int_vendors as (
    select * from {{ ref('int_vendors') }}
),

final as (
    select
        vendors_sk as vendor_sk,
        vendor_id,
        vendor_name,
        vendor_type,
        is_active,
        tin_masked,
        source_system
    from int_vendors
)

select * from final
