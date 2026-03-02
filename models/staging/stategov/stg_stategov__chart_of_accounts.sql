with

source as (
    select * from {{ source('stategov', 'chart_of_accounts') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.account_id']) }} as hk_chart_of_accounts,
        --  natural key
        cast(source.account_id as varchar) as account_id,
        --  fund dimension
        cast(source.fund_code as varchar) as fund_code,
        cast(source.fund_description as varchar) as fund_description,
        --  division dimension
        cast(source.division_code as varchar) as division_code,
        cast(source.division_description as varchar) as division_description,
        --  program dimension
        cast(source.program_code as varchar) as program_code,
        cast(source.program_description as varchar) as program_description,
        --  object dimension (expenditure/revenue type)
        cast(source.object_code as varchar) as object_code,
        cast(source.object_description as varchar) as object_description
    from source

)

select * from final
