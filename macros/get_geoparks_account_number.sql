{% macro get_geoparks_account_number(park_id_column) %}

    printf('GP-%03d', {{ park_id_column }})

{% endmacro %}
