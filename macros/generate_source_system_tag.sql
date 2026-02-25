{% macro generate_source_system_tag(system_code) %}
    
    {% if not system_code %}
        {% do exceptions.raise_compiler_error("generate_source_system_tag requires a system_code argument") %}
    {% endif %}

    cast('{{ system_code }}' as varchar)

{% endmacro %}
