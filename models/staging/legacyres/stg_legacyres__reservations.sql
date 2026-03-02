with

source as (
    select * from {{ source('legacyres', 'legacy_reservations') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.res_id']) }} as hk_reservations,  -- noqa: LT05
        --  ids
        cast(source.res_id as varchar) as reservation_id,
        cast(source.legacy_cust_id as varchar) as legacy_customer_id,
        cast(source.legacy_park_id as varchar) as legacy_park_id,
        --  dates (three incompatible source formats normalized to date)
        --  FlatFile era: MMDDYYYY (no separator)
        --  SQLDump era:  YYYY-MM-DD
        --  Export era:   MM/DD/YY
        coalesce(
            try_strptime(source.arrival_date, '%Y-%m-%d'),
            try_strptime(source.arrival_date, '%m%d%Y'),
            try_strptime(source.arrival_date, '%m/%d/%y')
        ) as arrival_date,
        coalesce(
            try_strptime(source.departure_date, '%Y-%m-%d'),
            try_strptime(source.departure_date, '%m%d%Y'),
            try_strptime(source.departure_date, '%m/%d/%y')
        ) as departure_date,
        --  numerics
        cast(source.total_paid as decimal(10, 2)) as total_paid,
        --  audit / provenance
        cast(source.data_format_source as varchar) as data_format_source,
        --  guest detail (pipe-delimited; FlatFile_2005_2010 era only)
        --  format: 'Adults:3|Kids:2|Pets:2|Vehicles:1'
        try_cast(
            nullif(regexp_extract(source.guest_info, 'Adults:(\d+)', 1), '')
            as integer
        ) as guest_count_adults,
        try_cast(
            nullif(regexp_extract(source.guest_info, 'Kids:(\d+)', 1), '')
            as integer
        ) as guest_count_children,
        try_cast(
            nullif(regexp_extract(source.guest_info, 'Pets:(\d+)', 1), '')
            as integer
        ) as guest_count_pets,
        try_cast(
            nullif(regexp_extract(source.guest_info, 'Vehicles:(\d+)', 1), '')
            as integer
        ) as guest_count_vehicles
    from source

)

select * from final
