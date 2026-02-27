-- depends_on: {{ ref('int_cdm_columns') }}
-- depends_on: {{ ref('cdm_crosswalk') }}

with

source as (
    select * from {{ ref('stg_vistareserve__reservations') }}
),

source_contacts as (
    select * from {{ ref('int_contacts') }}
),

source_assets as (
    select * from {{ ref('int_customer_assets') }}
),

joined_reservations as (
    select
        source.*,
        source_contacts.contacts_sk as _contact_sk,
        source_assets.customer_assets_sk as _asset_sk,
        source_assets._parent_park_sk as _park_sk,
        {{ generate_source_system_tag('DCR-REV-01') }} as source_system
    from source
    left join
        source_contacts
        on
            cast(source.customer_id as varchar)
            = cast(source_contacts.contactid as varchar)
    left join
        source_assets
        on
            cast(source.asset_id as varchar)
            = cast(source_assets.customerassetid as varchar)
),

final as (
    {{ generate_cdm_projection(
        integration_model='int_reservations',
        source_model='stg_vistareserve__reservations',
        cte_name='joined_reservations',
        sk_source_columns=['reservation_id'],
        pass_through_columns=[
            '_contact_sk', 
            '_asset_sk', 
            '_park_sk',
            'source_system',
            'reservation_status', 
            'total_amount', 
            'arrival_date', 
            'departure_date', 
            'reservation_created_at', 
            'booking_source', 
            'promo_code',
            'number_of_guests'
        ]
    ) }}
)

select * from final
