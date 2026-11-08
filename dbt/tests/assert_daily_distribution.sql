select transaction_date, us_state
from {{ ref('mart_daily_state_metrics') }}
where
    large_transaction_count > transaction_count
    or avg_amount < 0
    or p95_amount < 0
    or abs(large_transaction_share - 100.0 * large_transaction_count / transaction_count) > 0.000001
