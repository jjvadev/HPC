#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/procesos.c"
BIN="$DIR/procesos"
OUT="$DIR/output/output_procesos_8-16.txt"

# Compilar
echo "Compilando $SRC -> $BIN"
gcc -std=c11 "$SRC" -o "$BIN"
echo "Compilacion hecha"

# Asegurar carpeta de salida
mkdir -p "$(dirname "$OUT")"

# Encabezado
echo "N procesos trial wall_s user_s kernel_s cpu_total_s checksum seed" > "$OUT"

echo "Ejecutando benchmarks..."

# 10 rondas para cada tamaño y número de procesos
for round in {1..10}; do
    echo "  Ronda $round/10..."
    for size in 400 600 800 1000 2000 4000 5500 6000 8000; do
        for procesos in 8 16; do
            "$BIN" "$size" "$procesos" 1 123456789 >> "$OUT"
        done
    done
done

echo "✓ Benchmarks completados"

echo ""
echo "Resultados guardados en: $OUT"
echo ""
