#!/bin/sh
set -eu
cd "$(dirname "$0")/../dbt"
exec sqlfluff lint models macros tests
