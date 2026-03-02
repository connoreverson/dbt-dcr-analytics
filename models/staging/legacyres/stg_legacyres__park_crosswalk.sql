with

source as (
    select * from {{ source('legacyres', 'legacy_park_crosswalk') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.legacy_park_id']) }} as hk_park_crosswalk,  -- noqa: LT05
        --  ids
        cast(source.legacy_park_id as varchar) as legacy_park_id,
        cast(source.legacy_park_name as varchar) as legacy_park_name,
        --  current system reference (null for unmapped parks)
        cast(source.current_park_id as integer) as current_park_id
    from source

)

select * from final
