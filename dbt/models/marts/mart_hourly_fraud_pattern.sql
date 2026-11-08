with hourly_metrics as (
    select
        day_of_week,
        transaction_hour,
        count() as transaction_count,
        countIf(is_labeled) as labeled_transaction_count,
        countIf(is_fraud = 1) as fraud_count,
        {{ fraud_rate('countIf(is_fraud = 1)', 'countIf(is_labeled)') }} as fraud_rate,
        sum(amount) as total_amount,
        sumIf(amount, is_fraud = 1) as fraud_amount
    from {{ ref('stg_transactions') }}
    group by day_of_week, transaction_hour
),

baseline as (
    select
        {{ fraud_rate('countIf(is_fraud = 1)', 'countIf(is_labeled)') }} as baseline_fraud_rate
    from {{ ref('stg_transactions') }}
)

select
    h.*,
    b.baseline_fraud_rate,
    ifNull(
        h.labeled_transaction_count >= {{ var('suspicious_min_labeled_transactions') }}
        and h.fraud_rate > b.baseline_fraud_rate,
        false
    ) as is_high_risk_window
from hourly_metrics as h
cross join baseline as b
