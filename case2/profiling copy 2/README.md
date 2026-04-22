# Profiling - Caso 2 (OpenMP)

Este directorio contiene un flujo minimo y reproducible de perfilado para CPU y memoria.

## Scripts disponibles

- `run_gprof_openmp.sh`: perfilado con `gprof`.
- `run_gprof_secuencial.sh`: `gprof` para baseline secuencial.
- `run_gprof_memoria.sh`: `gprof` para variante optimizada de memoria.
- `run_perf_stat_openmp.sh`: contadores de CPU/cache con `perf stat`.
- `run_massif_openmp.sh`: perfilado de memoria con `valgrind --tool=massif`.
- `run_massif_secuencial.sh`: memoria para baseline secuencial con Massif.
- `run_massif_memoria.sh`: memoria para variante optimizada con Massif.
- `run_timev_openmp.sh`: alternativa sin privilegios con `/usr/bin/time -v`.

Todos los scripts reciben los mismos argumentos opcionales:

```bash
./script.sh [N] [threads] [trials] [seed]
```

Valores por defecto: `N=2000`, `threads=8`, `trials=1`, `seed=123456789`.

## 1) CPU profiling con gprof (minimo requerido)

```bash
cd case2/profiling
./run_gprof_openmp.sh 2000 8 1 123456789
```

Tambien puedes perfilar las otras variantes para comparacion directa:

```bash
./run_gprof_secuencial.sh 2000 1 123456789
./run_gprof_memoria.sh 2000 1 123456789
```

Salida generada en `output/`:

- `gmon_openmp_*`: datos crudos de gprof.
- `gprof_openmp_*.txt`: reporte legible.
- `run_gprof_openmp_*.txt`: salida de ejecucion del programa.

Nota importante: en programas OpenMP, `gprof` puede atribuir gran parte del tiempo a `main` y no desglosar bien los hilos. Por eso se recomienda complementar con `perf stat`.

## 2) CPU/cache profiling con perf stat (recomendado)

```bash
cd case2/profiling
./run_perf_stat_openmp.sh 2000 8 1 123456789
```

Si aparece un error de permisos (`perf_event_paranoid` alto), usa temporalmente:

```bash
./run_timev_openmp.sh 2000 8 1 123456789
```

Y si tienes permisos de administrador, habilita `perf` en esta sesion:

```bash
sudo sysctl -w kernel.perf_event_paranoid=1
```

Salida generada en `output/`:

- `perf_stat_openmp_*.txt`: contadores (cycles, instructions, cache-misses, etc.).
- `run_perf_openmp_*.txt`: salida de ejecucion del programa.

Indicadores a reportar:

- `task-clock`
- `cycles`
- `instructions`
- `cache-misses`
- `cache-misses / cache-references` (si aparece)

Con `time -v` puedes reportar:

- `User time (seconds)`
- `System time (seconds)`
- `Percent of CPU this job got`
- `Maximum resident set size (kbytes)`

## 3) Memoria con massif (requerido por actividad)

Primero instala valgrind si hace falta:

```bash
sudo apt update
sudo apt install -y valgrind
```

Luego:

```bash
cd case2/profiling
./run_massif_openmp.sh 2000 8 1 123456789
./run_massif_secuencial.sh 2000 1 123456789
./run_massif_memoria.sh 2000 1 123456789
```

Salida en `output/`:

- `massif_openmp_*.out`: datos crudos.
- `massif_openmp_*.txt`: reporte legible (`ms_print`).
- `run_massif_openmp_*.txt`: salida de ejecucion del programa.

Indicadores a reportar:

- Pico de memoria (peak heap).
- Evolucion de memoria por snapshots.
- Comparacion entre tamanos de matriz y numero de hilos.

Salida esperada por script:

- `massif_*.out`: datos crudos de Massif.
- `massif_*.txt`: resumen legible con `ms_print`.
- `run_massif_*.txt`: salida normal del programa.

## Flujo sugerido para informe

1. Ejecutar `gprof` para cumplir minimo solicitado.
2. Ejecutar `perf stat` para evidenciar comportamiento de CPU/cache.
3. Ejecutar `massif` para memoria.
4. Repetir el mismo protocolo en la segunda maquina (si disponible).
5. Comparar resultados por tamano de matriz y por hilos.
