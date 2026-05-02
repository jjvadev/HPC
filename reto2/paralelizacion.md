# Estrategia de Paralelización con OpenMP

## 1. Tipo de paralelismo

Se utilizó **paralelismo de datos (data parallelism)**.

Esto significa que el problema se divide en partes independientes que pueden ejecutarse simultáneamente. En este caso, cada celda de la carretera puede calcularse de forma independiente porque:

- El nuevo estado de una celda `i` depende únicamente de:
  - `old[i-1]`
  - `old[i]`
  - `old[i+1]`
- No depende de otros valores del nuevo arreglo (`new`)

Por lo tanto, todas las celdas pueden actualizarse en paralelo.

---

## 2. Descomposición del problema

Se utilizó una estrategia de **descomposición por dominio (domain decomposition)**.

La carretera de `N` celdas se divide entre los hilos disponibles.

Ejemplo con 4 hilos:

- Hilo 0 → celdas 1 a N/4  
- Hilo 1 → celdas N/4 a N/2  
- Hilo 2 → celdas N/2 a 3N/4  
- Hilo 3 → celdas 3N/4 a N  

Cada hilo trabaja sobre una parte distinta del arreglo.

---

## 3. Implementación con OpenMP

Se utilizó la directiva:

```c
#pragma omp parallel for reduction(+:moved) schedule(static)
```

Esta directiva permite:

- Dividir automáticamente el bucle entre los hilos
- Ejecutar iteraciones en paralelo
- Sincronizar correctamente la variable `moved`

---

## 4. Manejo de dependencias

El algoritmo es paralelizable porque:

- Todos los hilos **leen** del arreglo `old`
- Cada hilo **escribe únicamente en su propia posición `new[i]`**

Esto evita:

- Condiciones de carrera
- Escrituras concurrentes en la misma posición

---

## 5. Variable compartida: `moved`

La variable `moved` cuenta cuántos carros se desplazan.

En ejecución paralela, múltiples hilos la modifican. Para evitar errores, se utiliza:

```c
reduction(+:moved)
```

Esto significa:

- Cada hilo tiene una copia local de `moved`
- Al finalizar, OpenMP suma todas las copias

---

## 6. Política de planificación

Se utilizó:

```c
schedule(static)
```

Esto asigna bloques fijos de iteraciones a cada hilo.

Ventajas:

- Bajo costo de gestión
- Adecuado cuando todas las iteraciones tienen un costo similar

---

## 7. Manejo de frontera periódica

Las condiciones de frontera se manejan fuera de la región paralela:

```c
new[0]   = new[N];
new[N+1] = new[1];
```

Esto se hace porque:

- Son pocas operaciones
- No vale la pena paralelizarlas
- Reduce complejidad

---

## 8. Limitaciones de la paralelización

Aunque el algoritmo es paralelizable, el rendimiento no escala de forma lineal debido a:

- Limitaciones del ancho de banda de memoria
- Competencia entre hilos por acceso a RAM

Por esta razón, se observa que:

- El rendimiento mejora hasta cierto número de hilos
- A partir de cierto punto (por ejemplo, 8 hilos), el rendimiento deja de mejorar o incluso disminuye

---

## 9. Conclusión

La estrategia de paralelización se basa en:

- Paralelismo de datos
- Descomposición del dominio
- Uso de OpenMP con `parallel for`
- Uso de reducción para variables compartidas

Esto permite una implementación eficiente y segura, aprovechando múltiples núcleos del procesador.