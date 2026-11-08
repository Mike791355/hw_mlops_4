"""Запуск dbt и сохранение результатов."""
import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from load import ClickHouse, ROOT, load

MART_KEYS = {
    "mart_daily_state_metrics": "transaction_date, us_state",
    "mart_fraud_by_category": "category",
    "mart_fraud_by_state": "us_state",
    "mart_customer_risk_profile": "customer_id",
    "mart_hourly_fraud_pattern": "day_of_week, transaction_hour",
    "mart_merchant_analytics": "merchant",
}


def run_step(name, command, out, status):
    print(f"\n=== {name}: {' '.join(command)} ===", flush=True)
    with (out / f"{name}.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command, cwd=ROOT / "dbt", stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, env=os.environ.copy(),
        )
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
        code = process.wait()
    status["steps"].append(dict(step=name, exit_code=code))
    if code:
        raise RuntimeError(f"{name} failed with exit code {code}; see {out / (name + '.log')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", nargs="+", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--skip-load", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    if not args.skip_load and not args.csv:
        parser.error("provide --csv or --skip-load")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    status = dict(started_at=datetime.now(timezone.utc).isoformat(), success=False, steps=[])
    os.environ.setdefault("DBT_PROFILES_DIR", str(ROOT / "dbt"))
    os.environ.setdefault("DBT_SEND_ANONYMOUS_USAGE_STATS", "false")
    try:
        run_step("versions", ["dbt", "--version"], out, status)
        run_step("deps", ["dbt", "deps"], out, status)
        run_step("debug", ["dbt", "debug"], out, status)
        if not args.skip_load:
            summaries = load(args.csv, args.replace)
            (out / "data_profile.json").write_text(json.dumps(summaries, indent=2) + "\n")
        run_step("seed", ["dbt", "seed"], out, status)
        run_step("run", ["dbt", "run"], out, status)
        try:
            run_step("test", ["dbt", "test"], out, status)
        finally:
            test_results = ROOT / "dbt/target/run_results.json"
            if test_results.is_file():
                shutil.copy2(test_results, out / "dbt-test-results.json")
        run_step("docs", ["dbt", "docs", "generate", "--static"], out, status)
        for filename in ("manifest.json", "catalog.json", "static_index.html"):
            shutil.copy2(ROOT / "dbt/target" / filename, out / filename)
        run_step("lint", ["sqlfluff", "lint", "models", "macros", "tests"], out, status)
        ch = ClickHouse()
        schema = os.getenv("DBT_SCHEMA", "analytics")
        from load import identifier
        schema = identifier(schema)
        for mart, keys in MART_KEYS.items():
            text = ch.query(f"SELECT * FROM {schema}.{mart} ORDER BY {keys} FORMAT CSVWithNames")
            (out / f"{mart}.csv").write_text(text, encoding="utf-8")
        status["success"] = True
    finally:
        status["finished_at"] = datetime.now(timezone.utc).isoformat()
        (out / "verification_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(f"\nРезультаты: {out}")


if __name__ == "__main__":
    main()
