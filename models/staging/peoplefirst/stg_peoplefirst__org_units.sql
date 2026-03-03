with

source as (
    select * from {{ source('peoplefirst', 'org_units') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.org_unit_id']) }} as hk_org_unit,
        cast(source.org_unit_id as varchar) as org_unit_id,
        cast(source.org_unit_name as varchar) as org_unit_name,
        cast(source.region_id as integer) as region_id,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
