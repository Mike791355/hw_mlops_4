{% set marts = [
    'mart_daily_state_metrics', 'mart_fraud_by_category', 'mart_fraud_by_state',
    'mart_customer_risk_profile', 'mart_hourly_fraud_pattern', 'mart_merchant_analytics'
] %}

with staging as (
    select
        count() as row_count,
        sum(amount) as total_amount,
        countIf(is_labeled) as labeled_count,
        countIf(is_fraud = 1) as fraud_count,
        sumIf(amount, is_fraud = 1) as fraud_amount
    from {{ ref('stg_transactions') }}
)

{% for mart in marts %}
select '{{ mart }}' as model_name
from (
    select
        sum(transaction_count) as row_count,
        sum(total_amount) as total_amount{% if mart != 'mart_daily_state_metrics' %},
            sum(labeled_transaction_count) as labeled_count,
            sum(fraud_count) as fraud_count,
            sum(fraud_amount) as fraud_amount
        {% endif %}
    from {{ ref(mart) }}
) as m
cross join staging as s
where
    m.row_count != s.row_count
    or m.total_amount != s.total_amount
    {% if mart != 'mart_daily_state_metrics' %}
        or m.labeled_count != s.labeled_count
        or m.fraud_count != s.fraud_count
        or m.fraud_amount != s.fraud_amount
    {% endif %}
{% if not loop.last %}
union all
{% endif %}
{% endfor %}
