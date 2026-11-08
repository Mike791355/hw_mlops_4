select
    us_state,
    count() as transaction_count,
    countIf(is_labeled) as labeled_transaction_count,
    countIf(is_fraud = 1) as fraud_count,
    {{ fraud_rate('countIf(is_fraud = 1)', 'countIf(is_labeled)') }} as fraud_rate,
    uniqExact(customer_id) as unique_customers,
    uniqExact(merchant) as unique_merchants,
    sum(amount) as total_amount,
    sumIf(amount, is_fraud = 1) as fraud_amount
from {{ ref('stg_transactions') }}
group by us_state
