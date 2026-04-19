#!/usr/bin/env bash

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/secuencial.c"
BIN="$DIR/secuencial"
OUT_DIR="$DIR/output"
OUT="$OUT_DIR/output_secuencial.txt"

mkdir -p "$OUT_DIR"

# Compilar sin optimizaciones
printf "Compilando %s -> %s\n" "$SRC" "$BIN"
gcc -O0 -std=c11 -Wall -Wextra "$SRC" -o "$BIN"
printf "Compilacion hecha\n"

# Encabezado
printf "N trial wall_s user_s kernel_s cpu_total_s checksum seed\n" > "$OUT"

printf "Ejecutando benchmarks secuencial...\n"

# 10 rondas para cada tamano (trials=1 por corrida)
for round in {1..10}; do
    printf "  Ronda %d/10...\n" "$round"
    for size in 400 600 800 1000 2000 4000 5500 6000 8000; do
        "$BIN" "$size" 1 123456789 >> "$OUT"
    done
done

printf "Benchmarks completados\n"
printf "Resultados guardados en: %s\n" "$OUT"
