with

source as (
    select * from {{ source('rangershield', 'use_of_force') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.uof_id']) }} as hk_use_of_force,
        cast(source.uof_id as varchar) as uof_id,
        cast(source.incident_number as varchar) as incident_number,
        cast(source.involved_officer as varchar) as involved_officer_badge,
        cast(source.force_level as varchar) as force_level,
        cast(source.subject_injury as boolean) as subject_injury,
        cast(source.officer_injury as boolean) as officer_injury,
        cast(source.internal_review_status as varchar) as internal_review_status
    from source
)

select * from final
