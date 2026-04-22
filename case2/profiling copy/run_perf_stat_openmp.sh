#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$DIR/.." && pwd)"
SRC="$ROOT_DIR/hilos/hilos.c"
BIN="$DIR/hilos_perf"
OUT_DIR="$DIR/output"

N="${1:-2000}"
THREADS="${2:-8}"
TRIALS="${3:-1}"
SEED="${4:-123456789}"

if ! command -v perf >/dev/null 2>&1; then
  echo "perf no esta disponible. En Ubuntu/Debian: sudo apt install linux-tools-common linux-tools-generic" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

printf "[perf][OpenMP] Compilando %s -> %s\n" "$SRC" "$BIN"
gcc -O0 -g -std=c11 -Wall -Wextra -fopenmp "$SRC" -o "$BIN"

REPORT_FILE="$OUT_DIR/perf_stat_openmp_${N}_t${THREADS}.txt"
RUN_FILE="$OUT_DIR/run_perf_openmp_${N}_t${THREADS}.txt"

printf "[perf][OpenMP] Ejecutando: N=%s THREADS=%s TRIALS=%s SEED=%s\n" "$N" "$THREADS" "$TRIALS" "$SEED"
perf stat -e task-clock,cycles,instructions,cache-references,cache-misses,context-switches,cpu-migrations,page-faults \
  -o "$REPORT_FILE" -- "$BIN" "$N" "$TRIALS" "$THREADS" "$SEED" > "$RUN_FILE"

printf "[perf][OpenMP] Perfil generado:\n"
printf "  - %s\n" "$REPORT_FILE"
printf "  - %s\n" "$RUN_FILE"
