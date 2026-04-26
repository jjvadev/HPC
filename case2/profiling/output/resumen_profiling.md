# Resumen de profiling - caso de estudio 2

Fuente de CPU: Instruments Time Profiler.
Fuente de memoria/cache: Instruments CPU Counters con eventos L1D/L1DTLB misses.

## CPU

| Variante | CPU total (s) | CPU matmul (s) | % matmul | Speedup total |
| --- | ---: | ---: | ---: | ---: |
| Secuencial | 73.800 | 73.800 | 100.00% | 1.000x |
| O3 | 30.920 | 30.620 | 99.03% | 2.387x |
| Transpuesta/cache | 47.600 | 47.290 | 99.35% | 1.550x |

## Funciones mas costosas en CPU

| Variante | Funcion | CPU acumulado (s) | Self CPU (s) | % del total | Apariciones |
| --- | --- | ---: | ---: | ---: | ---: |
| Secuencial | `matmul` | 73.800 | 73.800 | 100.00% | 1 |
| Secuencial | `fill_random_matrices` | 0.280 | 0.015 | 0.38% | 1 |
| Secuencial | `rand_i32` | 0.260 | 0.056 | 0.35% | 2 |
| Secuencial | `zero_matrix` | 0.015 | 0.015 | 0.02% | 1 |
| Secuencial | `checksum_matrix` | 0.006 | 0.006 | 0.01% | 1 |
| O3 | `matmul` | 30.620 | 30.620 | 99.03% | 2 |
| O3 | `process_cpu_seconds` | 15.640 | 0.000 | 50.58% | 1 |
| O3 | `zero_matrix` | 14.980 | 0.000 | 48.45% | 1 |
| O3 | `fill_random_matrices` | 0.164 | 0.016 | 0.53% | 2 |
| O3 | `rand_i32` | 0.148 | 0.029 | 0.48% | 2 |
| O3 | `checksum_matrix` | 0.001 | 0.001 | 0.00% | 1 |
| O3 | `wall_seconds_now` | 0.001 | 0.000 | 0.00% | 1 |
| Transpuesta/cache | `matmul` | 47.290 | 47.290 | 99.35% | 1 |
| Transpuesta/cache | `fill_random_matrices` | 0.274 | 0.013 | 0.58% | 1 |
| Transpuesta/cache | `rand_i32` | 0.106 | 0.052 | 0.22% | 2 |
| Transpuesta/cache | `zero_matrix` | 0.016 | 0.016 | 0.03% | 1 |
| Transpuesta/cache | `checksum_matrix` | 0.006 | 0.006 | 0.01% | 1 |

Nota: los tiempos por funcion son inclusivos segun el arbol de llamadas de Time Profiler. Sirven para ubicar las funciones dominantes, no para sumarlos como si fueran partes disjuntas del tiempo total.

## CPU Counters

| Variante | L1D load misses matmul | L1D store misses matmul | L1DTLB misses matmul | Reduccion L1D load | Reduccion L1DTLB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Secuencial | 24502844 | 4859 | 24902122 | 0.00% | 0.00% |
| O3 | 24800801 | 4889 | 24616271 | -1.22% | 1.15% |
| Transpuesta/cache | 864929 | 487 | 1016 | 96.47% | 100.00% |

Interpretacion breve: O3 reduce el tiempo de CPU frente al secuencial, mientras que la version con matriz transpuesta reduce de forma marcada los misses L1D/L1DTLB de `matmul`, lo que confirma mejor localidad de cache.
