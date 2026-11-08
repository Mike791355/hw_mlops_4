select
    'high' as customer_id,
    toDecimal64(10, 2) as amount,
    toNullable(toUInt8(number = 0)) as is_fraud,
    toUInt8(1) as is_labeled,
    toDateTime('2019-01-01 10:00:00', 'UTC') as transaction_time
from numbers(20)
union all
select
    'medium' as customer_id,
    toDecimal64(10, 2) as amount,
    toNullable(toUInt8(number = 0)) as is_fraud,
    toUInt8(1) as is_labeled,
    toDateTime('2019-01-01 10:00:00', 'UTC') as transaction_time
from numbers(100)
union all
select
    'low' as customer_id,
    toDecimal64(10, 2) as amount,
    toNullable(toUInt8(number = 0)) as is_fraud,
    toUInt8(1) as is_labeled,
    toDateTime('2019-01-01 10:00:00', 'UTC') as transaction_time
from numbers(200)
union all
select
    'unknown' as customer_id,
    toDecimal64(10, 2) as amount,
    cast(null, 'Nullable(UInt8)') as is_fraud,
    toUInt8(0) as is_labeled,
    toDateTime('2019-01-01 10:00:00', 'UTC') as transaction_time
