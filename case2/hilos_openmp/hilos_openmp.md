# OpenMP en `hilos.c`: explicacion simple

Este documento explica:
1. Que es OpenMP.
2. Que hace `#pragma omp parallel for collapse(2)`.
3. Que lineas de tu codigo usan OpenMP.
4. Como se reparte el trabajo entre hilos en tu multiplicacion de matrices.

## 1) Que es OpenMP

OpenMP es una API para paralelizar programas en C/C++/Fortran con memoria compartida.

En C se usa con directivas del compilador:

```c
#pragma omp ...
```

Idea principal:
- Tu codigo empieza con un solo hilo (hilo maestro).
- Al entrar a una region `parallel`, OpenMP crea un equipo de hilos.
- Los hilos reparten iteraciones de bucles `for`.
- Al terminar, hay sincronizacion (barrera implicita) y se continua.

## 2) Lineas OpenMP en tu archivo

En `case2/hilos/hilos.c` se usan estas lineas importantes:

### a) Incluson de OpenMP
- Linea 8:

```c
#include <omp.h>
```

Sirve para usar funciones como `omp_set_num_threads`.

### b) Paralelizar el llenado de C en cero
- Linea 102:

```c
#pragma omp parallel for schedule(static)
```

Aplicado al `for` de la linea 103. Reparte las iteraciones del llenado `C[i] = 0` entre hilos.

### c) Paralelizar la multiplicacion de matrices
- Linea 124:

```c
#pragma omp parallel for collapse(2) schedule(static)
```

Aplicado al doble bucle `for (i)` y `for (j)` de lineas 125-126.

### d) Fijar cantidad de hilos
- Linea 155:

```c
omp_set_num_threads(threads);
```

Le dice a OpenMP cuántos hilos usar (segun argumento de linea de comandos).

## 3) Que significa `#pragma omp parallel for collapse(2)`

Desglose:

### `parallel`
Crea un equipo de hilos para ejecutar trabajo concurrentemente.

### `for`
Reparte las iteraciones del bucle entre esos hilos.

### `collapse(2)`
Le dice a OpenMP que combine 2 niveles de bucle anidado (`i` y `j`) en un solo espacio de iteraciones.

En lugar de repartir solo `i`, reparte pares `(i, j)`.
Eso mejora el balance de carga cuando hay muchos nucleos.

## 4) Como se paraleliza tu matmul

Tu nucleo es:

```c
#pragma omp parallel for collapse(2) schedule(static)
for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
        int64_t acc = 0;
        for (int k = 0; k < N; k++) {
            acc += A[i,k] * B[k,j];
        }
        C[i,j] = acc;
    }
}
```

Conceptualmente:
- Cada iteracion `(i,j)` calcula exactamente un elemento `C[i,j]`.
- OpenMP reparte esas iteraciones entre hilos.
- Cada hilo escribe en posiciones distintas de `C`.

Por eso no hay condicion de carrera en `C`.

## 5) Por que no hay race conditions aqui

No hay conflictos porque:
- `acc` es variable local de cada iteracion.
- Cada hilo calcula celdas distintas de `C`.
- No hay dos hilos escribiendo el mismo `C[i,j]`.

## 6) Que hace `schedule(static)`

`static` reparte iteraciones en bloques fijos entre hilos.

Ventajas en tu caso:
- Menor overhead de planificacion.
- Buena opcion cuando el costo por iteracion es parecido.

## 7) Ejemplo mental rapido (N=4, 2 hilos)

Con `collapse(2)`, el espacio de trabajo tiene 16 iteraciones:

`(0,0), (0,1), ..., (3,3)`

Con reparto estatico aproximado:
- Hilo 0 toma la primera mitad.
- Hilo 1 toma la segunda mitad.

Cada hilo calcula celdas distintas de `C`, luego se sincronizan al final del `parallel for`.

## 8) Resumen corto

- OpenMP paraleliza bucles con pragmas.
- `parallel for` crea hilos y reparte iteraciones.
- `collapse(2)` combina `i` y `j` para repartir mejor el trabajo del doble bucle.
- `schedule(static)` reparte bloques fijos, eficiente para trabajo uniforme.
- En tu matmul, cada hilo calcula elementos distintos de `C`, por eso funciona sin carreras.
