# Guía Didáctica: Multiplicación de Matrices con Procesos (fork)

## 📚 Índice

1. [¿Qué son los procesos?](#qué-son-los-procesos)
2. [Diferencia: Procesos vs Hilos](#diferencia-procesos-vs-hilos)
3. [Memoria Compartida](#memoria-compartida)
4. [Cómo funciona el código](#cómo-funciona-el-código)
5. [Ejemplo visual paso a paso](#ejemplo-visual-paso-a-paso)
6. [Comandos de uso](#comandos-de-uso)

---

## 🔍 ¿Qué son los procesos?

Un **proceso** es un programa en ejecución con:

- Su propio espacio de memoria (independiente)
- Su propio PID (Process ID)
- Sus propios recursos (archivos, variables, etc.)

**Analogía:** Si tu computadora es una fábrica:

- Cada **proceso** es un trabajador con su propia oficina y herramientas
- Cada **hilo** (thread) es un trabajador que comparte la oficina con otros

---

## ⚖️ Diferencia: Procesos vs Hilos

| Característica   | Procesos                                 | Hilos                             |
| ---------------- | ---------------------------------------- | --------------------------------- |
| **Memoria**      | Separada (copy-on-write)                 | Compartida automáticamente        |
| **Comunicación** | Necesita IPC (pipes, memoria compartida) | Directa (variables globales)      |
| **Creación**     | Más lenta (`fork()`)                     | Más rápida (`pthread_create()`)   |
| **Overhead**     | Mayor (context switching pesado)         | Menor                             |
| **Aislamiento**  | Fuerte (un crash no afecta otros)        | Débil (un crash tumba todo)       |
| **Uso típico**   | Tareas independientes, seguridad         | Paralelismo dentro de un programa |

**En nuestro caso:**

- **Hilos:** comparten `A`, `B`, `C` automáticamente
- **Procesos:** necesitan `mmap()` para compartir `C`

---

## 🗺️ Memoria Compartida

### Problema

Cuando haces `fork()`, cada proceso hijo obtiene una **copia** de la memoria del padre.

```
Padre:  A[...], B[...], C[...]
   ↓ fork()
Hijo 1: A[...], B[...], C[...]  ← copia independiente
Hijo 2: A[...], B[...], C[...]  ← otra copia
```

Si cada hijo escribe en su propia `C`, el padre **nunca verá los resultados**.

### Solución: `mmap()` con `MAP_SHARED`

```c
C = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
         MAP_SHARED | MAP_ANONYMOUS, -1, 0);
```

Esto crea una región de memoria que:

- ✅ Es visible para **todos los procesos** (padre e hijos)
- ✅ Los cambios de un proceso se ven en los demás
- ✅ Persiste después del `fork()`

```
Padre, Hijo 1, Hijo 2 → todos apuntan a la MISMA C[...]
```

---

## 🛠️ Cómo funciona el código

### 1️⃣ **Asignación de memoria**

```c
// A y B: memoria normal (privada por proceso)
allocate_matrices(N, &A, &B);

// C: memoria compartida (visible por todos)
C = allocate_shared_matrix(N);  // usa mmap(MAP_SHARED)
```

**¿Por qué A y B no necesitan ser compartidas?**

- Solo se **leen**, nunca se modifican
- Después del `fork()`, cada hijo tiene su copia read-only (eficiente por copy-on-write)

---

### 2️⃣ **División del trabajo**

El padre divide la matriz `C` por **filas**:

```c
for (int p = 0; p < nprocs; p++) {
    int row_start = (p * N) / nprocs;
    int row_end = ((p + 1) * N) / nprocs;

    // Proceso 0: filas [0, N/nprocs)
    // Proceso 1: filas [N/nprocs, 2*N/nprocs)
    // ...
}
```

**Ejemplo con N=1000, nprocs=4:**

- Proceso 0: filas 0-249
- Proceso 1: filas 250-499
- Proceso 2: filas 500-749
- Proceso 3: filas 750-999

---

### 3️⃣ **Creación de procesos con `fork()`**

```c
pid_t pid = fork();

if (pid < 0) {
    // Error: no se pudo crear el proceso
}

if (pid == 0) {
    // CÓDIGO DEL HIJO
    matmul_rows(N, A, B, C, row_start, row_end);
    _exit(0);  // Termina el hijo
}

// CÓDIGO DEL PADRE (pid > 0)
children[p] = pid;  // Guarda el PID del hijo
```

**¿Qué pasa aquí?**

1. `fork()` **duplica** el proceso actual
2. El hijo recibe `pid = 0`
3. El padre recibe `pid = PID_del_hijo`
4. Ambos continúan desde la línea después de `fork()`

**Visual:**

```
Padre (PID 1000) llama fork()
    ↓
Padre (PID 1000, ve pid=1001) → guarda PID del hijo
Hijo  (PID 1001, ve pid=0)    → calcula filas asignadas
```

---

### 4️⃣ **Trabajo en paralelo**

Cada hijo ejecuta:

```c
static void matmul_rows(int N, const int32_t *A, const int32_t *B,
                        int32_t *C, int row_start, int row_end) {
    for (int i = row_start; i < row_end; i++) {
        const int32_t *Ai = &A[i * N];
        for (int j = 0; j < N; j++) {
            int64_t acc = 0;
            for (int k = 0; k < N; k++) {
                acc += Ai[k] * B[k * N + j];
            }
            C[i * N + j] = (int32_t)acc;  // Escribe en memoria compartida
        }
    }
}
```

**Clave:** cada hijo escribe en **filas distintas** de `C`, así no hay conflicto.

---

### 5️⃣ **Espera con `waitpid()`**

El padre debe esperar a que **todos los hijos terminen** antes de leer `C`:

```c
for (int p = 0; p < nprocs; p++) {
    int status = 0;
    waitpid(children[p], &status, 0);  // Bloquea hasta que el hijo termine

    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        // El hijo terminó con error
    }
}
```

**¿Por qué es necesario?**

- Si el padre lee `C` antes de que los hijos terminen, verá datos incompletos.
- `waitpid()` es una **barrera de sincronización**.

---

### 6️⃣ **Limpieza**

```c
free_shared_matrix(N, C);  // munmap(C, bytes)
free(A);
free(B);
```

**Importante:** la memoria compartida (`mmap`) no se libera automáticamente con `free()`, necesita `munmap()`.

---

## 🎬 Ejemplo visual paso a paso

### Configuración: N=4, nprocs=2

#### **Paso 1: Inicialización**

```
Padre (PID 1000):
  A = [1 2 3 4]    B = [5 6 7 8]    C = [0 0 0 0]  ← memoria compartida
      [...]            [...]            [0 0 0 0]
      [...]            [...]            [0 0 0 0]
      [...]            [...]            [0 0 0 0]
```

#### **Paso 2: Fork proceso 0**

```
Padre (PID 1000):
  children[0] = 1001

Hijo 0 (PID 1001):
  row_start = 0
  row_end = 2
  → Calcula filas 0-1 de C
```

#### **Paso 3: Fork proceso 1**

```
Padre (PID 1000):
  children[1] = 1002

Hijo 1 (PID 1002):
  row_start = 2
  row_end = 4
  → Calcula filas 2-3 de C
```

#### **Paso 4: Trabajo en paralelo**

```
┌─────────────────┐     ┌─────────────────┐
│  Hijo 0 (1001)  │     │  Hijo 1 (1002)  │
│  Calcula:       │     │  Calcula:       │
│   C[0][j]       │     │   C[2][j]       │
│   C[1][j]       │     │   C[3][j]       │
└─────────────────┘     └─────────────────┘
         ↓                       ↓
    Escriben en la MISMA memoria C
```

#### **Paso 5: Padre espera**

```
Padre (PID 1000):
  waitpid(1001, ...)  ← espera
  waitpid(1002, ...)  ← espera
```

#### **Paso 6: Resultado**

```
C = [19 22 ...]  ← escrito por hijo 0
    [43 50 ...]  ← escrito por hijo 0
    [... ...]    ← escrito por hijo 1
    [... ...]    ← escrito por hijo 1
```

---

## 📟 Comandos de uso

### Compilar

```bash
cd case1_matrix_mul/procesos
gcc -O2 -std=c11 procesos.c -o procesos
```

### Ejecutar

```bash
# Formato: ./procesos N procesos trials [seed]

# Prueba pequeña (N=2, 2 procesos, 1 trial)
./procesos 2 2 1

# Caso real (N=1000, 4 procesos, 10 trials)
./procesos 1000 4 10 123456789
```

### Salida

```
N procesos trial wall_s user_s kernel_s cpu_total_s checksum seed
400 2 1 0.045968 0.091013 0.000014 0.091027 -254182613594 123456789
```

**Columnas:**

- `N`: tamaño de matriz
- `procesos`: número de procesos usados
- `trial`: número de prueba
- `wall_s`: tiempo real transcurrido
- `user_s`: tiempo en modo usuario
- `kernel_s`: tiempo en modo kernel
- `cpu_total_s`: user + kernel
- `checksum`: suma de verificación
- `seed`: semilla aleatoria

---

## 🔬 Comparación: Procesos vs Hilos

### Ventajas de procesos

✅ **Aislamiento:** si un hijo crashea, no afecta al padre ni otros hijos  
✅ **Seguridad:** cada proceso tiene su propio espacio de memoria  
✅ **Simplicidad conceptual:** no hay mutex, locks, race conditions

### Desventajas de procesos

❌ **Overhead mayor:** `fork()` es más lento que `pthread_create()`  
❌ **Comunicación compleja:** necesita `mmap`, pipes, sockets  
❌ **Memoria duplicada:** A y B se copian (aunque sea copy-on-write)

### ¿Cuándo usar cada uno?

| Usar Procesos                             | Usar Hilos                            |
| ----------------------------------------- | ------------------------------------- |
| Tareas completamente independientes       | Paralelismo dentro del mismo programa |
| Necesitas aislamiento fuerte              | Necesitas compartir muchos datos      |
| Seguridad/estabilidad crítica             | Baja latencia, alta frecuencia        |
| Ejemplo: servidor web (1 proceso/cliente) | Ejemplo: motor de videojuego          |

---

## 🧪 Experimento sugerido

Corre el mismo benchmark con hilos y procesos:

```bash
# Hilos
cd ../hilos
./hilos 2000 4 10 > results_threads.txt

# Procesos
cd ../procesos
./procesos 2000 4 10 > results_processes.txt

# Comparar tiempos
awk '{print $4}' results_threads.txt | awk '{s+=$1} END {print "Hilos:", s/NR}'
awk '{print $4}' results_processes.txt | awk '{s+=$1} END {print "Procesos:", s/NR}'
```

**Pregunta de investigación:** ¿Cuál es más rápido? ¿Por qué?

---

## 📚 Resumen de funciones clave

| Función            | Propósito                                             |
| ------------------ | ----------------------------------------------------- |
| `fork()`           | Crea un proceso hijo (copia del padre)                |
| `mmap(MAP_SHARED)` | Reserva memoria compartida entre procesos             |
| `waitpid()`        | Espera a que un proceso hijo termine                  |
| `_exit(0)`         | Termina el proceso hijo sin liberar recursos globales |
| `munmap()`         | Libera memoria compartida                             |

---

## 🎯 Conclusión

Este código demuestra **paralelismo basado en procesos** para multiplicación de matrices:

1. Divide el trabajo por **filas** (cada proceso calcula un bloque)
2. Usa **memoria compartida** (`mmap`) para `C`
3. Sincroniza con **waitpid** (barrera implícita)
4. Aprovecha **copy-on-write** para A y B (eficiente)

Es un ejemplo clásico de **paralelismo de datos** (data parallelism) con aislamiento fuerte entre trabajadores.
