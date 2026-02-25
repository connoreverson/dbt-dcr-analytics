{% macro clean_string(column_name) %}
    
    {% if not column_name %}
        {% do exceptions.raise_compiler_error("clean_string requires a column_name argument") %}
    {% endif %}

    trim(
        regexp_replace(
            cast({{ column_name }} as varchar),
            '[^a-zA-Z0-9 _-]', 
            '', 
            'g'
        )
    )

{% endmacro %}
