#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$DIR/.." && pwd)"
SRC="$ROOT_DIR/memoria/NoHilosCache.c"
BIN="$DIR/memoria_massif"
OUT_DIR="$DIR/output"

N="${1:-2000}"
TRIALS="${2:-1}"
SEED="${3:-123456789}"

if ! command -v valgrind >/dev/null 2>&1; then
  echo "valgrind no esta instalado. Instala con: sudo apt install valgrind" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

printf "[massif][Memoria] Compilando %s -> %s\n" "$SRC" "$BIN"
gcc -O0 -g -std=c11 -Wall -Wextra "$SRC" -o "$BIN"

MASSIF_RAW="$OUT_DIR/massif_memoria_${N}.out"
MASSIF_TXT="$OUT_DIR/massif_memoria_${N}.txt"
RUN_TXT="$OUT_DIR/run_massif_memoria_${N}.txt"

printf "[massif][Memoria] Ejecutando: N=%s TRIALS=%s SEED=%s\n" "$N" "$TRIALS" "$SEED"
valgrind --tool=massif --massif-out-file="$MASSIF_RAW" \
  "$BIN" "$N" "$TRIALS" "$SEED" > "$RUN_TXT"

ms_print "$MASSIF_RAW" > "$MASSIF_TXT"

printf "[massif][Memoria] Perfil generado:\n"
printf "  - %s\n" "$MASSIF_RAW"
printf "  - %s\n" "$MASSIF_TXT"
