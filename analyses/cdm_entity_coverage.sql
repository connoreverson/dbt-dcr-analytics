-- CDM entity coverage summary for all integration models in the crosswalk.
--
-- Shows how many columns each integration model has declared against its
-- assigned CDM entity (via seeds/cdm_crosswalk.csv) compared to the total
-- column count for that entity across all catalog seeds.
--
-- Usage:
--   dbt compile --select cdm_entity_coverage  (inspect compiled SQL)
--   dbt show --select cdm_entity_coverage     (run and display results)

with

crosswalk as (

    select distinct
        integration_model,
        cdm_entity,
        cdm_column_name
    from {{ ref('cdm_crosswalk') }}
    where cdm_column_name is not null
      and cdm_column_name != ''

),

all_cdm_columns as (

    select cdm_entity_name, dbt_column_name
    from {{ ref('column_catalog_asset') }}
    where dbt_column_name is not null
      and dbt_column_name != ''

    union all

    select cdm_entity_name, dbt_column_name
    from {{ ref('column_catalog_visits') }}
    where dbt_column_name is not null
      and dbt_column_name != ''

    union all

    select cdm_entity_name, dbt_column_name
    from {{ ref('column_catalog_application_common') }}
    where dbt_column_name is not null
      and dbt_column_name != ''

    union all

    select cdm_entity_name, dbt_column_name
    from {{ ref('column_catalog_non_profit_core') }}
    where dbt_column_name is not null
      and dbt_column_name != ''

    union all

    select cdm_entity_name, dbt_column_name
    from {{ ref('column_catalog_dcr_extensions') }}
    where dbt_column_name is not null
      and dbt_column_name != ''

),

entity_column_counts as (

    select
        cdm_entity_name,
        count(*) as total_cdm_columns
    from all_cdm_columns
    group by cdm_entity_name

),

model_coverage as (

    select
        xw.integration_model,
        xw.cdm_entity,
        count(distinct xw.cdm_column_name) as mapped_columns,
        ec.total_cdm_columns,
        round(
            100.0
            * count(distinct xw.cdm_column_name)
            / nullif(ec.total_cdm_columns, 0),
            1
        ) as coverage_pct
    from crosswalk xw
    left join entity_column_counts ec
        on xw.cdm_entity = ec.cdm_entity_name
    group by
        xw.integration_model,
        xw.cdm_entity,
        ec.total_cdm_columns

)

select
    integration_model,
    cdm_entity,
    mapped_columns,
    total_cdm_columns,
    coverage_pct,
    case
        when total_cdm_columns is null then 'No catalog entry'
        when coverage_pct >= 50        then 'Above threshold'
        else                                'Below threshold — review for CDM exception'
    end as coverage_status
from model_coverage
order by integration_model

