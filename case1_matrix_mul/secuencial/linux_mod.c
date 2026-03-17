#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <time.h>
#include "../matrix.h"


// ============================================================
//  TIEMPOS
// ============================================================

static double wall_seconds_now(void) {

  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

static int process_cpu_seconds(double *user_s, double *kernel_s) {

  struct rusage ru;
  if (getrusage(RUSAGE_SELF, &ru) != 0) {
    *user_s = 0.0;
    *kernel_s = 0.0;
    return 0;
  }

  *user_s = (double)ru.ru_utime.tv_sec + (double)ru.ru_utime.tv_usec * 1e-6;
  *kernel_s = (double)ru.ru_stime.tv_sec + (double)ru.ru_stime.tv_usec * 1e-6;
  return 1;

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
//  MAIN
// ============================================================

int main(int argc, char **argv) {
  int N, trials;
  unsigned seed = 123456789u;

  if (argc < 4) { usage(argv[0]); return 1; }
  if (!parse_int(argv[1], &N)) { usage(argv[0]); return 1; }
  if (!parse_int(argv[2], &trials)) { usage(argv[0]); return 1; }
  if (argc >= 4) seed = (unsigned)strtoul(argv[3], NULL, 10);

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
           N, 1, t, wall_s, user_s, kernel_s, cpu_total_s,
           (long long)chk, seed);
  }

  free(A); free(B); free(C);
  return 0;
}
