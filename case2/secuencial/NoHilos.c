  #define _POSIX_C_SOURCE 199309L
  #include <stdio.h>
  #include <stdlib.h>
  #include <stdint.h>
  #include <sys/resource.h>
  #include <sys/time.h>
  #include <time.h>

  // ============================================================
  //  TIEMPOS
  // ============================================================

  // Obtiene el tiempo de reloj real (wall-clock) actual en segundos.
  // Útil para medir duración total observada, incluyendo pausas del SO.
  static double wall_seconds_now(void) {
      struct timespec ts;
      clock_gettime(CLOCK_MONOTONIC, &ts);  // Reloj monótono, no afectado por cambios de hora
      return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;  // Conversión a segundos decimales
  }

  // Obtiene el tiempo de CPU consumido por el proceso actual.
  // Distingue entre tiempo en modo usuario (user_s) y modo kernel (kernel_s).
  static int process_cpu_seconds(double *user_s, double *kernel_s) {
      struct rusage ru;
      if (getrusage(RUSAGE_SELF, &ru) != 0) {
          *user_s = 0.0;
          *kernel_s = 0.0;
          return 0;  // Error al obtener datos
      }
      // Tiempo de CPU en modo usuario: segundos + microsegundos convertidos a segundos
      *user_s = (double)ru.ru_utime.tv_sec + (double)ru.ru_utime.tv_usec * 1e-6;
      // Tiempo de CPU en modo kernel: segundos + microsegundos convertidos a segundos
      *kernel_s = (double)ru.ru_stime.tv_sec + (double)ru.ru_stime.tv_usec * 1e-6;
      return 1;  // Éxito
  }

  // ============================================================
  //  PARSEO / UTILIDADES
  // ============================================================

  // Imprime instrucciones de uso del programa.
  // Parámetros:
  //   N: tamaño de las matrices (N x N)
  //   trials: número de repeticiones de la multiplicación
  //   seed: semilla para reproducibilidad (opcional)
  static void usage(const char *p) {
      fprintf(stderr, "Uso: %s N trials [seed]\n", p);
      fprintf(stderr, "Ej:  %s 400 10\n", p);
      fprintf(stderr, "Ej:  %s 1000 10 123456789\n", p);
  }

  // Parsea un argumento de línea de comandos como entero.
  // Valida que esté en rango [1, 50000] y sea formato válido.
  // Retorna 1 si es válido, 0 si hay error.
  static int parse_int(const char *s, int *out) {
      char *end = NULL;
      long v = strtol(s, &end, 10);  // Conversión segura
      if (!s[0] || (end && *end != '\0')) return 0;  // Formato inválido
      if (v <= 0 || v > 50000) return 0;  // Fuera de rango
      *out = (int)v;
      return 1;
  }

  // ============================================================
  //  ALEATORIOS / MATRICES
  // ============================================================

  // Genera un número pseudoaleatorio de 32 bits en rango [-1e9, +1e9].
  // Combina múltiples llamadas a rand() para obtener 32 bits de aleatoriedad.
  // El rango acotado evita desbordamientos en multiplicación de int32_t.
  static int32_t rand_i32(void) {
      uint32_t r = 0;
      r ^= (uint32_t)(rand() & 0x7fff);  // 15 bits
      r <<= 15;
      r ^= (uint32_t)(rand() & 0x7fff);  // 15 bits más
      r <<= 1;
      r ^= (uint32_t)(rand() & 0x0001);  // 1 bit más
      return (int32_t)(r) - (int32_t)0x3fffffff;  // Ajuste a [-1e9, +1e9]
  }

  // Reserva memoria para tres matrices cuadradas de tamaño N x N.
  // Cada matriz ocupa N² * 4 bytes (int32_t = 4 bytes).
  // Retorna 1 si éxito, 0 si falla (libera parciales).
  static int allocate_matrices(int N, int32_t **A, int32_t **B, int32_t **C) {
      size_t n = (size_t)N;
      size_t bytes = n * n * sizeof(int32_t);  // N² elementos de 4 bytes cada uno

      *A = (int32_t*)malloc(bytes);  // Matriz A de entrada
      *B = (int32_t*)malloc(bytes);  // Matriz B de entrada
      *C = (int32_t*)malloc(bytes);  // Matriz C de resultado (A * B)

      // Si alguna asignación falló, libera todo lo reservado
      if (!(*A) || !(*B) || !(*C)) {
          free(*A); free(*B); free(*C);
          *A = *B = *C = NULL;
          return 0;
      }
      return 1;
  }

  // Rellena las matrices A y B con valores.
  // Caso especial N=2: usa valores predefinidos (útil para debugging/verificación).
  // En general: valores pseudoaleatorios para pruebas de rendimiento.
  static void fill_random_matrices(int N, int32_t *A, int32_t *B) {
      size_t n = (size_t)N;
      // Caso de prueba: matrices 2x2 con valores conocidos
      if (N == 2){
        A[0] = 1; A[1] = 2;  // Fila 0 de A
        A[2] = 3; A[3] = 4;  // Fila 1 de A
        B[0] = 5; B[1] = 6;  // Fila 0 de B
        B[2] = 7; B[3] = 8;  // Fila 1 de B
        return;
      }
      // Caso general: llenar con valores aleatorios
      for (size_t i = 0; i < n*n; i++) {
          A[i] = rand_i32();  // Elemento i de matriz A
          B[i] = rand_i32();  // Elemento i de matriz B
      }
  }

  // Reinicia una matriz a ceros.
  // Se ejecuta antes de cada trial para medir la multiplicación limpia.
  static void zero_matrix(int N, int32_t *C) {
      size_t n = (size_t)N;
      for (size_t i = 0; i < n*n; i++) C[i] = 0;  // Todos los N² elementos a 0
  }

  // Calcula suma de todos los elementos de la matriz (checksum).
  // Verifica que el resultado es consistente sin imprimir toda la matriz.
  // Usa int64_t para evitar overflow con matrices grandes.
  static int64_t checksum_matrix(int N, const int32_t *C) {
      size_t n = (size_t)N;
      int64_t s = 0;
      for (size_t i = 0; i < n*n; i++) s += C[i];  // Suma acumulada
      return s;
  }

  // ============================================================
  //  MULTIPLICACIÓN DE MATRICES
  // ============================================================

  // Algoritmo de multiplicación de matrices: C = A × B
  // Usa triple bucle (O(N³)) en orden i-j-k.
  // Cada elemento C[i,j] es la suma del producto por elementos de fila i de A
  // multiplicados por los elementos de columna j de B.
  static void matmul(int N, const int32_t *A, const int32_t *B, int32_t *C) {
      size_t n = (size_t)N;
      // Bucle sobre filas de matriz resultado C
      for (int i = 0; i < N; i++) {
          // Bucle sobre columnas de matriz resultado C
          for (int j = 0; j < N; j++) {
              int64_t acc = 0;  // Acumulador: suma de productos elemento-sabio
              const int32_t *Ai = &A[(size_t)i * n];  // Puntero a fila i de A
              // Bucle de producto punto: fila i de A × columna j de B
              for (int k = 0; k < N; k++) {
                  // Suma: A[i,k] × B[k,j]
                  acc += (int64_t)Ai[k] * (int64_t)B[(size_t)k * n + (size_t)j];
              }
              // Resultado: C[i,j] = suma acumulada (truncada a int32_t)
              C[(size_t)i * n + (size_t)j] = (int32_t)acc;
          }
      }
  }


  // ============================================================
  //  MAIN - Orquestación de ejecución
  // ============================================================

  int main(int argc, char **argv) {
      int N, trials;  // N: tamaño matriz (N×N), trials: número de repeticiones
      unsigned seed = 123456789u;  // Semilla por defecto para reproducibilidad

      // Parseo de argumentos con validación
      if (argc < 3) { usage(argv[0]); return 1; }
      if (!parse_int(argv[1], &N)) { usage(argv[0]); return 1; }  // argv[1] = N
      if (!parse_int(argv[2], &trials)) { usage(argv[0]); return 1; }  // argv[2] = trials
      if (argc >= 4) seed = (unsigned)strtoul(argv[3], NULL, 10);  // argv[3] = seed (opcional)

      // Inicializa generador de números aleatorios con semilla
      srand(seed);

      // Matrices A y B (entrada), C (salida: resultado de A × B)
      int32_t *A = NULL, *B = NULL, *C = NULL;
      if (!allocate_matrices(N, &A, &B, &C)) {
          size_t n = (size_t)N;
          size_t bytes = n * n * sizeof(int32_t);
          fprintf(stderr, "Error: memoria insuficiente para N=%d (%.2f MB por matriz)\n",
                  N, (double)bytes / (1024.0 * 1024.0));
          return 2;
      }

      // Inicializa matrices A y B con datos (aleatorios o predefinidos para N=2)
      fill_random_matrices(N, A, B);

      // WARM-UP: Ejecución previa sin contar, para cargar cachés y páginas.
      // Evita que la primera medición salga sesgada por costos de arranque.
      zero_matrix(N, C);
      matmul(N, A, B, C);

      // CICLO DE MEDICIONES: trials repeticiones del cálculo
      for (int t = 1; t <= trials; t++) {
          // Reinicia matriz resultado a ceros antes de cada trial
          zero_matrix(N, C);

          // Captura tiempos iniciales (reloj real y CPU)
          double wall0 = wall_seconds_now();  // Tiempo real antes
          double u0=0, k0=0, u1=0, k1=0;  // Tiempos CPU: usuario y kernel
          process_cpu_seconds(&u0, &k0);  // Tiempos CPU antes

          // NÚCLEO: Multiplicación C = A × B
          matmul(N, A, B, C);

          // Captura tiempos finales
          process_cpu_seconds(&u1, &k1);  // Tiempos CPU después
          double wall1 = wall_seconds_now();  // Tiempo real después

          // Validación: checksum del resultado (sin imprimir toda C)
          int64_t chk = checksum_matrix(N, C);

          // Cálculo de deltas: tiempo transcurrido en esta trial
          double wall_s = wall1 - wall0;  // Tiempo real total (pared)
          double user_s = u1 - u0;  // CPU en modo usuario
          double kernel_s = k1 - k0;  // CPU en modo kernel
          double cpu_total_s = user_s + kernel_s;  // CPU total = usuario + kernel

          // Imprime resultados de esta trial:
          // N trial wall user kernel cpu_total checksum seed
          printf("%d %d %.6f %.6f %.6f %.6f %lld %u\n",
                N,              // Tamaño de la matriz
                t,              // Número de trial (1 a trials)
                wall_s,         // Tiempo real (wall-clock) en segundos
                user_s,         // CPU en modo usuario en segundos
                kernel_s,       // CPU en modo kernel en segundos
                cpu_total_s,    // CPU total en segundos
                (long long)chk, // Suma de elementos de C (validación)
                seed);          // Semilla usado para reproducibilidad
      }

      // Liberación de memoria dinámica
      free(A); free(B); free(C);
      return 0;
  }