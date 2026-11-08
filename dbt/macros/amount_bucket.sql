{% macro amount_bucket(column_name) -%}
    case
        when {{ column_name }} >= {{ var('large_amount_threshold') }} then 'LARGE'
        when {{ column_name }} >= {{ var('medium_amount_threshold') }} then 'MEDIUM'
        else 'SMALL'
    end
{%- endmacro %}
