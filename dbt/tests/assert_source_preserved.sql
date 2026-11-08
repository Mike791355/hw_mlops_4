with raw_metrics as (
    select
        count() as row_count,
        sum(toDecimal64(amount, 2)) as total_amount,
        countIf(target = 1) as fraud_count,
        countIf(isNotNull(target)) as labeled_count
    from {{ source('raw', 'transactions') }}
),

staging_metrics as (
    select
        count() as row_count,
        sum(amount) as total_amount,
        countIf(is_fraud = 1) as fraud_count,
        countIf(is_labeled) as labeled_count
    from {{ ref('stg_transactions') }}
)

select r.row_count as raw_rows, s.row_count as staging_rows
from raw_metrics as r
cross join staging_metrics as s
where
    r.row_count = 0
    or r.row_count != s.row_count
    or r.total_amount != s.total_amount
    or r.fraud_count != s.fraud_count
    or r.labeled_count != s.labeled_count
