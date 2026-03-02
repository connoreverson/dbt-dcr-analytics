with

source as (
    select * from {{ source('rangershield', 'dispatch_logs') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.log_id']) }} as hk_dispatch_log,
        cast(source.log_id as varchar) as log_id,
        cast(source.incident_number as varchar) as incident_number,
        cast(source.badge_number as varchar) as badge_number,
        cast(source.log_timestamp as timestamp) as log_timestamp,
        cast(source.event_type as varchar) as event_type,
        cast(source.radio_traffic_transcript as varchar) as radio_traffic_transcript
    from source
)

select * from final
