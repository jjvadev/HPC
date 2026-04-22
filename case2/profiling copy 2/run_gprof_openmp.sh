#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$DIR/.." && pwd)"
SRC="$ROOT_DIR/hilos/hilos.c"
BIN="$DIR/hilos_gprof"
OUT_DIR="$DIR/output"

N="${1:-3000}"
THREADS="${2:-8}"
TRIALS="${3:-1}"
SEED="${4:-123456789}"

mkdir -p "$OUT_DIR"

printf "[gprof][OpenMP] Compilando %s -> %s\n" "$SRC" "$BIN"
gcc -O0 -g -pg -std=c11 -Wall -Wextra -fopenmp "$SRC" -o "$BIN"

printf "[gprof][OpenMP] Ejecutando: N=%s THREADS=%s TRIALS=%s SEED=%s\n" "$N" "$THREADS" "$TRIALS" "$SEED"
(
  cd "$OUT_DIR"
  "$BIN" "$N" "$TRIALS" "$THREADS" "$SEED" > "run_gprof_openmp_${N}_t${THREADS}.txt"
)

if [[ ! -f "$OUT_DIR/gmon.out" ]]; then
  echo "No se genero gmon.out. Verifica si la ejecucion finalizo correctamente." >&2
  exit 1
fi

GMON_FILE="$OUT_DIR/gmon_openmp_${N}_t${THREADS}.out"
REPORT_FILE="$OUT_DIR/gprof_openmp_${N}_t${THREADS}.txt"

mv "$OUT_DIR/gmon.out" "$GMON_FILE"
gprof "$BIN" "$GMON_FILE" > "$REPORT_FILE"

printf "[gprof][OpenMP] Perfil generado:\n"
printf "  - %s\n" "$GMON_FILE"
printf "  - %s\n" "$REPORT_FILE"
