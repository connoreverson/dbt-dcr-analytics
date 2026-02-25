with fct_res as (
    select coalesce(sum(reservation_amount), 0) as total_res
    from {{ ref('fct_reservations') }}
),

fct_pos as (
    select coalesce(sum(transaction_amount), 0) as total_pos
    from {{ ref('fct_pos_transactions') }}
),

rpt as (
    select
        coalesce(sum(total_reservation_revenue), 0) as rpt_res,
        coalesce(sum(total_pos_revenue), 0) as rpt_pos
    from {{ ref('rpt_park_revenue_summary') }}
)

select
    fct_res.total_res,
    fct_pos.total_pos,
    rpt.rpt_res,
    rpt.rpt_pos
from fct_res as fct_res
cross join fct_pos as fct_pos
cross join rpt as rpt
where
    round(fct_res.total_res, 2) != round(rpt.rpt_res, 2)
    or round(fct_pos.total_pos, 2) != round(rpt.rpt_pos, 2)
