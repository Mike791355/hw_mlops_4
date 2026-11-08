with normalized as (
    select
        toString(source_file) as source_file,
        toUInt64(row_number) as row_number,
        toDateTime(transaction_time, 'UTC') as transaction_time,
        trimBoth(toString(merch)) as merchant,
        lowerUTF8(trimBoth(toString(cat_id))) as category,
        toDecimal64(amount, 2) as amount,
        lowerUTF8(trimBoth(toString(name_1))) as first_name,
        lowerUTF8(trimBoth(toString(name_2))) as last_name,
        upperUTF8(trimBoth(toString(gender))) as gender,
        upperUTF8(trimBoth(toString(us_state))) as us_state,
        toFloat64(lat) as latitude,
        toFloat64(lon) as longitude,
        toFloat64(merchant_lat) as merchant_latitude,
        toFloat64(merchant_lon) as merchant_longitude,
        cast(target, 'Nullable(UInt8)') as is_fraud
    from {{ source('raw', 'transactions') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['source_file', 'row_number']) }} as transaction_id,
    {{ dbt_utils.generate_surrogate_key([
        'first_name', 'last_name', 'gender', 'latitude', 'longitude'
    ]) }} as customer_id,
    source_file,
    row_number,
    transaction_time,
    toDate(transaction_time) as transaction_date,
    {{ dbt_date.day_of_week('transaction_time', isoweek=true) }} as day_of_week,
    toHour(transaction_time) as transaction_hour,
    merchant,
    category,
    amount,
    {{ amount_bucket('amount') }} as amount_bucket,
    gender,
    us_state,
    latitude,
    longitude,
    merchant_latitude,
    merchant_longitude,
    is_fraud,
    isNotNull(is_fraud) as is_labeled
from normalized
