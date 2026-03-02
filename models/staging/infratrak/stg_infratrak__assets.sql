with

source as (
    select * from {{ source('infratrak', 'assets') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.asset_tag']) }} as hk_asset,
        --  ids
        cast(source.asset_tag as varchar) as asset_tag,
        cast(source.park_id as integer) as park_id,
        --  classification
        cast(source.asset_category as varchar) as asset_category,
        cast(source.description as varchar) as description,
        --  physical lifecycle
        cast(source.construction_year as integer) as construction_year,
        cast(source.expected_lifespan_years as integer) as expected_lifespan_years,
        cast(source.replacement_value as decimal(12, 2)) as replacement_value,
        --  geography
        cast(source.latitude as decimal(9, 6)) as latitude,
        cast(source.longitude as decimal(9, 6)) as longitude,
        --  flags
        cast(source.is_visible_in_survey as boolean) as is_visible_in_survey
    from source
)

select * from final
