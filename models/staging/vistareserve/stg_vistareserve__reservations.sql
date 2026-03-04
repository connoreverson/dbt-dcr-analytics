with

source as (
    select * from {{ source('vistareserve', 'reservations') }}
),

final as (

    select
        --  hash key


        {{ dbt_utils.generate_surrogate_key(['source.reservation_id']) }}
            as hk_reservations,
        --  ids
        cast(source.asset_id as varchar) as asset_id,
        cast(source.customer_id as varchar) as customer_id,
        cast(source.reservation_id as varchar) as reservation_id,
        --  strings
        cast(source.status as varchar) as reservation_status,
        --  numerics
        cast(source.total_amount as decimal(10, 2)) as total_amount,
        --  dates/timestamps
        cast(source.arrival_date as date) as arrival_date,
        cast(source.booking_date as timestamp) as reservation_created_at,
        cast(source.departure_date as date) as departure_date,
        --  semi_structured (5% of rows have malformed booking_metadata JSON;
        --  sanitize to '{}' before extraction so json_extract_string never
        --  receives invalid input, regardless of vectorized evaluation order)
        cast(
            json_extract_string(
                case
                    when json_valid(source.booking_metadata)
                        then source.booking_metadata
                    else '{}'
                end,
                '$.booking_source'
            ) as varchar
        ) as booking_source,
        cast(
            json_extract_string(
                case
                    when json_valid(source.booking_metadata)
                        then source.booking_metadata
                    else '{}'
                end,
                '$.promo_code'
            ) as varchar
        ) as promo_code,
        cast(
            json_extract_string(
                case
                    when json_valid(source.booking_metadata)
                        then source.booking_metadata
                    else '{}'
                end,
                '$.number_of_guests'
            ) as integer
        ) as number_of_guests
    from source

)

select * from final
