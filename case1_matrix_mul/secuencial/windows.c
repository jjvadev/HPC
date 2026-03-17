#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#ifdef _WIN32
  #include <windows.h>
#endif

#ifdef _OPENMP
  #include <omp.h>
#endif

// ============================================================
//  TIEMPOS
// ============================================================

static double wall_seconds_now(void) {
#ifdef _WIN32
  static LARGE_INTEGER freq;
  static int inited = 0;
  LARGE_INTEGER t;
  if (!inited) { QueryPerformanceFrequency(&freq); inited = 1; }
  QueryPerformanceCounter(&t);
  return (double)t.QuadPart / (double)freq.QuadPart;
#else
  #include <time.h>
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
#endif
}

static int process_cpu_seconds(double *user_s, double *kernel_s) {
#ifdef _WIN32
  FILETIME ftCreate, ftExit, ftKernel, ftUser;
  ULARGE_INTEGER k, u;

  if (!GetProcessTimes(GetCurrentProcess(), &ftCreate, &ftExit, &ftKernel, &ftUser))
    return 0;

  k.LowPart = ftKernel.dwLowDateTime; k.HighPart = ftKernel.dwHighDateTime;
  u.LowPart = ftUser.dwLowDateTime;   u.HighPart = ftUser.dwHighDateTime;

  *kernel_s = (double)k.QuadPart * 1e-7; // 100ns -> s
  *user_s   = (double)u.QuadPart * 1e-7;
  return 1;
#else
  *user_s = 0.0; *kernel_s = 0.0;
  return 1;
#endif
}

// ============================================================
//  CONTROL DE “NO PEREZA” (Windows)
// ============================================================

static void set_high_priority(void) {
#ifdef _WIN32
  SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS);
  SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_HIGHEST);
#endif
}

static void set_affinity_first_cores(int threads) {
#ifdef _WIN32
  if (threads <= 0) return;
  if (threads > 63) threads = 63;
  DWORD_PTR mask = ((DWORD_PTR)1 << threads) - (DWORD_PTR)1;
  SetProcessAffinityMask(GetCurrentProcess(), mask);
#else
  (void)threads;
#endif
}

// ============================================================
//  PARSEO / UTILIDADES
// ============================================================

static void usage(const char *p) {
  fprintf(stderr, "Uso: %s N threads trials [seed]\n", p);
  fprintf(stderr, "Ej:  %s 400 1 10\n", p);
  fprintf(stderr, "Ej:  %s 1000 8 10 123456789\n", p);
}

static int parse_int(const char *s, int *out) {
  char *end = NULL;
  long v = strtol(s, &end, 10);
  if (!s[0] || (end && *end != '\0')) return 0;
  if (v <= 0 || v > 50000) return 0;
  *out = (int)v;
  return 1;
}

// ============================================================
//  ALEATORIOS / MATRICES
// ============================================================

static int32_t rand_i32(void) {
  uint32_t r = 0;
  r ^= (uint32_t)(rand() & 0x7fff);
  r <<= 15;
  r ^= (uint32_t)(rand() & 0x7fff);
  r <<= 1;
  r ^= (uint32_t)(rand() & 0x0001);
  return (int32_t)(r) - (int32_t)0x3fffffff;
}

static int allocate_matrices(int N, int32_t **A, int32_t **B, int32_t **C) {
  size_t n = (size_t)N;
  size_t bytes = n * n * sizeof(int32_t);

  *A = (int32_t*)malloc(bytes);
  *B = (int32_t*)malloc(bytes);
  *C = (int32_t*)malloc(bytes);

  if (!(*A) || !(*B) || !(*C)) {
    free(*A); free(*B); free(*C);
    *A = *B = *C = NULL;
    return 0;
  }
  return 1;
}

static void fill_random_matrices(int N, int32_t *A, int32_t *B) {
  size_t n = (size_t)N;
  for (size_t i = 0; i < n*n; i++) {
    A[i] = rand_i32();
    B[i] = rand_i32();
  }
}

static void zero_matrix(int N, int32_t *C) {
  size_t n = (size_t)N;
  for (size_t i = 0; i < n*n; i++) C[i] = 0;
}

static int64_t checksum_matrix(int N, const int32_t *C) {
  size_t n = (size_t)N;
  int64_t s = 0;
  for (size_t i = 0; i < n*n; i++) s += C[i];
  return s;
}

// ============================================================
//  MULTIPLICACIÓN
// ============================================================

static void matmul(int N, const int32_t *A, const int32_t *B, int32_t *C) {
  size_t n = (size_t)N;

#ifdef _OPENMP
#pragma omp parallel for schedule(static)
#endif
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      int64_t acc = 0;
      const int32_t *Ai = &A[(size_t)i * n];
      for (int k = 0; k < N; k++) {
        acc += (int64_t)Ai[k] * (int64_t)B[(size_t)k * n + (size_t)j];
      }
      C[(size_t)i * n + (size_t)j] = (int32_t)acc;
    }
  }
}

// ============================================================
//  CONFIGURACIÓN DE HILOS
// ============================================================

static void configure_threads(int threads) {
#ifdef _OPENMP
  omp_set_dynamic(0);
  omp_set_num_threads(threads);
#else
  (void)threads;
#endif
}

// ============================================================
//  MAIN
// ============================================================

int main(int argc, char **argv) {
  int N, threads, trials;
  unsigned seed = 123456789u;

  if (argc < 4) { usage(argv[0]); return 1; }
  if (!parse_int(argv[1], &N)) { usage(argv[0]); return 1; }
  if (!parse_int(argv[2], &threads)) { usage(argv[0]); return 1; }
  if (!parse_int(argv[3], &trials)) { usage(argv[0]); return 1; }
  if (argc >= 5) seed = (unsigned)strtoul(argv[4], NULL, 10);

  set_high_priority();
  set_affinity_first_cores(threads);
  configure_threads(threads);

  srand(seed);

  int32_t *A = NULL, *B = NULL, *C = NULL;
  if (!allocate_matrices(N, &A, &B, &C)) {
    size_t n = (size_t)N;
    size_t bytes = n * n * sizeof(int32_t);
    fprintf(stderr, "Error: memoria insuficiente para N=%d (%.2f MB por matriz)\n",
            N, (double)bytes / (1024.0 * 1024.0));
    return 2;
  }

  fill_random_matrices(N, A, B);

  // Warm-up (no contado)
  zero_matrix(N, C);
  matmul(N, A, B, C);

  for (int t = 1; t <= trials; t++) {
    zero_matrix(N, C);

    double wall0 = wall_seconds_now();
    double u0=0, k0=0, u1=0, k1=0;
    process_cpu_seconds(&u0, &k0);

    matmul(N, A, B, C);

    process_cpu_seconds(&u1, &k1);
    double wall1 = wall_seconds_now();

    int64_t chk = checksum_matrix(N, C);

    double wall_s = wall1 - wall0;
    double user_s = u1 - u0;
    double kernel_s = k1 - k0;
    double cpu_total_s = user_s + kernel_s;

    // N threads trial wall user kernel cpu_total checksum seed
    printf("%d %d %d %.6f %.6f %.6f %.6f %lld %u\n",
           N, threads, t, wall_s, user_s, kernel_s, cpu_total_s,
           (long long)chk, seed);
  }

  free(A); free(B); free(C);
  return 0;
}