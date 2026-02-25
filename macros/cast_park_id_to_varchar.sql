{% macro cast_park_id_to_varchar(column_name) %}
    
    {% if not column_name %}
        {% do exceptions.raise_compiler_error("cast_park_id_to_varchar requires a column_name argument") %}
    {% endif %}

    cast(cast({{ column_name }} as integer) as varchar)
    
{% endmacro %}
