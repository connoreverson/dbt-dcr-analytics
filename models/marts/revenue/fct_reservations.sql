with

int_reservations as (
    select * from {{ ref('int_reservations') }}
),

fct_reservations as (
    select
        cast(reservations_sk as varchar) as reservations_sk,

        -- Dimension Keys
        cast(_contact_sk as varchar) as contacts_sk,
        cast(_asset_sk as varchar) as customer_assets_sk,
        cast(_park_sk as varchar) as parks_sk,

        -- Measures
        cast(reservation_status as varchar) as reservation_status,
        cast(total_amount as decimal(10, 2)) as reservation_amount,

        -- Dates
        cast(arrival_date as date) as check_in_date,
        cast(departure_date as date) as check_out_date,
        cast(reservation_created_at as timestamp) as reservation_created_at,

        cast(
            date_diff(
                'day', cast(arrival_date as date), cast(departure_date as date)
            ) as integer
        ) as nights_stayed,

        -- Attributes
        cast(booking_source as varchar) as booking_source,
        cast(promo_code as varchar) as promo_code,
        cast(number_of_guests as integer) as number_of_guests

    from int_reservations
)

select * from fct_reservations
