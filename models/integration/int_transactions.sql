with

source as (
    select * from {{ ref('stg_vistareserve__pos_transactions') }}
),

source_contacts as (
    select * from {{ ref('int_contacts') }}
),

source_parks as (
    select * from {{ ref('int_parks') }}
),

joined_transactions as (
    select
        source.*,
        source_contacts.contacts_sk as _contact_sk,
        source_parks.parks_sk as _park_sk
    from source
    left join
        source_contacts
        on
            cast(source.customer_id as varchar)
            = cast(source_contacts.contact_id as varchar)
    left join
        source_parks
        on
            {{ get_geoparks_account_number('source.park_id') }}
            = source_parks.accountnumber
),

/*
    Open Question #2: Revenue Batch Integration
    'revenue_batch' records represent aggregated daily batches rather
    than individual customer-level point-of-sale transactions. Unioning
    them here would mix grains and distort transaction counts. Revenue
    batches are excluded from this model and will be modeled separately
    (e.g., int_revenue_batches) per the spec.
*/
final as (
    select
        {{ dbt_utils.generate_surrogate_key(['transaction_id']) }} as transactions_sk,
        transaction_id,
        transaction_created_at as book_date,
        transaction_amount as amount,
        _contact_sk,
        _park_sk
    from joined_transactions
)

select * from final
