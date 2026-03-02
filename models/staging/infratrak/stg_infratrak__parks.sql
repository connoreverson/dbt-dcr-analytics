with

source as (
    select * from {{ source('infratrak', 'parks') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.park_id']) }} as hk_park,
        --  ids
        cast(source.park_id as integer) as park_id,
        cast(source.region_id as integer) as region_id,
        --  attributes
        cast(source.park_name as varchar) as park_name,
        cast(source.classification as varchar) as classification
    from source
)

select * from final
