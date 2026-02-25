-- depends_on: {{ ref('int_cdm_columns') }}
-- depends_on: {{ ref('cdm_crosswalk') }}

with

source as (
    select 
        *,
        first_name as firstname,
        last_name as lastname,
        email as emailaddress1,
        phone as telephone1
    from {{ ref('stg_vistareserve__customer_profiles') }}
),

final as (
    {{ generate_cdm_projection(
        integration_model='int_contacts', 
        source_model='stg_vistareserve__customer_profiles',
        cte_name='source',
        sk_source_columns=['customer_id'],
        pass_through_columns=[
            'account_created_at',
            'address_state',
            'has_annual_pass',
            'is_senior',
            'is_veteran',
            generate_source_system_tag('DCR-REV-01') ~ " as source_system"
        ]
    ) }}
)

select * from final
