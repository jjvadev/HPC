#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
EXE="$DIR/mul.exe"
OUT="$DIR/times2.txt"

if [ ! -f "$EXE" ]; then
  echo "No se encontro: $EXE" >&2
  exit 1
fi

if command -v wine >/dev/null 2>&1; then
  RUNNER="wine"
elif command -v wine64 >/dev/null 2>&1; then
  RUNNER="wine64"
else
  echo "No se encontro Wine (wine/wine64). Es necesario para ejecutar mul.exe en macOS." >&2
  exit 1
fi

# Encabezado
echo "round N threads trial wall_s user_s kernel_s cpu_total_s checksum seed" > "$OUT"

# Lista de tamaños (ajústala a lo que necesitas)
NS=(400 2000 3000 4000)

# 10 rondas (ronda afuera, N adentro)
for R in $(seq 1 10); do
  for N in "${NS[@]}"; do
    "$RUNNER" "$EXE" "$N" 1 1 123456789 >> "$OUT"
  done
done

echo "Listo: $OUT"
