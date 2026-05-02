#!/usr/bin/env bash

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

BIN_SERIAL="$DIR/traffic_serial"
if [ ! -f "$BIN_SERIAL" ]; then
    echo "Compilando traffic_serial.c..."
    gcc -o "$BIN_SERIAL" "$DIR/traffic_serial.c"
    echo "✓ Compilado traffic_serial.c"
else
    echo "✓ traffic_serial.c ya compilado"
fi

OUT="$DIR/output/density.txt"

echo "version,hilos,N,pasos,densidad,densidad_real,tiempo_s,mceldas_s,velocidad,trial" > "$OUT"



TRIALS=5
N=10000000
PASOS=1000

DENSITIES=(0.1 0.3 0.5 0.7 0.9 1.0)

echo "==== Benchmark: variando densidad ===="

for trial in $(seq 1 $TRIALS); do
    for d in "${DENSITIES[@]}"; do
        "$BIN_SERIAL" $N $PASOS $d \
            | grep "^serial," \
            | sed "s/$/,$trial/" >> "$OUT"
    done
done

echo "✓ Densidades listas"