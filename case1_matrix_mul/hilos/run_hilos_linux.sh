#!/usr/bin/env bash

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/hilos.c"
BIN="$DIR/hilos"
OUT="$DIR/output/output_hilos.txt"



#Compilar

echo "Compilando $SRC -> $BIN"
gcc -pthread "$SRC" -o "$BIN"
echo "Compilacion hecha"


#Ejecutar benchmarks

# Encabezado
echo "N threads trial wall_s user_s kernel_s cpu_total_s checksum seed" > "$OUT"

echo "Ejecutando benchmarks..."

# 10 rondas para cada tamaño y número de hilos
for round in {1..10}; do
    echo "  Ronda $round/10..."
    for size in 400 800 1000 2000 4000 6000; do
        for threads in 2 4 8 16 32; do
            "$BIN" "$size" "$threads" 1 123456789 >> "$OUT"
        done
    done
done

echo "✓ Benchmarks completados"

echo ""
echo "Resultados guardados en: $OUT"
echo ""