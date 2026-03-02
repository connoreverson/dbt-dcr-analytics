{% macro identify_candidate_cdm(model_name, top_n=10) %}

{#
    Identify candidate CDM entities for an integration model by comparing the
    model's business columns against every entity schema in the CDM catalog seeds.

    Invoke via:
        dbt run-operation identify_candidate_cdm --args '{model_name: "int_xxx"}'
        dbt run-operation identify_candidate_cdm --args '{model_name: "int_xxx", top_n: 5}'

    Requirements:
        - The target model must be materialized in the warehouse before running.
          The macro uses adapter.get_columns_in_relation() which requires the
          relation to exist.
        - All CDM catalog seeds must be loaded (dbt seed).

    Column filtering:
        Surrogate keys (_sk suffix), FK reference columns (_ prefix), and primary
        ID columns (_id suffix) are excluded from matching. Only business-content
        columns (e.g. first_name, amount, book_date) participate in coverage scoring.

    Coverage interpretation:
        Large CDM entities (e.g. Contact with 192 columns) will show low percentage
        coverage even for semantically correct matches. Review both matched count and
        coverage_pct together. If the top candidate is below 50% coverage, the macro
        will recommend running the cdm-exception-request skill.
#}

{% if execute %}

    {# Resolve the integration model relation #}
    {% set model_relation = ref(model_name) %}

    {# Get the model's actual columns at runtime #}
    {% set all_columns = adapter.get_columns_in_relation(model_relation) %}

    {# Filter out infrastructure columns to focus on business-content columns #}
    {% set business_columns = [] %}
    {% for col in all_columns %}
        {% set col_lower = col.name | lower %}
        {% if not col_lower.endswith('_sk')
           and not col_lower.startswith('_')
           and not col_lower.endswith('_id') %}
            {% do business_columns.append(col_lower) %}
        {% endif %}
    {% endfor %}

    {% do log("", info=True) %}
    {% do log("=== CDM Candidate Identification: " ~ model_name ~ " ===", info=True) %}

    {% if business_columns | length == 0 %}

        {% do log(
            "No business columns found after filtering surrogate keys (_sk), "
            ~ "FK columns (_ prefix), and ID columns (_id). "
            ~ "Verify the model is materialized and inspect its column list.",
            info=True
        ) %}

    {% else %}

        {% do log("Business columns evaluated: " ~ business_columns | join(", "), info=True) %}
        {% do log("", info=True) %}

        {# Build the SQL IN-list for the column match predicate #}
        {% set col_in_list = "'" ~ (business_columns | join("', '")) ~ "'" %}

        {% set coverage_sql %}

            with

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

            coverage as (

                select
                    cdm_entity_name,
                    count(*) as total_entity_columns,
                    sum(
                        case when dbt_column_name in ({{ col_in_list }}) then 1 else 0 end
                    ) as matched_columns,
                    round(
                        100.0
                        * sum(case when dbt_column_name in ({{ col_in_list }}) then 1 else 0 end)
                        / nullif(count(*), 0),
                        1
                    ) as coverage_pct
                from all_cdm_columns
                group by cdm_entity_name
                having sum(case when dbt_column_name in ({{ col_in_list }}) then 1 else 0 end) > 0

            )

            select
                cdm_entity_name,
                total_entity_columns,
                matched_columns,
                coverage_pct
            from coverage
            order by matched_columns desc, coverage_pct desc
            limit {{ top_n }}

        {% endset %}

        {% set results = run_query(coverage_sql) %}

        {% if results.rows | length == 0 %}

            {% do log(
                "No CDM entity column matches found for the business columns above.",
                info=True
            ) %}
            {% do log(
                "Recommendation: Run the cdm-exception-request skill to document "
                ~ "a CDM_EXCEPTION for " ~ model_name ~ ".",
                info=True
            ) %}

        {% else %}

            {% do log(
                "Top CDM entity candidates (ranked by matched columns, then coverage %):",
                info=True
            ) %}
            {% do log("", info=True) %}

            {% for row in results.rows %}
                {% set entity  = row[0] %}
                {% set total   = row[1] %}
                {% set matched = row[2] %}
                {% set pct     = row[3] %}
                {% do log(
                    loop.index | string ~ ". " ~ entity
                    ~ "  —  " ~ matched ~ "/" ~ total ~ " columns matched"
                    ~ "  (" ~ pct ~ "%)",
                    info=True
                ) %}
            {% endfor %}

            {% do log("", info=True) %}

            {% set top_pct = results.rows[0][3] | float %}

            {% if top_pct < 50 %}
                {% do log(
                    "WARNING: Top CDM entity coverage is " ~ top_pct
                    ~ "% (below 50% threshold).",
                    info=True
                ) %}
                {% do log(
                    "Recommendation: Run the cdm-exception-request skill to document "
                    ~ "a CDM_EXCEPTION for " ~ model_name ~ ".",
                    info=True
                ) %}
            {% else %}
                {% do log(
                    "Top candidate exceeds 50% threshold. Confirm entity alignment "
                    ~ "and update seeds/cdm_crosswalk.csv.",
                    info=True
                ) %}
            {% endif %}

        {% endif %}

    {% endif %}

    {% do log("", info=True) %}

{% endif %}

{% endmacro %}
