with

/*
    RangerShield CAD/RMS (DCR-LES-01) is air-gapped from all other DCR systems.
    Per governance policy, LE data must be isolated at the integration layer —
    this model does not join to int_parks or any non-LE integration model.
    Officer assignments are at the region level only (assigned_region); no
    park-specific location data is available within RangerShield.
*/
source_activity as (
    select * from {{ ref('stg_rangershield__officer_activity') }}
),

source_officers as (
    select * from {{ ref('stg_rangershield__officers') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['act.activity_id']) }} as officer_shifts_sk,
        act.activity_id,
        act.badge_number,
        act.shift_date,
        act.shift_start_time,
        act.shift_end_time,
        act.patrol_miles,
        act.visitor_contacts,
        act.resource_checks,
        ofr.rank,
        ofr.certification_status,
        ofr.assigned_region,
        {{ generate_source_system_tag('DCR-LES-01') }} as source_system
    from source_activity as act
    left join source_officers as ofr
        on act.badge_number = ofr.badge_number
)

select * from final
