-- depends_on: {{ ref('int_cdm_columns') }}
-- depends_on: {{ ref('cdm_crosswalk') }}

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
        source_parks.parks_sk as _park_sk,
        {{ generate_source_system_tag('DCR-REV-01') }} as source_system
    from source
    left join
        source_contacts
        on
            cast(source.customer_id as varchar)
            = cast(source_contacts.contactid as varchar)
    left join
        source_parks
        on {{ get_geoparks_account_number('source.park_id') }} = source_parks.accountnumber
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
    {{ generate_cdm_projection(
        integration_model='int_transactions',
        source_model='stg_vistareserve__pos_transactions',
        cte_name='joined_transactions',
        sk_source_columns=['transaction_id'],
        pass_through_columns=[
            '_contact_sk', 
            '_park_sk', 
            'source_system',
            'transaction_amount',
            'revenue_category',
            'is_kiosk_entry',
            'transaction_created_at'
        ]
    ) }}
)

select * from final
