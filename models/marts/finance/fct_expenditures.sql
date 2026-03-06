with

gl as (
    select * from {{ ref('int_financial_transactions') }}
    where entry_type = 'Expenditure'
),

ap as (
    select
        account_id,
        amount,
        max(cast(vendor_id as varchar)) as vendor_id
    from {{ ref('stg_stategov__accounts_payable') }}
    group by account_id, amount
),

final as (
    select
        gl.financials_sk as expenditure_sk,
        gl.gl_entry_id as source_record_id,
        case
            when ap.vendor_id is not null then {{ dbt_utils.generate_surrogate_key(['ap.vendor_id']) }}
        end as vendors_sk,
        cast(null as varchar) as parks_sk,
        cast(
            cast(gl.fiscal_year as varchar) || '-'
            || lpad(cast(gl.accounting_month as varchar), 2, '0') || '-01'
            as date
        ) as expenditure_month_date,
        gl.amount,
        gl.account_fund_code,
        gl.fund_description,
        gl.account_division_code,
        gl.division_description,
        gl.account_program_code,
        gl.program_description,
        gl.account_object_code,
        gl.object_description,
        gl.award_id,
        gl.award_amount,
        gl.award_fiscal_year_actual,
        gl.source_system
    from gl
    left join ap
        on
            gl.account_id = ap.account_id
            and gl.amount = ap.amount
)

select * from final
