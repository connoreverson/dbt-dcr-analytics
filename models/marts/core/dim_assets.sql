with

int_physical_assets as (
    select * from {{ ref('int_physical_assets') }}
),

final as (
    select
        physical_assets_sk as asset_sk,
        asset_id,
        parks_sk,
        feature_class,
        sub_type,
        description,
        installation_year,
        replacement_value,
        expected_lifespan_years,
        point_latitude,
        point_longitude,
        geometry_wkt,
        positional_accuracy_meters,
        last_updated,
        status,
        is_visible_in_survey,
        source_system
    from int_physical_assets
)

select * from final
