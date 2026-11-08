with merchant_metrics as (
    select
        merchant,
        count() as transaction_count,
        countIf(is_labeled) as labeled_transaction_count,
        countIf(is_fraud = 1) as fraud_count,
        {{ fraud_rate('countIf(is_fraud = 1)', 'countIf(is_labeled)') }} as fraud_rate,
        sum(amount) as total_amount,
        sumIf(amount, is_fraud = 1) as fraud_amount,
        avg(amount) as avg_amount,
        uniqExact(customer_id) as unique_customers,
        uniqExact(us_state) as unique_states,
        min(transaction_time) as first_transaction_at,
        max(transaction_time) as last_transaction_at
    from {{ ref('stg_transactions') }}
    group by merchant
)

select
    *,
    ifNull(
        labeled_transaction_count >= {{ var('suspicious_min_labeled_transactions') }}
        and fraud_rate >= {{ var('high_risk_fraud_rate') }},
        false
    ) as is_suspicious
from merchant_metrics
