with

source as (
    select * from {{ source('legacyres', 'legacy_fee_schedule_wide') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.facility_type']) }} as hk_fee_schedule,
        --  ids / natural key
        cast(source.facility_type as varchar) as facility_type,
        --  rates (stored as decimal dollars)
        cast(source.base_rate_peak as decimal(6, 2)) as base_rate_peak,
        cast(source.base_rate_offpeak as decimal(6, 2)) as base_rate_offpeak,
        cast(source.base_rate_shoulder as decimal(6, 2)) as base_rate_shoulder,
        --  discount rates (source '15%' -> 0.15 decimal fraction)
        cast(replace(source.resident_discount_pct, '%', '') as decimal(5, 2))
        / 100.0 as resident_discount_rate,
        cast(replace(source.senior_discount_pct, '%', '') as decimal(5, 2))
        / 100.0 as senior_discount_rate,
        --  dates
        cast(source.export_date as date) as schedule_export_date
    from source

)

select * from final
