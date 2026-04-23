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
    fprintf(stderr, "Uso: %s N trials [seed]\n", p);
    fprintf(stderr, "Ej:  %s 400 10\n", p);
    fprintf(stderr, "Ej:  %s 1000 10 123456789\n", p);
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
    if (N == 2){
      A[0] = 1; A[1] = 2;
      A[2] = 3; A[3] = 4;
      B[0] = 5; B[1] = 6;
      B[2] = 7; B[3] = 8;
      return;
    }
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
//  MULTIPLICACIÓN (B COMO SI ESTUVIERA TRANSPUESTA)
// ============================================================

static void matmul(int N, const int32_t *A, const int32_t *B, int32_t *C) {
    size_t n = (size_t)N;
    for (int i = 0; i < N; i++) {
        const int32_t *Ai = &A[(size_t)i * n];  // Fila i de A
        
        for (int j = 0; j < N; j++) {
            int64_t acc = 0;
            const int32_t *Bj = &B[(size_t)j * n];  // Fila j (que sería columna si no estuviera transpuesta)
            
            for (int k = 0; k < N; k++) {
                acc += (int64_t)Ai[k] * (int64_t)Bj[k];  // Acceso secuencial
            }
            C[(size_t)i * n + (size_t)j] = (int32_t)acc;
        }
    }
}


// ============================================================
//  MAIN
// ============================================================

int main(int argc, char **argv) {
    int N, trials;
    unsigned seed = 123456789u;

    if (argc < 3) { usage(argv[0]); return 1; }
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

        // N trial wall user kernel cpu_total checksum seed
        printf("%d %d %.6f %.6f %.6f %.6f %lld %u\n",
               N, t, wall_s, user_s, kernel_s, cpu_total_s,
               (long long)chk, seed);
    }

    free(A); free(B); free(C);
    return 0;
}