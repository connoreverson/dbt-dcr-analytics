with

source as (
    select * from {{ source('rangershield', 'citations') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.citation_number']) }} as hk_citation,
        cast(source.citation_number as varchar) as citation_number,
        cast(source.incident_number as varchar) as incident_number,
        cast(source.issuing_officer as varchar) as issuing_officer_badge,
        cast(source.violation_code as varchar) as violation_code,
        cast(source.issue_timestamp as timestamp) as issue_timestamp,
        cast(source.fine_amount as decimal(6, 2)) as fine_amount,
        cast(source.court_disposition as varchar) as court_disposition
    from source
)

select * from final
