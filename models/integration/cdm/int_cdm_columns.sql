{{ config(
    materialized='view'
) }}

{% set relations = [
    ref('column_catalog_asset'),
    ref('column_catalog_visits'),
    ref('column_catalog_application_common'),
    ref('column_catalog_cdmfoundation'),
    ref('column_catalog_non_profit_core')
] %}

with

unioned_catalogs as (
    {{ dbt_utils.union_relations(relations=relations) }}
),

deduped as (
    select
        cdm_entity_name,
        dbt_column_name,
        max(dbt_data_type) as dbt_data_type,
        max(cast(is_primary_key as integer)) as is_primary_key,
        max(cast(is_foreign_key as integer)) as is_foreign_key,
        max(description) as description
    from unioned_catalogs
    group by 1, 2
),

final as (
    select 
        cdm_entity_name,
        dbt_column_name,
        dbt_data_type,
        cast(is_primary_key as boolean) as is_primary_key,
        cast(is_foreign_key as boolean) as is_foreign_key,
        description
    from deduped
)

select * from final
