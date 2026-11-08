select 'customer' as model_name, customer_id as entity_id
from {{ ref('mart_customer_risk_profile') }}
where
    risk_level != {{ risk_level('fraud_rate') }}
    or has_known_risk != (labeled_transaction_count > 0)
    or first_transaction_at > last_transaction_at
union all
select 'merchant' as model_name, merchant as entity_id
from {{ ref('mart_merchant_analytics') }}
where
    is_suspicious != ifNull(
        labeled_transaction_count >= {{ var('suspicious_min_labeled_transactions') }}
        and fraud_rate >= {{ var('high_risk_fraud_rate') }},
        false
    )
union all
select
    'hourly' as model_name,
    concat(toString(day_of_week), ':', toString(transaction_hour)) as entity_id
from {{ ref('mart_hourly_fraud_pattern') }}
where
    is_high_risk_window != ifNull(
        labeled_transaction_count >= {{ var('suspicious_min_labeled_transactions') }}
        and fraud_rate > baseline_fraud_rate,
        false
    )
