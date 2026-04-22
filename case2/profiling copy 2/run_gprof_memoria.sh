#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$DIR/.." && pwd)"
SRC="$ROOT_DIR/memoria/NoHilosCache.c"
BIN="$DIR/memoria_gprof"
OUT_DIR="$DIR/output"

N="${1:-3000}"
TRIALS="${2:-1}"
SEED="${3:-123456789}"

mkdir -p "$OUT_DIR"

printf "[gprof][Memoria] Compilando %s -> %s\n" "$SRC" "$BIN"
gcc -O0 -g -pg -std=c11 -Wall -Wextra "$SRC" -o "$BIN"

printf "[gprof][Memoria] Ejecutando: N=%s TRIALS=%s SEED=%s\n" "$N" "$TRIALS" "$SEED"
(
  cd "$OUT_DIR"
  "$BIN" "$N" "$TRIALS" "$SEED" > "run_gprof_memoria_${N}.txt"
)

if [[ ! -f "$OUT_DIR/gmon.out" ]]; then
  echo "No se genero gmon.out. Verifica si la ejecucion finalizo correctamente." >&2
  exit 1
fi

GMON_FILE="$OUT_DIR/gmon_memoria_${N}.out"
REPORT_FILE="$OUT_DIR/gprof_memoria_${N}.txt"

mv "$OUT_DIR/gmon.out" "$GMON_FILE"
gprof "$BIN" "$GMON_FILE" > "$REPORT_FILE"

printf "[gprof][Memoria] Perfil generado:\n"
printf "  - %s\n" "$GMON_FILE"
printf "  - %s\n" "$REPORT_FILE"
