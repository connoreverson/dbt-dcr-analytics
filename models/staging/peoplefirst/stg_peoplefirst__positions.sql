with

source as (
    select * from {{ source('peoplefirst', 'positions') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.position_id']) }} as hk_position,
        cast(source.position_id as varchar) as position_id,
        cast(source.job_classification as varchar) as job_classification,
        cast(source.pay_grade as varchar) as pay_grade,
        cast(source.org_unit_id as varchar) as org_unit_id,
        cast(source.funding_source as varchar) as funding_source,
        cast(source.is_active as boolean) as is_active,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
