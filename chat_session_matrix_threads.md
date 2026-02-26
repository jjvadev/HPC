## Guía estructurada (para compartir) sobre `matmul` y `pthreads` en tu proyecto HPC

### 1. Contexto del proyecto
- Archivo analizado: `/Users/nico/University/HPC/case1_matrix_mul/secuencial/linux.c`
- Estructura actual:
  - `/Users/nico/University/HPC/case1_matrix_mul/secuencial/`
  - `/Users/nico/University/HPC/case1_matrix_mul/hilos/`

---

### 2. ¿Qué forma de matriz es más escalable para HPC?
#### Recomendación
Usar la forma actual del proyecto:
- `int32_t *A, *B, *C` (memoria contigua)
- indexado manual: `A[i*N + j]`

#### No recomendado para HPC (como base principal)
- `int32_t **` con `malloc` por fila

#### Motivos
- Mejor localidad de memoria (cache)
- Menos fragmentación
- Menos llamadas a `malloc`
- Mejor para vectorización del compilador
- Más conveniente para repartir trabajo en `pthreads`

---

### 3. ¿El `main` actual está usando OpenMP?
#### Sí, pero solo si compilas con OpenMP
En `/Users/nico/University/HPC/case1_matrix_mul/secuencial/linux.c`:
- `main()` llama a `configure_threads(threads)`
- `matmul()` tiene `#pragma omp parallel for`

#### Comportamiento
- Si compilas con OpenMP (`-fopenmp`): usa OpenMP
- Si no compilas con OpenMP: corre secuencialmente

---

### 4. Explicación didáctica de `matmul`
La función `matmul` calcula:

`C[i][j] = sum_{k=0..N-1} A[i][k] * B[k][j]`

#### Significado de los bucles
- `i`: fila de `C`
- `j`: columna de `C`
- `k`: suma interna (producto punto)

#### Cómo se indexa en memoria lineal
Para una matriz `N x N` guardada en `int32_t *`:

- `(i, j)` -> `i*N + j`

Ejemplos:
- `A[i][k]` -> `A[i*N + k]`
- `B[k][j]` -> `B[k*N + j]`
- `C[i][j]` -> `C[i*N + j]`

---

### 5. Ejemplo visual de multiplicación 2x2 (sin hilos)
#### Matrices
```text
A = [ [1, 2],
      [3, 4] ]

B = [ [5, 6],
      [7, 8] ]
```

#### Resultado
```text
C = [ [19, 22],
      [43, 50] ]
```

#### Cálculo celda por celda
- `C[0][0] = 1*5 + 2*7 = 19`
- `C[0][1] = 1*6 + 2*8 = 22`
- `C[1][0] = 3*5 + 4*7 = 43`
- `C[1][1] = 3*6 + 4*8 = 50`

#### En memoria lineal (`N=2`)
```text
A = [1, 2, 3, 4]
B = [5, 6, 7, 8]
C = [19, 22, 43, 50]
```

---

### 6. Cómo repartir la multiplicación en `pthreads`
#### Idea principal (reparto por filas de `C`)
Cada hilo calcula un rango de filas de `C`.

#### Fórmulas generales (para cualquier número de hilos `T`)
```c
row_start = (t * N) / T;
row_end   = ((t + 1) * N) / T;
```

- Hilo `t` procesa filas en el rango `[row_start, row_end)`
- Rango semiabierto:
  - incluye `row_start`
  - excluye `row_end`

#### Ventajas
- No necesitas `mutex`
- Cada hilo escribe en filas distintas de `C`
- `A` y `B` son solo lectura

---

### 7. Ejemplo visual 2x2 con 2 hilos
#### Datos
- `N = 2`
- `T = 2`

#### Repartición
- Hilo `0`:
  - `row_start = (0*2)/2 = 0`
  - `row_end   = (1*2)/2 = 1`
  - procesa fila `0`
- Hilo `1`:
  - `row_start = (1*2)/2 = 1`
  - `row_end   = (2*2)/2 = 2`
  - procesa fila `1`

