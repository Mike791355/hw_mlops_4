SHELL := /bin/sh
COMPOSE := docker compose
TOOLS := $(COMPOSE) run --rm dbt
CSV ?= /workspace/teta-ml-1-2025/train.csv /workspace/teta-ml-1-2025/test.csv

.PHONY: help image up full demo existing inspect deps seed run test unit lint fix docs screenshot down
help:
	@echo 'make full       Запуск на полных CSV'
	@echo 'make demo       Запуск на демо из 10 строк'
	@echo 'make existing   Запуск с уже загруженными данными'
	@echo 'make inspect    Проверка CSV без Docker'
	@echo 'make docs       Документация: http://localhost:18080'
	@echo 'make down       Остановить контейнеры'
image:
	$(COMPOSE) build dbt
up:
	$(COMPOSE) up -d --wait clickhouse
full: image up
	$(TOOLS) python /workspace/code/run.py --csv $(CSV)
	$(MAKE) screenshot
demo: image up
	$(COMPOSE) run --rm -e RAW_DATABASE=transactions_demo -e DBT_SCHEMA=analytics_demo dbt python /workspace/code/run.py --csv /workspace/data/demo.csv --out /workspace/results/demo
	$(COMPOSE) run --build --rm screenshots python code/screenshots.py --out /workspace/results/demo
existing: image up
	$(TOOLS) python /workspace/code/run.py --skip-load
	$(MAKE) screenshot
inspect:
	python3 code/load.py --inspect-only --csv teta-ml-1-2025/train.csv teta-ml-1-2025/test.csv --report results/data_profile.json
deps: image up
	$(TOOLS) dbt deps
seed:
	$(TOOLS) dbt seed
run:
	$(TOOLS) dbt run
test:
	$(TOOLS) dbt test
unit:
	$(TOOLS) dbt test --select test_type:unit
lint:
	$(TOOLS) sh /workspace/code/lint.sh
fix:
	$(TOOLS) sqlfluff fix models macros tests
docs:
	$(COMPOSE) --profile docs up docs
screenshot:
	$(COMPOSE) run --build --rm screenshots
down:
	$(COMPOSE) down
