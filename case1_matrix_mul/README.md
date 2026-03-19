# Caso 1: Multiplicacion de matrices en HPC

Este caso de estudio evalua el comportamiento de la multiplicacion de matrices cuadradas bajo diferentes estrategias de ejecucion, con enfoque en rendimiento y escalabilidad. El objetivo es medir como cambia el tiempo de ejecucion cuando se aplican mejoras de memoria, optimizacion de compilacion y paralelismo con hilos y procesos.

## Contexto del experimento

La multiplicacion de matrices es una carga de trabajo clasica en computo de alto desempeno por su complejidad y alta demanda de CPU y memoria. En este caso se comparan implementaciones que representan escenarios reales:

- Baseline secuencial (referencia)
- Secuencial con mejora de acceso a memoria (transpuesta)
- Secuencial compilado con optimizacion O3
- Paralelismo por hilos (2, 4, 8, 16)
- Paralelismo por procesos (2, 4, 8, 16)

La comparacion permite responder preguntas como:

- Desde que tamano de matriz conviene paralelizar
- Que tecnica reduce mas el tiempo promedio
- Como varia el speedup en tamanos pequenos vs grandes

## Objetivo general

Comparar tiempos y speedup de todas las variantes para identificar la estrategia mas eficiente por rango de tamano de matriz.

## Objetivos especificos

- Medir tiempos por ronda para cada configuracion.
- Calcular promedio por tamano de matriz.
- Calcular speedup respecto al secuencial base.
- Consolidar resultados en tablas y graficas para su analisis.

## Configuracion evaluada

- Tamanos de matriz (N): 400, 600, 800, 1000, 2000, 4000, 5500, 6000, 8000
- Rondas: 10 ejecuciones por cada configuracion
- Metricas principales:
  - wall_s por ronda
  - Promedio por tamano N
  - Speedup respecto al secuencial base

## Caracteristicas del sistema de pruebas

Las mediciones de este caso fueron realizadas en el siguiente equipo:

- Procesador: Apple M4 chip with 10-core CPU, 10-core GPU, and 16-core Neural Engine
- Cantidad de nucleos: 10
- Cantidad de subprocesos/hilos: 10
- Frecuencia basica del procesador: 2.89 GHz
- Frecuencia turbo maxima: 4.46 GHz
- RAM: 16 GB DDR5 @ 6400 MHz
- SSD: 512 GB (lectura: 3034.5 MB/s, escritura: 3437.4 MB/s)
- Sistema operativo: macOS Tahoe 26.3.1
- Arquitectura: ARM

## Metodologia de comparacion

1. Se toma el secuencial base como referencia.
2. Para cada variante se calcula su tiempo promedio por N.
3. El speedup se define como:

   speedup = tiempo_secuencial_base / tiempo_variante

4. Se generan tablas por prueba (rondas, promedio y speedup).
5. Se consolidan tablas resumen para comparar todas las pruebas en una sola vista.

## Estructura de carpetas

- secuencial/: implementaciones secuenciales, tiempos base, transpuesta y O3
- hilos/: implementacion paralela con hilos y tablas por cantidad de hilos
- procesos/: implementacion paralela con procesos y tablas por cantidad de procesos
- resumen/: tablas consolidadas de speedup y promedios (CSV/PNG)

## Scripts de resumen

- generar_resumen_speedup.py
  - Lee la fila Speedup de cada prueba.
  - Genera tabla consolidada en CSV y PNG.

- generar_resumen_promedios.py
  - Lee la fila Promedio de cada prueba.
  - Incluye Secuencial al inicio como referencia temporal.
  - Genera tabla consolidada en CSV y PNG.

## Flujo recomendado de uso

1. Ejecutar las pruebas secuenciales, de hilos y de procesos.
2. Verificar que existan los CSV individuales en:
   - secuencial/output/tables
   - hilos/tables
   - procesos/tables
3. Generar resumen de speedup.
4. Generar resumen de promedios.
5. Analizar las tablas resumen y graficas de comparacion.

## Salidas esperadas

En la carpeta resumen se generan archivos consolidados para analisis y reporte:

- tabla_resumen_speedup.csv
- tabla_resumen_speedup.png
- tabla_resumen_promedios.csv
- tabla_resumen_promedios.png

## Interpretacion rapida de resultados

- Un speedup mayor a 1 indica mejora frente al secuencial base.
- En tamanos pequenos, el overhead de paralelizacion puede limitar ganancias.
- En tamanos grandes, hilos y procesos suelen mostrar mejor aceleracion.
- La comparacion de promedios permite identificar la estrategia mas estable por N.

## Resultado esperado del caso

Obtener evidencia cuantitativa para decidir que estrategia conviene segun el tamano de matriz y el objetivo del experimento (menor tiempo absoluto o mayor speedup relativo).
