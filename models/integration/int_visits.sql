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
        source_assets._parent_park_sk as _park_sk
    from source
    left join
        source_contacts
        on
            cast(source.customer_id as varchar)
            = cast(source_contacts.contact_id as varchar)
    left join
        source_assets
        on
            cast(source.asset_id as varchar)
            = cast(source_assets.customerasset_id as varchar)
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['reservation_id']) }} as visits_sk,
        reservation_id as visit_id,
        _contact_sk,
        _asset_sk,
        _park_sk
    from joined_reservations
)

select * from final
