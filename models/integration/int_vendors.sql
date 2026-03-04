with

source_vendors as (
    select * from {{ ref('stg_stategov__vendors') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['vendor_id']) }} as vendors_sk,
        vendor_id,
        vendor_name,
        vendor_type,
        is_active,
        tin_masked,
        {{ generate_source_system_tag('DCR-FIN-01') }} as source_system
    from source_vendors
)

select * from final
