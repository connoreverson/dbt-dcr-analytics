{% macro get_cdm_columns(entity) %}
    
    {% if not entity or entity | trim == '' %}
        {% do exceptions.raise_compiler_error("get_cdm_columns requires a non-empty entity argument") %}
    {% endif %}

    {% set query %}
        select lower(dbt_column_name) as dbt_column_name
        from {{ ref('int_cdm_columns') }}
        where cdm_entity_name = '{{ entity | replace("'", "''") }}'
    {% endset %}

    {% set results = run_query(query) %}
    
    {% if execute %}
        {% set column_list = results.columns[0].values() %}
        {{ return(column_list) }}
    {% else %}
        {{ return([]) }}
    {% endif %}
    
{% endmacro %}
