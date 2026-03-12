#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h> // Funciones como fork
#include <sys/wait.h> // Para la espera de procesos
#if defined(__APPLE__)
  #define _DARWIN_C_SOURCE
#endif
#include <sys/mman.h>


// ============================================================
//  TIEMPOS
// ============================================================

// wall_seconds_now:
// Devuelve el tiempo de reloj real (wall clock).
// Este tiempo sí cuenta espera del sistema, planificación del SO, etc.
// Lo usamos para medir "cuánto tardó" el experimento de punta a punta.
static double wall_seconds_now(void) {
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

// process_cpu_seconds:
// Obtiene tiempo de CPU consumido por ESTE proceso (no wall-time):
// - user_s: tiempo en espacio de usuario
// - kernel_s: tiempo en llamadas al kernel
// Si falla getrusage, regresamos 0 y colocamos ambos en 0.0.
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

// usage:
// Muestra cómo ejecutar el programa desde terminal.
static void usage(const char *p) {
	fprintf(stderr, "Uso: %s N procesos trials [seed]\n", p);
	fprintf(stderr, "Ej:  %s 400 2 10\n", p);
	fprintf(stderr, "Ej:  %s 1000 8 10 123456789\n", p);
}

// parse_int:
// Convierte texto -> entero validando que:
// 1) todo el argumento sea numérico
// 2) esté en rango razonable (1..50000)
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

// rand_i32:
// Construye un entero de 32 bits a partir de varias llamadas a rand().
// Esto evita depender solo de 15 bits de algunas implementaciones de rand().
static int32_t rand_i32(void) {
	uint32_t r = 0;
	r ^= (uint32_t)(rand() & 0x7fff);
	r <<= 15;
	r ^= (uint32_t)(rand() & 0x7fff);
	r <<= 1;
	r ^= (uint32_t)(rand() & 0x0001);
	return (int32_t)r - (int32_t)0x3fffffff;
}

// allocate_matrices:
// Reserva A y B en heap (memoria normal de proceso).
// NOTA: A y B solo se leen durante el cálculo, por eso no necesitamos
// que sean compartidas explícitamente con mmap.
static int allocate_matrices(int N, int32_t **A, int32_t **B) {
	size_t n = (size_t)N;
	size_t bytes = n * n * sizeof(int32_t);

	*A = (int32_t*)malloc(bytes);
	*B = (int32_t*)malloc(bytes);

	if (!(*A) || !(*B)) {
		free(*A);
		free(*B);
		*A = *B = NULL;
		return 0;
	}
	return 1;
}


// allocate_shared_matrix:
// Reserva C con mmap en modo compartido para que padre e hijos vean
// el MISMO arreglo de salida.
// MAP_ANON: no viene de archivo.
// MAP_SHARED: cambios visibles entre procesos.
static int32_t *allocate_shared_matrix(int N) {
	size_t bytes = (size_t)N * (size_t)N * sizeof(int32_t);
	void *p = mmap(NULL, bytes, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
	if (p == MAP_FAILED) return NULL;
	return (int32_t *)p;
}

// free_shared_matrix:
// Libera la región compartida reservada por mmap.
static void free_shared_matrix(int N, int32_t *C) {
	size_t bytes = (size_t)N * (size_t)N * sizeof(int32_t);
	if (C) {
		munmap(C, bytes);
	}
}

// fill_random_matrices:
// Llena A y B con datos pseudoaleatorios.
// Para N=2 usamos un caso fijo que permite verificar a mano.
static void fill_random_matrices(int N, int32_t *A, int32_t *B) {
	size_t n = (size_t)N;

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

// zero_matrix:
// Limpia C antes de cada prueba.
static void zero_matrix(int N, int32_t *C) {
	size_t n = (size_t)N;
	for (size_t i = 0; i < n * n; i++) C[i] = 0;
}

// checksum_matrix:
// Suma todos los elementos de C para validar consistencia entre ejecuciones.
// Si el checksum cambia entre 2/4/8/16 procesos, hay bug de correctitud.
static int64_t checksum_matrix(int N, const int32_t *C) {
	size_t n = (size_t)N;
	int64_t s = 0;
	for (size_t i = 0; i < n * n; i++) s += C[i];
	return s;
}

// ============================================================
//  PROCESOS
// ============================================================

// matmul_rows:
// Multiplica solo un bloque de filas [row_start, row_end).
// Esa partición evita condiciones de carrera porque cada proceso escribe
// en filas diferentes de C.
static void matmul_rows(int N, const int32_t *A, const int32_t *B, int32_t *C,
						int row_start, int row_end) {
	size_t n = (size_t)N;

	for (int i = row_start; i < row_end; i++) {
		// Matrices guardadas en 1D: índice(i,j) = i*n + j.
		// Ai apunta al inicio de la fila i de A para evitar recalcular i*n.
		const int32_t *Ai = &A[(size_t)i * n];
		for (int j = 0; j < N; j++) {
			// int64_t para reducir riesgo de overflow durante acumulación.
			int64_t acc = 0;
			for (int k = 0; k < N; k++) {
				// Producto punto: fila i de A por columna j de B.
				acc += (int64_t)Ai[k] * (int64_t)B[(size_t)k * n + (size_t)j];
			}
			// Guardamos el resultado final en C[i][j].
			C[(size_t)i * n + (size_t)j] = (int32_t)acc;
		}
	}
}

// matmul_parallel_processes:
// Orquesta el paralelismo por procesos con fork():
// 1) divide filas entre nprocs
// 2) crea procesos hijos
// 3) cada hijo calcula su bloque y termina
// 4) padre espera a todos con waitpid
static int matmul_parallel_processes(int N, int nprocs,
									 const int32_t *A, const int32_t *B, int32_t *C) {
	pid_t *children = (pid_t *)malloc((size_t)nprocs * sizeof(pid_t));
	if (!children) return 0;

	for (int p = 0; p < nprocs; p++) {
		// Reparto balanceado (funciona aunque N no sea múltiplo exacto).
		int row_start = (p * N) / nprocs;
		int row_end = ((p + 1) * N) / nprocs;

		pid_t pid = fork();
		if (pid < 0) {
			// Si falla fork, esperamos los hijos ya creados para evitar zombies.
			for (int i = 0; i < p; i++) waitpid(children[i], NULL, 0);
			free(children);
			return 0;
		}

		if (pid == 0) {
			// Camino del hijo: calcula su bloque y sale inmediatamente.
			// _exit evita ejecutar lógica del padre al terminar.
			matmul_rows(N, A, B, C, row_start, row_end);
			_exit(0);
		}

		// Camino del padre: guarda PID para esperar después.
		children[p] = pid;
	}

	int ok = 1;
	for (int p = 0; p < nprocs; p++) {
		int status = 0;
		// waitpid sincroniza: padre no continúa hasta que cada hijo termine.
		if (waitpid(children[p], &status, 0) < 0) {
			ok = 0;
			continue;
		}
		// Validamos salida normal del hijo.
		if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
			ok = 0;
		}
	}

	free(children);
	return ok;
}

// ============================================================
//  MAIN
// ============================================================

// Flujo principal:
// 1) parsea argumentos
// 2) reserva memoria (A/B normal, C compartida)
// 3) llena datos
// 4) warm-up
// 5) ejecuta 'trials' y reporta tiempos + checksum
int main(int argc, char **argv) {
	int N, nprocs, trials;
	unsigned seed = 123456789u;

	if (argc < 4) { usage(argv[0]); return 1; }
	if (!parse_int(argv[1], &N)) { usage(argv[0]); return 1; }
	if (!parse_int(argv[2], &nprocs)) { usage(argv[0]); return 1; }
	if (!parse_int(argv[3], &trials)) { usage(argv[0]); return 1; }
	if (argc >= 5) seed = (unsigned)strtoul(argv[4], NULL, 10);

	if (nprocs != 2 && nprocs != 4 && nprocs != 8 && nprocs != 16) {
		fprintf(stderr, "procesos debe ser: 2, 4, 8 o 16\n");
		return 1;
	}

	srand(seed);

	int32_t *A = NULL;
	int32_t *B = NULL;
	int32_t *C = NULL;

	if (!allocate_matrices(N, &A, &B)) {
		size_t bytes = (size_t)N * (size_t)N * sizeof(int32_t);
		fprintf(stderr, "Error: memoria insuficiente para N=%d (%.2f MB por matriz)\n",
				N, (double)bytes / (1024.0 * 1024.0));
		return 2;
	}

	C = allocate_shared_matrix(N);
	if (!C) {
		fprintf(stderr, "Error: no se pudo reservar memoria compartida para C\n");
		free(A);
		free(B);
		return 2;
	}

	fill_random_matrices(N, A, B);

	// Warm-up: primera ejecución para estabilizar cachés y páginas.
	// No se reporta en resultados.
	zero_matrix(N, C);
	if (!matmul_parallel_processes(N, nprocs, A, B, C)) {
		fprintf(stderr, "Error creando procesos en warm-up\n");
		free_shared_matrix(N, C);
		free(A);
		free(B);
		return 3;
	}

	for (int t = 1; t <= trials; t++) {
		zero_matrix(N, C);

		// Inicio de medición.
		double wall0 = wall_seconds_now();
		double u0 = 0.0, k0 = 0.0, u1 = 0.0, k1 = 0.0;
		process_cpu_seconds(&u0, &k0);

		if (!matmul_parallel_processes(N, nprocs, A, B, C)) {
			fprintf(stderr, "Error creando procesos en trial %d\n", t);
			free_shared_matrix(N, C);
			free(A);
			free(B);
			return 3;
		}

		process_cpu_seconds(&u1, &k1);
		double wall1 = wall_seconds_now();

		// Checksum para verificar correctitud entre corridas.
		int64_t chk = checksum_matrix(N, C);

		// Métricas finales del trial.
		double wall_s = wall1 - wall0;
		double user_s = u1 - u0;
		double kernel_s = k1 - k0;
		double cpu_total_s = user_s + kernel_s;

		printf("%d %d %d %.6f %.6f %.6f %.6f %lld %u\n",
			   N, nprocs, t, wall_s, user_s, kernel_s, cpu_total_s,
			   (long long)chk, seed);
	}

	free_shared_matrix(N, C);
	free(A);
	free(B);
	return 0;
}
