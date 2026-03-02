with

source as (
    select * from {{ source('stategov', 'budget_activity_log') }}
),

final as (

    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.log_sequence_id']) }} as hk_budget_activity_log,
        --  ids
        cast(source.log_sequence_id as varchar) as log_sequence_id,
        --  period
        cast(source.fiscal_year as integer) as fiscal_year,
        cast(source.accounting_period as integer) as accounting_period,
        --  account id (compound: {fund}-DIV-{div}-PRG-{prog}-OBJ-{obj}) kept whole and split
        cast(source.account_id as varchar) as account_id,
        cast(regexp_extract(source.account_id, '^(\d+)-DIV', 1) as varchar) as account_fund_code,
        cast(regexp_extract(source.account_id, '-DIV-(\w+)-PRG', 1) as varchar) as account_division_code,
        cast(regexp_extract(source.account_id, '-PRG-(\w+)-OBJ', 1) as varchar) as account_program_code,
        cast(regexp_extract(source.account_id, '-OBJ-(\w+)$', 1) as varchar) as account_object_code,
        --  classification
        cast(source.activity_type as varchar) as activity_type,
        --  date (COBOL YYYYMMDD text format normalized to date)
        try_strptime(source.effective_date, '%Y%m%d') as effective_date,
        --  numerics
        cast(source.amount as decimal(12, 2)) as amount,
        --  optional references (populated by activity_type; see source docs for nullability rules)
        cast(source.vendor_id as varchar) as vendor_id,
        cast(source.encumbrance_ref as varchar) as encumbrance_ref,
        cast(source.revenue_source_code as varchar) as revenue_source_code,
        cast(source.appropriation_auth as varchar) as appropriation_auth,
        cast(source.allotment_period as varchar) as allotment_period,
        --  audit
        cast(source.batch_id as varchar) as batch_id,
        cast(source.entry_operator as varchar) as entry_operator
    from source

)

select * from final
