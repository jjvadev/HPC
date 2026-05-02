#!/usr/bin/env bash

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

BIN_SERIAL="$DIR/traffic_serial"

OUT="$DIR/output/sizes_serial.txt"

echo "version,hilos,N,pasos,densidad,densidad_real,tiempo_s,mceldas_s,velocidad,trial" > "$OUT"

# Compilar traffic_serial.c
echo "Compilando traffic_serial.c..."
gcc -o "$BIN_SERIAL" "$DIR/traffic_serial.c"
echo "✓ Compilado traffic_serial.c"


TRIALS=5
PASOS=1000
DENSIDAD=0.5

SIZES=(100000 1000000 5000000 10000000 50000000)
echo "==== Benchmark: variando N ===="

for trial in $(seq 1 $TRIALS); do
    for N in "${SIZES[@]}"; do
        echo "Trial $trial/$TRIALS - Serial N=$N"
        "$BIN_SERIAL" $N $PASOS $DENSIDAD \
            | grep "^serial," \
            | sed "s/$/,$trial/" >> "$OUT"
    done
done

echo "✓ Tamaños listos"