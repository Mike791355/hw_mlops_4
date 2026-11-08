{% macro fraud_rate(fraud_count, labeled_count) -%}
    100.0 * {{ fraud_count }} / nullIf({{ labeled_count }}, 0)
{%- endmacro %}
