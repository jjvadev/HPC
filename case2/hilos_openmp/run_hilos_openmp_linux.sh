#!/usr/bin/env bash

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/hilos_openmp.c"
BIN="$DIR/hilos_openmp"
OUT_DIR="$DIR/output"
OUT="$OUT_DIR/output_hilos_openmp.txt"

mkdir -p "$OUT_DIR"

# Compilar sin optimizaciones (OpenMP)
printf "Compilando %s -> %s\n" "$SRC" "$BIN"
gcc -O0 -std=c11 -Wall -Wextra -fopenmp "$SRC" -o "$BIN"
printf "Compilacion hecha\n"

# Encabezado
printf "N trial threads wall_s user_s kernel_s cpu_total_s checksum seed\n" > "$OUT"

printf "Ejecutando benchmarks hilos (OpenMP)...\n"

# 10 rondas para cada tamano y numero de hilos (trials=1 por corrida)
for round in {1..10}; do
    printf "  Ronda %d/10...\n" "$round"
    for size in 400 600 800 1000 2000 4000 5500 6000 8000; do
        for threads in 2 4 8 16; do
            "$BIN" "$size" 1 "$threads" 123456789 >> "$OUT"
        done
    done
done

printf "Benchmarks completados\n"
printf "Resultados guardados en: %s\n" "$OUT"
