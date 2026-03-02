with

source as (
    select * from {{ source('stategov', 'general_ledger') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.gl_entry_id']) }} as hk_general_ledger,
        --  ids
        cast(source.gl_entry_id as varchar) as gl_entry_id,
        --  account id (compound: {fund}-DIV-{div}-PRG-{prog}-OBJ-{obj}) kept whole and split
        cast(source.account_id as varchar) as account_id,
        cast(regexp_extract(source.account_id, '^(\d+)-DIV', 1) as varchar) as account_fund_code,
        cast(regexp_extract(source.account_id, '-DIV-(\w+)-PRG', 1) as varchar) as account_division_code,
        cast(regexp_extract(source.account_id, '-PRG-(\w+)-OBJ', 1) as varchar) as account_program_code,
        cast(regexp_extract(source.account_id, '-OBJ-(\w+)$', 1) as varchar) as account_object_code,
        --  period
        cast(source.fiscal_year as integer) as fiscal_year,
        cast(source.accounting_month as integer) as accounting_month,
        --  classification
        cast(source.entry_type as varchar) as entry_type,
        --  numerics
        cast(source.amount as decimal(12, 2)) as amount,
        --  audit
        cast(source.batch_reference as varchar) as batch_reference,
        --  batch_detail_text: pipe-delimited invoice memo (format: INV|amount|description|date, repeating)
        --  kept as raw text at staging; unpacking to rows is an integration-layer responsibility
        cast(source.batch_detail_text as varchar) as batch_detail_text,
        --  derived: count of invoice records embedded in the batch detail memo
        case
            when source.batch_detail_text is null then null
            else cast(
                (length(source.batch_detail_text) - length(replace(source.batch_detail_text, 'INV-', ''))) / 4
                as integer
            )
        end as batch_entry_count
    from source

)

select * from final
