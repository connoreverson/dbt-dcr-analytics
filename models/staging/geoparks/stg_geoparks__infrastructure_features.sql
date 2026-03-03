with

source as (
    select * from {{ source('geoparks', 'infrastructure_features') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.feature_id']) }} as hk_infrastructure_features,
        --  ids
        cast(source.feature_id as varchar) as feature_id,
        cast(source.geo_park_id as varchar) as geo_park_id,
        --  classification
        cast(source.feature_class as varchar) as feature_class,
        cast(source.sub_type as varchar) as sub_type,
        --  operational status
        cast(source.status as varchar) as status,
        --  physical lifecycle
        cast(source.installation_year as integer) as installation_year,
        --  geometry
        cast(source.geometry_wkt as varchar) as geometry_wkt,
        cast(source.positional_accuracy_meters as decimal(5, 2)) as positional_accuracy_meters,
        --  audit
        cast(source.last_updated as date) as last_updated
    from source
)

select * from final
