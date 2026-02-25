{% macro generate_staging_model(source_schema=None,source_table=None,relation=None) %}

{% if source_table is not none %}
    {%- set from_expression -%}
        {% raw %}{{ source({% endraw %}'{{ source_schema }}','{{ source_table}}'{% raw %}) }}{% endraw %}
    {% endset -%}
    {% set staging_relation = source(source_schema,source_table) %}
{% else %}
    {% set from_expression %}
        {% raw %}{{ ref({% endraw %}'{{ relation }}'{% raw %}) }}{% endraw %}
    {% endset %}
    {% set staging_relation = ref(relation) %}
{% endif %}

{%- set columns = adapter.get_columns_in_relation(staging_relation) -%}

{% set id_columns = [] %}

{% set metadata_columns = [] %}

{% for column in columns %}
    {% if column.name !="_fivetran_id" %}
        {% do id_columns.append(column.name) if modules.re.search('(?:id[A-Z]|id(?=$))', column.name, flags=modules.re.IGNORECASE) is not none %}
    {% endif %}
{% endfor %}

{% for column in columns %}
{% do metadata_columns.append(column.name) if modules.re.search('^_', column.name, flags=modules.re.IGNORECASE) is not none %}
{% endfor %}


{% set data_columns = columns|rejectattr('name','in',id_columns)|rejectattr('name','in',metadata_columns)|list %}

{% set string_data_types = ['VARCHAR'] %}
{% set numeric_data_types = ['INTEGER','BIGINT','HUGEINT','FLOAT','DOUBLE','DECIMAL','NUMERIC','TINYINT','SMALLINT'] %}
{% set boolean_data_types =  ['BOOLEAN'] %}
{% set date_time_data_types = ['DATE','TIMESTAMP','TIME','INTERVAL'] %}
{% set semi_structured_data_types = ['LIST','STRUCT','MAP','JSON'] %}


{% set column_categories = dict() %}

{% do column_categories.update({'ids': columns|selectattr('name','in',id_columns)|list}) %}
{% do column_categories.update({'strings': data_columns|selectattr('data_type','in',string_data_types)|list}) %}
{% do column_categories.update({'numerics': data_columns|selectattr('data_type','in',numeric_data_types)|list}) %}
{% do column_categories.update({'booleans': data_columns|selectattr('data_type','in',boolean_data_types)|list}) %}
{% do column_categories.update({'dates/timestamps': data_columns|selectattr('data_type','in',date_time_data_types)|list}) %}
{% do column_categories.update({'semi_structured': data_columns|selectattr('data_type','in',semi_structured_data_types)|list}) %}
{% do column_categories.update({'metadata': columns|selectattr('name','in',metadata_columns)|list}) %}



{% set staging_model_sql %}
with

source as (

    select * from {{ from_expression }}

),

final as (

    select
{% for category,columns in column_categories.items() %}
{{'--  ' + category}} 
{%- set outer_loop_last = loop.last %}
    {% for column in columns|sort(attribute='name') %}
        {%- set all_loops_last = outer_loop_last and loop.last -%}
        cast(source.{{ column.name }} as {{ column.data_type | lower}}) as {{column.name | lower}}{{',' if not all_loops_last}}
    {% endfor -%}
{% endfor -%}
    from source

)

select * from final
{% endset %}

{% if execute %}

{{ log(staging_model_sql, info=True) }}
{% do return(staging_model_sql) %}

{% endif %}
{% endmacro %}