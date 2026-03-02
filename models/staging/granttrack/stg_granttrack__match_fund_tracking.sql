with

source as (
    select * from {{ source('granttrack', 'match_fund_tracking') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.match_id']) }} as hk_match_fund,
        --  ids
        cast(source.match_id as varchar) as match_id,
        cast(source.award_id as varchar) as award_id,
        --  attributes
        cast(source.match_type as varchar) as match_type,
        cast(source.description as varchar) as description,
        --  contributors: comma-separated list of organisations and individuals
        --  preserved as raw text; normalising to rows is an integration-layer responsibility
        cast(source.contributors as varchar) as contributors,
        --  amounts
        cast(source.amount_value as decimal(10, 2)) as amount_value,
        --  dates
        cast(source.transaction_date as date) as transaction_date
    from source
)

select * from final
