#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$DIR/.." && pwd)"
SRC="$ROOT_DIR/hilos/hilos.c"
BIN="$DIR/hilos_timev"
OUT_DIR="$DIR/output"

N="${1:-2000}"
THREADS="${2:-8}"
TRIALS="${3:-1}"
SEED="${4:-123456789}"

if ! command -v /usr/bin/time >/dev/null 2>&1; then
  echo "No se encontro /usr/bin/time en el sistema." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

printf "[time -v][OpenMP] Compilando %s -> %s\n" "$SRC" "$BIN"
gcc -O0 -g -std=c11 -Wall -Wextra -fopenmp "$SRC" -o "$BIN"

RUN_TXT="$OUT_DIR/run_timev_openmp_${N}_t${THREADS}.txt"
TIME_TXT="$OUT_DIR/timev_openmp_${N}_t${THREADS}.txt"

printf "[time -v][OpenMP] Ejecutando: N=%s THREADS=%s TRIALS=%s SEED=%s\n" "$N" "$THREADS" "$TRIALS" "$SEED"
/usr/bin/time -v -o "$TIME_TXT" "$BIN" "$N" "$TRIALS" "$THREADS" "$SEED" > "$RUN_TXT"

printf "[time -v][OpenMP] Perfil generado:\n"
printf "  - %s\n" "$TIME_TXT"
printf "  - %s\n" "$RUN_TXT"
