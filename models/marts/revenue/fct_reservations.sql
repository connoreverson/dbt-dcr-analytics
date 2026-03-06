with

int_visits as (
    select * from {{ ref('int_visits') }}
),

stg_reservations as (
    select * from {{ ref('stg_vistareserve__reservations') }}
),

fct_reservations as (
    select
        cast(visits_sk as varchar) as reservations_sk,

        -- Dimension Keys
        cast(_contact_sk as varchar) as contacts_sk,
        cast(_asset_sk as varchar) as customer_assets_sk,
        cast(_park_sk as varchar) as parks_sk,

        -- Measures
        cast(stg_reservations.reservation_status as varchar) as reservation_status,
        cast(stg_reservations.total_amount as decimal(10, 2)) as reservation_amount,

        -- Dates
        cast(stg_reservations.arrival_date as date) as check_in_date,
        cast(stg_reservations.departure_date as date) as check_out_date,
        cast(stg_reservations.reservation_created_at as timestamp) as reservation_created_at,

        cast(
            date_diff(
                'day', cast(stg_reservations.arrival_date as date), cast(stg_reservations.departure_date as date)
            ) as integer
        ) as nights_stayed,

        -- Attributes
        cast(stg_reservations.booking_source as varchar) as booking_source,
        cast(stg_reservations.promo_code as varchar) as promo_code,
        cast(stg_reservations.number_of_guests as integer) as number_of_guests

    from int_visits
    left join stg_reservations
        on cast(int_visits.visit_id as varchar) = cast(stg_reservations.reservation_id as varchar)
)

select * from fct_reservations
