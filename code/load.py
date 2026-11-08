"""Загрузка CSV в ClickHouse."""
import argparse
import csv
import hashlib
import json
import math
import os
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "transaction_time", "merch", "cat_id", "amount", "name_1", "name_2", "gender",
    "street", "one_city", "us_state", "post_code", "lat", "lon", "population_city",
    "jobs", "merchant_lat", "merchant_lon",
}
COORDINATES = {"lat": 90, "lon": 180, "merchant_lat": 90, "merchant_lon": 180}


def identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value):
        raise ValueError(f"Invalid SQL identifier: {value!r}")
    return value


class ClickHouse:
    def __init__(self):
        host = os.getenv("CLICKHOUSE_HOST", "localhost")
        port = os.getenv("CLICKHOUSE_PORT", "18124")
        self.url = os.getenv("CLICKHOUSE_URL", f"http://{host}:{port}")
        self.database = identifier(os.getenv("RAW_DATABASE", "transactions_db"))

    def query(self, sql, data=b""):
        request = Request(self.url, data=sql.encode() + b"\n" + data, headers={
            "X-ClickHouse-User": os.getenv("CLICKHOUSE_USER", "homework"),
            "X-ClickHouse-Key": os.getenv("CLICKHOUSE_PASSWORD", "homework"),
        })
        try:
            with urlopen(request, timeout=300) as response:
                return response.read().decode()
        except HTTPError as error:
            raise RuntimeError(error.read().decode()) from error


def validate_paths(paths):
    paths = [Path(path) for path in paths]
    if not paths or len({p.name for p in paths}) != len(paths):
        raise ValueError("Provide CSV files with distinct basenames")
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    return paths


def iter_transactions(path):
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError(f"{path}: missing columns {sorted(REQUIRED - set(reader.fieldnames or []))}")
        for number, row in enumerate(reader, start=1):
            try:
                if None in row or any(row.get(field) in (None, "") for field in REQUIRED):
                    raise ValueError("missing value or invalid CSV width")
                amount = Decimal(row["amount"])
                if not amount.is_finite() or not 0 <= amount < Decimal("10000000000"):
                    raise ValueError("amount outside Decimal(12,2) range")
                if amount != amount.quantize(Decimal("0.01")):
                    raise ValueError("amount has more than two decimal places")
                timestamp = datetime.fromisoformat(row["transaction_time"])
                if timestamp.tzinfo is not None or timestamp.microsecond:
                    raise ValueError("expected timestamp without timezone or microseconds")
                if not datetime(1970, 1, 1) <= timestamp <= datetime(2106, 2, 7, 6, 28, 15):
                    raise ValueError("timestamp outside ClickHouse DateTime range")
                target = row.get("target", "")
                if target not in ("", "0", "1"):
                    raise ValueError("target must be 0, 1, or empty")
                if row["gender"].strip().upper() not in ("F", "M"):
                    raise ValueError("invalid gender")
                state = row["us_state"].strip().upper()
                if not re.fullmatch(r"[A-Z]{2}", state):
                    raise ValueError("invalid state code")
                population = int(row["population_city"])
                if not 0 <= population < 2**32:
                    raise ValueError("population outside UInt32 range")
                result = {field: row[field] for field in REQUIRED}
                result.update(
                    source_file=path.name, row_number=number,
                    transaction_time=timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    amount=format(amount, ".2f"), population_city=population,
                    target=int(target) if target else None,
                )
                for field, bound in COORDINATES.items():
                    value = float(row[field])
                    if not math.isfinite(value) or not -bound <= value <= bound:
                        raise ValueError(f"invalid {field}")
                    result[field] = value
                yield result
            except (ValueError, TypeError, InvalidOperation) as error:
                raise ValueError(f"{path}:{number}: {error}") from error


def inspect_files(paths):
    paths = validate_paths(paths)
    summaries = []
    for path in paths:
        count = labeled = fraud = 0
        total = Decimal(0)
        states, categories = Counter(), Counter()
        first = last = None
        for row in iter_transactions(path):
            count += 1
            labeled += row["target"] is not None
            fraud += row["target"] == 1
            total += Decimal(row["amount"])
            states[row["us_state"].strip().upper()] += 1
            categories[row["cat_id"].strip().lower()] += 1
            timestamp = row["transaction_time"]
            first = min(first, timestamp) if first else timestamp
            last = max(last, timestamp) if last else timestamp
        if count == 0:
            raise ValueError(f"{path}: empty dataset")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        summaries.append(dict(
            file=path.name, sha256=digest.hexdigest(), rows=count,
            labeled_rows=labeled, fraud_rows=fraud, total_amount=str(total),
            first_transaction_at=first, last_transaction_at=last,
            states=dict(sorted(states.items())), categories=dict(sorted(categories.items())),
        ))
    return summaries


def load(paths, replace=False):
    paths = validate_paths(paths)
    summaries = inspect_files(paths)
    fingerprint = hashlib.sha256(json.dumps(summaries, sort_keys=True).encode()).hexdigest()
    expected = sum(item["rows"] for item in summaries)
    ch = ClickHouse()
    db = ch.database
    ch.query(f"CREATE DATABASE IF NOT EXISTS {db}")
    ch.query((ROOT / "docker/table.sql").read_text().format(database=db))
    current = int(ch.query(f"SELECT count() FROM {db}.transactions"))
    comment = ch.query(
        f"SELECT comment FROM system.tables WHERE database='{db}' AND name='transactions' FORMAT TabSeparatedRaw"
    ).strip()
    if current and not replace:
        if current == expected and comment == fingerprint:
            print(f"Raw already loaded: {current:,} rows, SHA-256 matches", flush=True)
            return summaries
        raise RuntimeError("Raw is not empty or load was interrupted; use --replace explicitly to reload")
    if replace:
        ch.query(f"TRUNCATE TABLE {db}.transactions")
    ch.query(f"ALTER TABLE {db}.transactions MODIFY COMMENT '{fingerprint}'")
    batch, sent = [], 0
    for path in paths:
        for row in iter_transactions(path):
            batch.append(json.dumps(row, ensure_ascii=False, allow_nan=False).encode())
            if len(batch) == 10000:
                ch.query(f"INSERT INTO {db}.transactions FORMAT JSONEachRow", b"\n".join(batch))
                sent += len(batch)
                batch.clear()
                if sent % 100000 == 0:
                    print(f"Raw: {sent:,}/{expected:,}", flush=True)
    if batch:
        ch.query(f"INSERT INTO {db}.transactions FORMAT JSONEachRow", b"\n".join(batch))
    actual = int(ch.query(f"SELECT count() FROM {db}.transactions"))
    if actual != expected:
        raise RuntimeError(f"Expected {expected} rows, got {actual}")
    print(f"Raw: {actual:,} rows verified", flush=True)
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", nargs="+", required=True, type=Path)
    parser.add_argument("--replace", action="store_true", help="Explicitly replace existing raw data")
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = inspect_files(args.csv) if args.inspect_only else load(args.csv, args.replace)
    report = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
