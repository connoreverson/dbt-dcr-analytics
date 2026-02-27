{% macro generate_cdm_projection(integration_model, source_model, cte_name='source', sk_source_columns=none, pass_through_columns=none) %}

    {% if not integration_model or integration_model | trim == '' %}
        {% do exceptions.raise_compiler_error("generate_cdm_projection requires a non-empty integration_model argument") %}
    {% endif %}
    
    {% if not source_model or source_model | trim == '' %}
        {% do exceptions.raise_compiler_error("generate_cdm_projection requires a non-empty source_model argument") %}
    {% endif %}

    {% set query %}
        select
            cdm_entity,
            trim(lower(cdm_column_name)) as cdm_column_name,
            trim(lower(staging_column_name)) as staging_column_name
        from {{ ref('cdm_crosswalk') }}
        where integration_model = '{{ integration_model | replace("'", "''") }}'
          and source_model = '{{ source_model | replace("'", "''") }}'
    {% endset %}

    {% set crosswalk_results = run_query(query) %}
    
    {% if execute %}
        {% if crosswalk_results|length == 0 %}
            {% do exceptions.raise_compiler_error(
                "generate_cdm_projection: no crosswalk entries found for integration_model='"
                ~ integration_model ~ "' and source_model='" ~ source_model
                ~ "'. Add the mapping to seeds/cdm_crosswalk.csv and re-run dbt seed."
            ) %}
        {% endif %}
        
        {% set cdm_entity = crosswalk_results.columns[0].values()[0] %}
        {% set authorized_columns = get_cdm_columns(cdm_entity) %}
        
        {% set sk_column = integration_model | replace('int_', '') ~ '_sk' %}
        
        {# Handle Surrogate Key Logic #}
        {% set sk_logic = '' %}
        {% if sk_source_columns %}
            {% set sk_logic = dbt_utils.generate_surrogate_key(sk_source_columns) %}
        {% else %}
            {% do log("WARNING: generate_cdm_projection used implicit surrogate key generation for " ~ integration_model ~ ". Provide sk_source_columns for deterministic builds.", info=True) %}
            {% set sk_logic = dbt_utils.generate_surrogate_key([crosswalk_results.columns[2].values()[0]]) %}
        {% endif %}

        {% set sql %}
    select
{%- set projected_columns = [sk_logic ~ " as " ~ sk_column] %}
{%- for row in crosswalk_results.rows %}
    {%- set cdm_col = row['cdm_column_name'] %}
    {%- set stg_col = row['staging_column_name'] %}
    {%- if cdm_col == sk_column %}
        {# Skip emitting this column since it's the surrogate key we already injected #}
    {%- elif cdm_col in authorized_columns %}
        {%- do projected_columns.append(stg_col ~ " as " ~ cdm_col) %}
    {%- else %}
        {%- do projected_columns.append("-- WARNING: " ~ cdm_col ~ " is not an authorized CDM column for " ~ cdm_entity ~ "\n        " ~ stg_col ~ " as " ~ cdm_col) %}
    {%- endif %}
{%- endfor %}

{%- if pass_through_columns %}
    {%- for pt_col in pass_through_columns %}
        {%- do projected_columns.append(pt_col) %}
    {%- endfor %}
{%- endif %}
        {{ projected_columns | join(',\n        ') }}
    from {{ cte_name }}
        {% endset %}
        
        {{ return(sql) }}
    {% endif %}
{% endmacro %}
