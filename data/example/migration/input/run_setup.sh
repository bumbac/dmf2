#!/usr/bin/env bash
# Creates objects, seeds static rows, loads CSV, refreshes materialized view.
# Usage:
#   DATABASE_URL=postgres://... ./run_setup.sh
# or:
#   PGHOST=... PGUSER=... PGDATABASE=... ./run_setup.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV="${ROOT}/patients_import.csv"

if [[ ! -f "$CSV" ]]; then
  echo "Missing CSV: $CSV" >&2
  exit 1
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  echo "Running psql with DATABASE_URL and CSV=${CSV}"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -v "abs_csv=${CSV}" -f "${ROOT}/setup.sql"
else
  echo "Running psql (default connection) with CSV=${CSV}"
  psql -v ON_ERROR_STOP=1 -v "abs_csv=${CSV}" -f "${ROOT}/setup.sql"
fi
