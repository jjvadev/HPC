#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$DIR/.." && pwd)"
SRC="$ROOT_DIR/hilos/hilos.c"
BIN="$DIR/hilos_massif"
OUT_DIR="$DIR/output"

N="${1:-2000}"
THREADS="${2:-8}"
TRIALS="${3:-1}"
SEED="${4:-123456789}"

if ! command -v valgrind >/dev/null 2>&1; then
  echo "valgrind no esta instalado. Instala con: sudo apt install valgrind" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

printf "[massif][OpenMP] Compilando %s -> %s\n" "$SRC" "$BIN"
gcc -O0 -g -std=c11 -Wall -Wextra -fopenmp "$SRC" -o "$BIN"

MASSIF_RAW="$OUT_DIR/massif_openmp_${N}_t${THREADS}.out"
MASSIF_TXT="$OUT_DIR/massif_openmp_${N}_t${THREADS}.txt"
RUN_TXT="$OUT_DIR/run_massif_openmp_${N}_t${THREADS}.txt"

printf "[massif][OpenMP] Ejecutando: N=%s THREADS=%s TRIALS=%s SEED=%s\n" "$N" "$THREADS" "$TRIALS" "$SEED"
valgrind --tool=massif --massif-out-file="$MASSIF_RAW" \
  "$BIN" "$N" "$TRIALS" "$THREADS" "$SEED" > "$RUN_TXT"

ms_print "$MASSIF_RAW" > "$MASSIF_TXT"

printf "[massif][OpenMP] Perfil generado:\n"
printf "  - %s\n" "$MASSIF_RAW"
printf "  - %s\n" "$MASSIF_TXT"
