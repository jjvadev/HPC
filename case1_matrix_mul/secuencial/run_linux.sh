#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/linux_mod.c"
BIN="$DIR/secuencial_o3"
OUT="$DIR/times_secuencial_o3.txt"

if [ ! -f "$SRC" ]; then
  echo "No se encontro el codigo fuente: $SRC" >&2
  exit 1
fi

# Compila solo si hace falta (o si linux_mod.c es mas nuevo que el binario).
if [ ! -x "$BIN" ] || [ "$SRC" -nt "$BIN" ]; then
  echo "Compilando $SRC -> $BIN"
  cc -O2 -std=c11 "$SRC" -o "$BIN"
fi

# Encabezado opcional para identificar columnas del programa.
echo "N threads trial wall_s user_s kernel_s cpu_total_s checksum seed" > "$OUT"

for j in {1..10}; do
  for i in  400 600 800 1000 2000 4000 5500 6000 8000; do
    "$BIN" "$i" 1 1 123456789 >> "$OUT"
  done
done

echo "Listo: $OUT"
