select
    transaction_date,
    us_state,
    count() as transaction_count,
    sum(amount) as total_amount,
    avg(amount) as avg_amount,
    quantileExact(0.95) (amount) as p95_amount,
    countIf(amount_bucket = 'LARGE') as large_transaction_count,
    100.0 * countIf(amount_bucket = 'LARGE') / count() as large_transaction_share
from {{ ref('stg_transactions') }}
group by transaction_date, us_state
