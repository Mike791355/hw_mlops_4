with customer_metrics as (
    select
        customer_id,
        count() as transaction_count,
        countIf(is_labeled) as labeled_transaction_count,
        countIf(is_fraud = 1) as fraud_count,
        {{ fraud_rate('countIf(is_fraud = 1)', 'countIf(is_labeled)') }} as fraud_rate,
        sum(amount) as total_amount,
        sumIf(amount, is_fraud = 1) as fraud_amount,
        avg(amount) as avg_amount,
        min(transaction_time) as first_transaction_at,
        max(transaction_time) as last_transaction_at,
        uniqExact(toDate(transaction_time)) as active_days
    from {{ ref('stg_transactions') }}
    group by customer_id
)

select
    *,
    {{ risk_level('fraud_rate') }} as risk_level,
    labeled_transaction_count > 0 as has_known_risk
from customer_metrics
