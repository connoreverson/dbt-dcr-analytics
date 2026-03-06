with

dim_parks as (
    select * from {{ ref('dim_parks') }}
),

fct_reservations as (
    select * from {{ ref('fct_reservations') }}
),

fct_pos_transactions as (
    select * from {{ ref('fct_pos_transactions') }}
),

-- Truncate dates for grouping
res_prepared as (
    select
        parks_sk,
        reservations_sk,
        reservation_amount,
        nights_stayed,
        date_trunc('month', check_in_date) as report_month
    from fct_reservations
),

-- Aggregate reservations to park-month
res_agg as (
    select
        parks_sk,
        report_month,
        count(reservations_sk) as total_reservations,
        sum(reservation_amount) as total_reservation_revenue,
        avg(reservation_amount) as avg_reservation_value,
        sum(nights_stayed) as total_nights_stayed,
        avg(nights_stayed) as avg_nights_per_reservation
    from res_prepared
    group by 1, 2
),

-- Truncate POS dates for grouping
pos_prepared as (
    select
        parks_sk,
        transactions_sk,
        transaction_amount,
        quantity,
        date_trunc('month', transaction_created_at) as report_month
    from fct_pos_transactions
),

-- Aggregate POS to park-month
pos_agg as (
    select
        parks_sk,
        report_month,
        count(transactions_sk) as total_pos_transactions,
        sum(transaction_amount) as total_pos_revenue,
        avg(transaction_amount) as avg_pos_transaction_value,
        sum(quantity) as total_pos_items_sold
    from pos_prepared
    group by 1, 2
),

-- Get all unique park-months
park_months as (
    select
        parks_sk,
        report_month
    from res_agg
    union all
    select
        parks_sk,
        report_month
    from pos_agg
),

distinct_park_months as (
    select
        parks_sk,
        report_month
    from park_months
    group by 1, 2
),

-- Combine them
combined as (
    select
        pm.parks_sk,
        cast(pm.report_month as date) as report_month,

        p.park_name,
        p.region,
        p.park_type,

        cast(coalesce(r.total_reservations, 0) as integer)
            as total_reservations,
        cast(coalesce(r.total_reservation_revenue, 0) as decimal(14, 2))
            as total_reservation_revenue,
        cast(r.avg_reservation_value as decimal(14, 2))
            as avg_reservation_value,
        cast(coalesce(r.total_nights_stayed, 0) as integer)
            as total_nights_stayed,
        cast(r.avg_nights_per_reservation as decimal(10, 2))
            as avg_nights_per_reservation,

        cast(coalesce(s.total_pos_transactions, 0) as integer)
            as total_pos_transactions,
        cast(coalesce(s.total_pos_revenue, 0) as decimal(14, 2))
            as total_pos_revenue,
        cast(s.avg_pos_transaction_value as decimal(14, 2))
            as avg_pos_transaction_value,
        cast(coalesce(s.total_pos_items_sold, 0) as integer)
            as total_pos_items_sold,

        cast(
            (
                coalesce(r.total_reservation_revenue, 0)
                + coalesce(s.total_pos_revenue, 0)
            ) as decimal(14, 2)
        ) as total_combined_revenue

    from distinct_park_months as pm
    left join
        res_agg as r
        on pm.parks_sk = r.parks_sk and pm.report_month = r.report_month
    left join
        pos_agg as s
        on pm.parks_sk = s.parks_sk and pm.report_month = s.report_month
    left join dim_parks as p on pm.parks_sk = p.parks_sk
)

select * from combined
