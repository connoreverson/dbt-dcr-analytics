with

source as (
    select * from {{ source('peoplefirst', 'seasonal_workforce') }}
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['source.seasonal_emp_id']) }} as hk_seasonal_employee,
        cast(source.seasonal_emp_id as varchar) as seasonal_emp_id,
        md5(cast(source.first_name as varchar)) as first_name_hash,
        md5(cast(source.last_name as varchar)) as last_name_hash,
        cast(source.org_unit_id as varchar) as org_unit_id,
        cast(source.season_year as integer) as season_year,
        cast(source.actual_start_date as date) as actual_start_date,
        cast(source.system_onboard_date as date) as system_onboard_date,
        cast(source.separation_date as date) as separation_date,
        cast(source.hourly_rate as decimal(6, 2)) as hourly_rate,
        cast(source._is_deleted as boolean) as is_deleted
    from source
)

select * from final
