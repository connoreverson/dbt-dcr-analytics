with

visits as (
    select * from {{ ref('int_visits') }}
),

visits_stg as (
    select * from {{ ref('stg_vistareserve__reservations') }}
),

visits_enriched as (
    select
        v._park_sk as parks_sk,
        s.arrival_date,
        s.number_of_guests,
        v.visit_id
    from visits as v
    inner join visits_stg as s
        on v.visit_id = s.reservation_id
    where s.reservation_status in ('Checked In', 'Completed')
),

visits_daily as (
    select
        cast(parks_sk as varchar) as parks_sk,
        cast(arrival_date as date) as date_sk,
        sum(cast(number_of_guests as integer)) as registered_visitors,
        count(visit_id) as reservation_count_checkins
    from visits_enriched
    where arrival_date is not null
    group by parks_sk, arrival_date
),

sensor_counts as (
    select * from {{ ref('int_visitor_counts') }}
),

sensor_daily as (
    select
        cast(parks_sk as varchar) as parks_sk,
        cast(target_date as date) as date_sk,
        sum(cast(estimated_total_visitors as integer)) as sensor_estimated_visitors
    from sensor_counts
    group by parks_sk, target_date
),

parks as (
    select
        coalesce(v.parks_sk, s.parks_sk) as parks_sk,
        coalesce(v.date_sk, s.date_sk) as date_sk
    from visits_daily as v
    full outer join sensor_daily as s
        on
            v.parks_sk = s.parks_sk
            and v.date_sk = s.date_sk
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['p.parks_sk', 'p.date_sk']) }} as visitation_sk,
        p.parks_sk,
        p.date_sk,
        coalesce(v.registered_visitors, 0) as registered_visitors,
        coalesce(v.reservation_count_checkins, 0) as checked_in_reservations,
        coalesce(s.sensor_estimated_visitors, 0) as sensor_estimated_visitors,
        coalesce(v.registered_visitors, 0) + coalesce(s.sensor_estimated_visitors, 0) as total_estimated_visitors
    from parks as p
    left join visits_daily as v
        on
            p.parks_sk = v.parks_sk
            and p.date_sk = v.date_sk
    left join sensor_daily as s
        on
            p.parks_sk = s.parks_sk
            and p.date_sk = s.date_sk
)

select * from final
