#!/usr/bin/env bash

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

BIN_OMP="$DIR/traffic_omp"
if [ ! -f "$BIN_OMP" ]; then
    echo "Compilando traffic_omp.c..."
    gcc -fopenmp -o "$BIN_OMP" "$DIR/traffic_omp.c"
    echo "✓ Compilado traffic_omp.c"
else
    echo "✓ traffic_omp.c ya compilado"
fi

OUT="$DIR/output/sizes_omp.txt"

echo "version,hilos,N,pasos,densidad,densidad_real,tiempo_s,mceldas_s,velocidad,trial" > "$OUT"


TRIALS=5
PASOS=1000
DENSIDAD=0.5

SIZES=(100000 1000000 5000000 10000000 50000000)
THREADS=(2 4 8 16)
echo "==== Benchmark: variando N ===="

for trial in $(seq 1 $TRIALS); do
    for N in "${SIZES[@]}"; do
        for threads in "${THREADS[@]}"; do
            echo "Trial $trial/$TRIALS - OpenMP hilos=$threads N=$N"
            "$BIN_OMP" $N $PASOS $DENSIDAD $threads \
                | grep "^openmp," \
                | sed "s/$/,$trial/" >> "$OUT"
        done
    done
done

echo "✓ Tamaños listos"