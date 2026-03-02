with

source as (
    select * from {{ source('granttrack', 'reimbursement_requests') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.request_id']) }} as hk_reimbursement_request,
        --  ids
        cast(source.request_id as varchar) as request_id,
        cast(source.award_id as varchar) as award_id,
        --  encumbrance reference linking to StateGov financials
        cast(source.sgf_encumbrance_ref as varchar) as sgf_encumbrance_ref,
        --  amounts
        cast(source.requested_amount as decimal(10, 2)) as requested_amount,
        cast(source.approved_amount as decimal(10, 2)) as approved_amount,
        --  dates
        cast(source.submission_date as date) as submission_date,
        cast(source.receipt_date as date) as receipt_date
    from source
)

select * from final
