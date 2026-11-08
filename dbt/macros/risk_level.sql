{% macro risk_level(rate) -%}
    case
        when {{ rate }} >= {{ var('high_risk_fraud_rate') }} then 'HIGH'
        when {{ rate }} >= {{ var('medium_risk_fraud_rate') }} then 'MEDIUM'
        else 'LOW'
    end
{%- endmacro %}
