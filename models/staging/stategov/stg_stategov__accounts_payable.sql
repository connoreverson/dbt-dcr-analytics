with

source as (
    select * from {{ source('stategov', 'accounts_payable') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.invoice_id']) }} as hk_accounts_payable,
        --  ids
        cast(source.invoice_id as varchar) as invoice_id,
        cast(source.vendor_id as varchar) as vendor_id,
        cast(source.encumbrance_id as varchar) as encumbrance_id,
        --  account id (compound: {fund}-DIV-{div}-PRG-{prog}-OBJ-{obj}) kept whole and split
        cast(source.account_id as varchar) as account_id,
        cast(regexp_extract(source.account_id, '^(\d+)-DIV', 1) as varchar) as account_fund_code,
        cast(regexp_extract(source.account_id, '-DIV-(\w+)-PRG', 1) as varchar) as account_division_code,
        cast(regexp_extract(source.account_id, '-PRG-(\w+)-OBJ', 1) as varchar) as account_program_code,
        cast(regexp_extract(source.account_id, '-OBJ-(\w+)$', 1) as varchar) as account_object_code,
        --  dates
        cast(source.invoice_date as date) as invoice_date,
        cast(source.payment_date as date) as payment_date,
        --  numerics
        cast(source.amount as decimal(12, 2)) as amount,
        --  status
        cast(source.status as varchar) as status
    from source

)

select * from final
