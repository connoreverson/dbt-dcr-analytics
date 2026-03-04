with

finance as (
    select
        parks_sk,
        date_trunc('month', expenditure_month_date) as report_month,
        sum(amount) as total_expenditures
    from {{ ref('fct_expenditures') }}
    group by parks_sk, date_trunc('month', expenditure_month_date)
),

visitation as (
    select
        parks_sk,
        date_trunc('month', date_sk) as report_month,
        sum(total_estimated_visitors) as total_visitors
    from {{ ref('fct_visitation') }}
    group by parks_sk, date_trunc('month', date_sk)
),

ops as (
    select
        parks_sk,
        date_trunc('month', event_date) as report_month,
        count(event_sk) as total_incidents
    from {{ ref('fct_incidents_and_maintenance') }}
    where event_category = 'Maintenance Work Order'
    group by parks_sk, date_trunc('month', event_date)
),

reports as (
    select
        coalesce(f.parks_sk, coalesce(v.parks_sk, o.parks_sk)) as parks_sk,
        coalesce(f.report_month, coalesce(v.report_month, o.report_month)) as report_month
    from finance as f
    full outer join visitation as v
        on
            f.parks_sk = v.parks_sk
            and f.report_month = v.report_month
    full outer join ops as o
        on
            coalesce(f.parks_sk, v.parks_sk) = o.parks_sk
            and coalesce(f.report_month, v.report_month) = o.report_month
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['r.parks_sk', 'r.report_month']) }} as performance_sk,
        cast(r.report_month as date) as report_month,
        cast(r.parks_sk as varchar) as parks_sk,
        coalesce(f.total_expenditures, 0) as total_expenditures,
        coalesce(v.total_visitors, 0) as total_visitors,
        coalesce(o.total_incidents, 0) as total_incidents
    from reports as r
    left join finance as f
        on
            r.parks_sk = f.parks_sk
            and r.report_month = f.report_month
    left join visitation as v
        on
            r.parks_sk = v.parks_sk
            and r.report_month = v.report_month
    left join ops as o
        on
            r.parks_sk = o.parks_sk
            and r.report_month = o.report_month
)

select * from final
