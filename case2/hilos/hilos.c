#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <pthread.h>
#include <sys/resource.h>
#include <time.h>

// ============================================================
//  TIEMPOS
// ============================================================

// Tiempo de reloj de pared (real)
static double wall_seconds_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

// Tiempo de CPU del proceso (user + kernel)
static int process_cpu_seconds(double *user_s, double *kernel_s) {
    struct rusage ru;
    if (getrusage(RUSAGE_SELF, &ru) != 0) {
        *user_s = 0.0;
        *kernel_s = 0.0;
        return 0;
    }
    *user_s   = (double)ru.ru_utime.tv_sec + (double)ru.ru_utime.tv_usec * 1e-6;
    *kernel_s = (double)ru.ru_stime.tv_sec + (double)ru.ru_stime.tv_usec * 1e-6;
    return 1;
}

// ============================================================
//  PARSEO / UTILIDADES
// ============================================================

static void usage(const char *p) {
    fprintf(stderr, "Uso: %s N threads trials [seed]\n", p);
    fprintf(stderr, "Ej:  %s 400 2 10\n", p);
    fprintf(stderr, "Ej:  %s 1000 4 10 123456789\n", p);
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
    return (int32_t)r - (int32_t)0x3fffffff;
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

    // Caso pequeño para validar a mano (2x2)
    if (N == 2) {
        A[0] = 1; A[1] = 2;
        A[2] = 3; A[3] = 4;

        B[0] = 5; B[1] = 6;
        B[2] = 7; B[3] = 8;
        return;
    }

    for (size_t i = 0; i < n * n; i++) {
        A[i] = rand_i32();
        B[i] = rand_i32();
    }
}

static void zero_matrix(int N, int32_t *C) {
    size_t n = (size_t)N;
    for (size_t i = 0; i < n * n; i++) C[i] = 0;
}

static int64_t checksum_matrix(int N, const int32_t *C) {
    size_t n = (size_t)N;
    int64_t s = 0;
    for (size_t i = 0; i < n * n; i++) s += C[i];
    return s;
}

// ============================================================
//  HILOS
// ============================================================

typedef struct {
    int tid;
    int nthreads;
    int N;
    const int32_t *A;
    const int32_t *B;
    int32_t *C;
    int row_start; // incluida
    int row_end;   // excluida
} ThreadArgs;

// Cada hilo calcula SOLO su bloque de filas de C
static void *worker_matmul(void *arg) {
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

static int matmul_parallel(int N, int nthreads, const int32_t *A, const int32_t *B, int32_t *C) {
    pthread_t *threads = (pthread_t *)malloc((size_t)nthreads * sizeof(pthread_t));
    ThreadArgs *args   = (ThreadArgs *)malloc((size_t)nthreads * sizeof(ThreadArgs));

    if (!threads || !args) {
        free(threads);
        free(args);
        return 0;
    }

    // Crear hilos
    for (int t = 0; t < nthreads; t++) {
        args[t].tid = t;
        args[t].nthreads = nthreads;
        args[t].N = N;
        args[t].A = A;
        args[t].B = B;
        args[t].C = C;

        // Reparto por filas
        args[t].row_start = (t * N) / nthreads;
        args[t].row_end   = ((t + 1) * N) / nthreads;

        if (pthread_create(&threads[t], NULL, worker_matmul, &args[t]) != 0) {
            // Si falla, unir los ya creados
            for (int j = 0; j < t; j++) pthread_join(threads[j], NULL);
            free(threads);
            free(args);
            return 0;
        }
    }

    // Esperar a todos
    for (int t = 0; t < nthreads; t++) {
        pthread_join(threads[t], NULL);
    }

    free(threads);
    free(args);
    return 1;
}

// ============================================================
//  MAIN
// ============================================================

int main(int argc, char **argv) {
    int N, nthreads, trials;
    unsigned seed = 123456789u;

    if (argc < 4) { usage(argv[0]); return 1; }
    if (!parse_int(argv[1], &N))       { usage(argv[0]); return 1; }
    if (!parse_int(argv[2], &nthreads)){ usage(argv[0]); return 1; }
    if (!parse_int(argv[3], &trials))  { usage(argv[0]); return 1; }
    if (argc >= 5) seed = (unsigned)strtoul(argv[4], NULL, 10);

    // Si quieres solo estos valores:
    // 2, 4, 8, 16, 32
    if (nthreads != 2 && nthreads != 4 && nthreads != 8 &&
        nthreads != 16 && nthreads != 32) {
        fprintf(stderr, "threads debe ser: 2, 4, 8, 16 o 32\n");
        return 1;
    }

    srand(seed);

    int32_t *A = NULL, *B = NULL, *C = NULL;
    if (!allocate_matrices(N, &A, &B, &C)) {
        size_t bytes = (size_t)N * (size_t)N * sizeof(int32_t);
        fprintf(stderr, "Error: memoria insuficiente para N=%d (%.2f MB por matriz)\n",
                N, (double)bytes / (1024.0 * 1024.0));
        return 2;
    }

    fill_random_matrices(N, A, B);

    // Warm-up (no contado)
    zero_matrix(N, C);
    if (!matmul_parallel(N, nthreads, A, B, C)) {
        fprintf(stderr, "Error creando hilos en warm-up\n");
        free(A); free(B); free(C);
        return 3;
    }

    for (int t = 1; t <= trials; t++) {
        zero_matrix(N, C);

        double wall0 = wall_seconds_now();
        double u0 = 0.0, k0 = 0.0, u1 = 0.0, k1 = 0.0;
        process_cpu_seconds(&u0, &k0);

        if (!matmul_parallel(N, nthreads, A, B, C)) {
            fprintf(stderr, "Error creando hilos en trial %d\n", t);
            free(A); free(B); free(C);
            return 3;
        }

        process_cpu_seconds(&u1, &k1);
        double wall1 = wall_seconds_now();

        int64_t chk = checksum_matrix(N, C);

        double wall_s      = wall1 - wall0;
        double user_s      = u1 - u0;
        double kernel_s    = k1 - k0;
        double cpu_total_s = user_s + kernel_s;

        // N threads trial wall_s user_s kernel_s cpu_total_s checksum seed
        printf("%d %d %d %.6f %.6f %.6f %.6f %lld %u\n",
               N, nthreads, t, wall_s, user_s, kernel_s, cpu_total_s,
               (long long)chk, seed);
    }

    free(A); free(B); free(C);
    return 0;
}