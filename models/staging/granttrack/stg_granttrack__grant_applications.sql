with

source as (
    select * from {{ source('granttrack', 'grant_applications') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.application_id']) }} as hk_grant_application,
        --  ids
        cast(source.application_id as varchar) as application_id,
        --  attributes
        cast(source.grant_program as varchar) as grant_program,
        cast(source.status as varchar) as status,
        --  dates
        cast(source.submission_date as date) as submission_date,
        cast(source.estimated_award_date as date) as estimated_award_date,
        --  amounts
        cast(source.requested_amount as decimal(12, 2)) as requested_amount,
        --  primary_contact: pipe-delimited "name|email|phone" — split into components
        cast(source.primary_contact as varchar) as primary_contact_raw,
        cast(regexp_extract(source.primary_contact, '^([^|]*)', 1) as varchar) as contact_name,
        cast(regexp_extract(source.primary_contact, '\|([^|]*)\|', 1) as varchar) as contact_email,
        cast(regexp_extract(source.primary_contact, '\|([^|]*)$', 1) as varchar) as contact_phone
    from source
)

select * from final
