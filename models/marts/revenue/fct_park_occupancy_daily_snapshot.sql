with

fct_reservations as (
    select * from {{ ref('fct_reservations') }}
),

dim_date as (
    select * from {{ ref('dim_date') }}
),

dim_parks as (
    select * from {{ ref('dim_parks') }}
),

/*
    Date spine fan-out: for each reservation, generate one row per calendar
    day that falls within the stay window. Check-in is the first night
    on-site; check-out is the morning the guest departs, so the last night
    on-site is (check_out_date - 1 day). The join condition reflects this:
    full_date >= check_in_date AND full_date < check_out_date.

    Reservations with null or same-day check-in/check-out dates are excluded
    because they produce no valid overnight stay interval.
*/
stays_by_day as (
    select
        dim_date.full_date as snapshot_date,
        fct_reservations.parks_sk,
        fct_reservations.reservations_sk,
        fct_reservations.number_of_guests,
        fct_reservations.reservation_amount,
        cast(dim_date.calendar_year as bigint) as calendar_year,
        cast(dim_date.calendar_month as bigint) as calendar_month,
        cast(dim_date.calendar_quarter as bigint) as calendar_quarter,
        cast(dim_date.fiscal_year as bigint) as fiscal_year,
        cast(dim_date.fiscal_month as bigint) as fiscal_month,
        dim_date.day_name,
        cast(dim_date.day_of_month as bigint) as day_of_month
    from fct_reservations
    inner join dim_date
        on
            fct_reservations.check_in_date <= dim_date.full_date
            and fct_reservations.check_out_date > dim_date.full_date
    where
        fct_reservations.check_in_date is not null
        and fct_reservations.check_out_date is not null
        and fct_reservations.check_out_date > fct_reservations.check_in_date
),

/*
    Aggregate the fanned-out rows to the target grain:
    one row per park per calendar day.
*/
occupancy_by_park_day as (
    select
        parks_sk,
        snapshot_date,
        calendar_year,
        calendar_month,
        calendar_quarter,
        fiscal_year,
        fiscal_month,
        day_name,
        day_of_month,
        cast(count(reservations_sk) as bigint) as active_reservation_count,
        cast(sum(number_of_guests) as bigint) as total_guests_on_site,
        sum(reservation_amount) as total_reservation_revenue_in_stay
    from stays_by_day
    group by
        parks_sk,
        snapshot_date,
        calendar_year,
        calendar_month,
        calendar_quarter,
        fiscal_year,
        fiscal_month,
        day_name,
        day_of_month
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key([
            'occupancy_by_park_day.parks_sk', 'occupancy_by_park_day.snapshot_date'
        ]) }} as occupancy_snapshot_sk,
        occupancy_by_park_day.parks_sk,
        dim_parks.park_name,
        dim_parks.region,
        occupancy_by_park_day.snapshot_date,
        occupancy_by_park_day.calendar_year,
        occupancy_by_park_day.calendar_month,
        occupancy_by_park_day.calendar_quarter,
        occupancy_by_park_day.fiscal_year,
        occupancy_by_park_day.fiscal_month,
        occupancy_by_park_day.day_name,
        occupancy_by_park_day.day_of_month,
        occupancy_by_park_day.active_reservation_count,
        occupancy_by_park_day.total_guests_on_site,
        cast(occupancy_by_park_day.total_reservation_revenue_in_stay as decimal(14, 2))
            as total_reservation_revenue_in_stay
    from occupancy_by_park_day
    left join dim_parks
        on occupancy_by_park_day.parks_sk = dim_parks.parks_sk
)

select * from final
