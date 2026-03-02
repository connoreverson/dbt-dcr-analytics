with

source as (
    select * from {{ source('rangershield', 'incidents') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.incident_number']) }} as hk_incident,
        cast(source.incident_number as varchar) as incident_number,
        cast(source.reporting_officer as varchar) as reporting_officer_badge,
        cast(source.incident_type as varchar) as incident_type,
        cast(source.report_timestamp as timestamp) as report_timestamp,
        cast(source.location_narrative as varchar) as location_narrative,
        cast(source.narrative_summary as varchar) as narrative_summary,
        cast(source.review_status as varchar) as review_status
    from source
)

select * from final
