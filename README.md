# ДЗ 4. dbt и ClickHouse

В проекте есть staging и 6 витрин из задания. На полном наборе из 1 048 575 строк
прошли 125 data tests и 8 unit tests. SQLFluff тоже прошёл.

## Запуск

Нужны Docker с запущенным Engine, Docker Compose и make. Python на компьютере устанавливать  
не нужно. Команды выполняются из папки с Makefile.

Для проверки на приложенном демо из 10 строк:

```bash
make demo
```

Команда загружает CSV, создаёт витрины, запускает тесты и линтер, генерирует
документацию и скриншоты. Результаты будут в `results/demo/`.

Для полного набора положите исходные train.csv и test.csv в `teta-ml-1-2025/`
внутри проекта и выполните:

```bash
make full
```

Большие CSV в комплект не включены. Результаты уже выполненного полного
прогона сохранены в `results/`.

Если полные данные уже есть в ClickHouse проекта, можно выполнить `make existing`.
Повторная загрузка тех же CSV не добавляет дубли. Для замены набора есть
параметр `--replace` у `code/run.py`.

После полного запуска доступны отдельные команды:

```bash
make test        # все dbt-тесты
make unit        # только unit tests
make lint        # SQLFluff
make docs        # документация на localhost:18080 после генерации dbt/target
make down        # остановка контейнеров, данные сохраняются
```

Демо использует другие базы. После `make demo` для отдельных проверок:

```bash
RAW_DATABASE=transactions_demo DBT_SCHEMA=analytics_demo make test
RAW_DATABASE=transactions_demo DBT_SCHEMA=analytics_demo make unit
RAW_DATABASE=transactions_demo DBT_SCHEMA=analytics_demo make lint
```

В results/ находятся:

test.log, dbt-test-results.json  133 успешных теста;

lint.log, versions.log - линтер и версии dbt;

[dbt-dag.png](results/dbt-dag.png) и [dbt-docs.png](results/dbt-docs.png): скриншоты;

mart_*.csv выгрузки всех 6 витрин; 

static_index.html  документация;

verification_status.json, screenshots_status.json - статусы запуска.

В каждой витрине 1 048 575 транзакций и сумма 73 692 902.08.  
Известных меток 786 431, фродов 4 504.

Для просмотра сохранённой документации без ClickHouse:

```bash
python3 -m http.server 18081 --bind 127.0.0.1 --directory results
```

Адрес: `http://localhost:18081/static_index.html`.

## Работа без контейнера dbt

Нужен Python 3.12 или 3.13, запущенный ClickHouse и загруженные raw-данные.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd dbt
export DBT_PROFILES_DIR="$PWD"
export DBT_SEND_ANONYMOUS_USAGE_STATS=false
dbt deps
dbt seed
dbt run
dbt test
dbt docs generate --static
sqlfluff lint models macros tests
```

ClickHouse на хосте доступен по localhost:18124, внутри Docker - clickhouse:8123.  
Настройки подключения задаются через CLICKHOUSE_HOST, CLICKHOUSE_PORT,  
CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, RAW_DATABASE и DBT_SCHEMA.

После установки зависимостей в локальном Git-репозитории можно выполнить
`pre-commit install`. Перед коммитом будет запускаться SQLFluff.

## Версии

Использованы dbt-core 1.10.13 и dbt-clickhouse 1.9.8. Версии подтверждены  
в [versions.log](results/versions.log).  
SQLFluff и dbt-templater 4.0.4, pre-commit 4.3.0, ClickHouse 25.8.1.5101.  
Пакеты: dbt_utils 1.3.0, dbt_date 0.10.1, dbt_expectations 0.10.10.

1. `mart_daily_state_metrics`: дневные метрики по штатам.
2. `mart_fraud_by_category`: анализ фрода по категориям.
3. `mart_fraud_by_state`: анализ фрода по штатам.
4. `mart_customer_risk_profile`: история операций и риск клиентов.
5. `mart_hourly_fraud_pattern`: фрод по дням недели и часам.
6. `mart_merchant_analytics`: аналитика и подозрительность мерчантов.

Базовые тесты: not_null, unique, accepted_values и relationships.
Также есть проверки диапазонов из dbt_expectations и уникальности составных
ключей всех 6 витрин из dbt_utils.

В [dbt/tests/](dbt/tests/) находятся 7 singular tests:
`assert_no_negative_amounts`, `assert_nonempty_dimensions`,
`assert_source_preserved`, `assert_marts_reconcile`, `assert_fraud_rate_bounds`,
`assert_risk_flags`, `assert_daily_distribution`.

8 native unit tests находятся в [unit_tests.yml](dbt/models/unit_tests.yml).
Они проверяют границы сегментов сумм, NULL в метках фрода, дневные метрики и P95,
пороги риска клиентов, уникальных клиентов и мерчантов, минимальную выборку
мерчанта, сравнение часового риска с общим и часы без известных меток.

Результат полного запуска: PASS=133, WARN=0, ERROR=0, SKIP=0.
Подтверждение: [test.log](results/test.log).
Скриншот DAG: [dbt-dag.png](results/dbt-dag.png).

Конфигурация SQLFluff: [dbt/.sqlfluff](dbt/.sqlfluff).
Конфигурация pre-commit: [.pre-commit-config.yaml](.pre-commit-config.yaml).
Команды запуска: [Makefile](Makefile).