#### Qué calcula cada hilo
- Hilo 0:
  - `C[0][0] = 19`
  - `C[0][1] = 22`
- Hilo 1:
  - `C[1][0] = 43`
  - `C[1][1] = 50`

#### Resultado final
```text
C = [ [19, 22],
      [43, 50] ]
```

---

### 8. ¿Por qué `row_end` usa `(t + 1)`?
Porque `row_end` es la frontera derecha del bloque del hilo `t`, y debe coincidir con el inicio del siguiente hilo.

#### Fórmulas como fronteras
- frontera izquierda del hilo `t`: `(t * N) / T`
- frontera derecha del hilo `t`: `((t + 1) * N) / T`

#### Ejemplo (`N=10`, `T=4`)
- `t=0`: `[0, 2)`
- `t=1`: `[2, 5)`
- `t=2`: `[5, 7)`
- `t=3`: `[7, 10)`

No hay huecos ni solapamientos.

#### Si usaras `row_end = (t*N)/T`
El hilo 0 tendría:
- `row_start = 0`
- `row_end = 0`
- no haría trabajo

---

### 9. Plantilla básica de `pthreads` (estructura recomendada)
#### Estructura de argumentos por hilo
```c
typedef struct {
    int tid;
    int nthreads;
    int N;
    const int32_t *A;
    const int32_t *B;
    int32_t *C;
    int row_start;
    int row_end;
} ThreadArgs;
```

#### Worker (función del hilo)
```c
void *worker_matmul(void *arg) {
    ThreadArgs *p = (ThreadArgs *)arg;
    size_t n = (size_t)p->N;

    for (int i = p->row_start; i < p->row_end; i++) {
        const int32_t *Ai = &p->A[(size_t)i * n];
        for (int j = 0; j < p->N; j++) {
            int64_t acc = 0;
            for (int k = 0; k < p->N; k++) {
                acc += (int64_t)Ai[k] * (int64_t)p->B[(size_t)k * n + (size_t)j];
            }
            p->C[(size_t)i * n + (size_t)j] = (int32_t)acc;
        }
    }
    return NULL;
}
```

#### Creación y unión de hilos
```c
for (int t = 0; t < T; t++) {
    args[t].row_start = (t * N) / T;
    args[t].row_end   = ((t + 1) * N) / T;
    pthread_create(&threads[t], NULL, worker_matmul, &args[t]);
}

for (int t = 0; t < T; t++) {
    pthread_join(threads[t], NULL);
}
```

---

### 10. Cómo escala a 2, 4, 8 y 16 hilos
No cambias el algoritmo. Solo cambias `T`.

- `T=2`: 2 bloques de filas
- `T=4`: 4 bloques de filas
- `T=8`: 8 bloques de filas
- `T=16`: 16 bloques de filas

La fórmula de `row_start/row_end` ya resuelve el reparto automáticamente.

---

### 11. Nota importante de rendimiento (HPC real)
Aunque el layout actual es bueno, el acceso a `B[k*N + j]` es por columna y penaliza cache.

#### Mejora recomendada
- Transponer `B` una vez (`BT[j*N + k]`)
- Multiplicar usando `BT` para que los accesos sean contiguos

Esto suele mejorar mucho más el rendimiento y el escalado con hilos.

---

### 12. Ruta sugerida para implementar `pthreads` en tu proyecto
1. Mantener matrices contiguas (`int32_t *`)
2. Implementar reparto por filas con `pthreads`
3. Verificar checksum contra versión secuencial
4. Medir tiempos (2, 4, 8, 16 hilos)
5. Añadir versión con `B` transpuesta
6. Luego probar blocking/tiling si quieren ir más lejos

---

### 13. Resumen final (decisión técnica)
- La forma actual de `matmul` con indexado lineal es la correcta para escalar en HPC con `pthreads`.
- `int32_t **` con `malloc` por fila es más fácil de leer al inicio, pero peor para rendimiento y escalabilidad.
- La repartición por filas usando `[row_start, row_end)` es la forma más simple, segura y efectiva para comenzar.
