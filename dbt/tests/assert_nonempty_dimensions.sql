select transaction_id
from {{ ref('stg_transactions') }}
where
    empty(merchant)
    or empty(category)
    or empty(us_state)
    or empty(source_file)
    or row_number = 0
