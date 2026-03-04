with

date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2010-01-01' as date)",
        end_date="cast('2030-12-31' as date)"
    ) }}
),

final as (
    select
        cast(date_day as date) as date_sk,
        cast(date_day as date) as full_date,
        extract(year from date_day) as calendar_year,
        extract(month from date_day) as calendar_month,
        extract(day from date_day) as day_of_month,
        extract(quarter from date_day) as calendar_quarter,
        case
            when extract(month from date_day) >= 7 then cast(extract(year from date_day) as integer) + 1
            else cast(extract(year from date_day) as integer)
        end as fiscal_year,
        case
            when extract(month from date_day) >= 7 then cast(extract(month from date_day) as integer) - 6
            else cast(extract(month from date_day) as integer) + 6
        end as fiscal_month,
        case
            when extract(month from date_day) >= 7 then cast(extract(quarter from date_day) as integer) - 2
            when extract(month from date_day) <= 6 then cast(extract(quarter from date_day) as integer) + 2
        end as fiscal_quarter,
        dayname(date_day) as day_name,
        monthname(date_day) as month_name
    from date_spine
)

select * from final
