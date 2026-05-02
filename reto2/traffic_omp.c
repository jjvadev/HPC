/*
 * ================================================================
 * Cellular Automaton - Flujo de Trafico (VERSION OPENMP)
 * ================================================================
 *
 * Compilar:
 *   gcc -fopenmp -o traffic_openmp traffic_openmp.c
 *
 * Uso:
 *   ./traffic_openmp <N> <pasos> <densidad> <hilos>
 *
 * Ejemplo:
 *   ./traffic_openmp 10000000 1000 0.5 4
 *
 * ================================================================
 */

#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <omp.h>

/* ---------------------------------------------------------------
 * Tiempo de pared en segundos
 * --------------------------------------------------------------- */
static double wall_time(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* ---------------------------------------------------------------
 * Inicializa la carretera con una densidad dada
 * road[1] hasta road[N] son celdas reales.
 * road[0] y road[N+1] son celdas fantasma.
 * --------------------------------------------------------------- */
static void init_road(int *road, int N, double density) {
    for (int i = 1; i <= N; i++) {
        double r = (double)rand() / ((double)RAND_MAX + 1.0);

        if (r < density) {
            road[i] = 1;
        } else {
            road[i] = 0;
        }
    }

    road[0] = road[N];
    road[N + 1] = road[1];
}

/* ---------------------------------------------------------------
 * Cuenta carros en la carretera
 * Versión serial, usada para validación.
 * --------------------------------------------------------------- */
static int count_cars(const int *road, int N) {
    int total = 0;

    for (int i = 1; i <= N; i++) {
        total += road[i];
    }

    return total;
}

/* ---------------------------------------------------------------
 * Actualiza la carretera un paso de tiempo usando OpenMP.
 *
 * Esta versión es paralelizable porque:
 * - cada iteración lee de old[]
 * - cada iteración escribe solamente en new_road[i]
 * - moved se suma con reduction
 * --------------------------------------------------------------- */
static int update_road_openmp(const int *old, int *new_road, int N) {
    int moved = 0;

    #pragma omp parallel for reduction(+:moved) schedule(static)
    for (int i = 1; i <= N; i++) {

        int curr  = old[i];
        int right = old[i + 1];
        int left  = old[i - 1];

        /*
         * Caso 1:
         * Hay carro en i y la celda de adelante está libre.
         * Entonces el carro sale de i.
         */
        if (curr == 1 && right == 0) {
            new_road[i] = 0;
            moved++;
        }

        /*
         * Caso 2:
         * La celda i está vacía y había carro atrás.
         * Entonces llega un carro desde i-1.
         */
        else if (curr == 0 && left == 1) {
            new_road[i] = 1;
        }

        /*
         * Caso 3:
         * Si no ocurre movimiento que afecte a i,
         * la celda conserva su valor actual.
         */
        else {
            new_road[i] = curr;
        }
    }

    /*
     * Frontera periódica.
     * Esto se hace después del parallel for.
     */
    new_road[0] = new_road[N];
    new_road[N + 1] = new_road[1];

    return moved;
}

/* ---------------------------------------------------------------
 * Valida parámetros
 * --------------------------------------------------------------- */
static int validate_params(int N, int pasos, double density, int threads) {
    if (N <= 0) {
        fprintf(stderr, "Error: N debe ser > 0\n");
        return 0;
    }

    if (pasos <= 0) {
        fprintf(stderr, "Error: pasos debe ser > 0\n");
        return 0;
    }

    if (density < 0.0 || density > 1.0) {
        fprintf(stderr, "Error: densidad debe estar entre 0.0 y 1.0\n");
        return 0;
    }

    if (threads <= 0) {
        fprintf(stderr, "Error: hilos debe ser > 0\n");
        return 0;
    }

    return 1;
}

/* ===============================================================
 * MAIN
 * =============================================================== */
int main(int argc, char *argv[]) {

    int N = (argc >= 2) ? atoi(argv[1]) : 5000;
    int pasos = (argc >= 3) ? atoi(argv[2]) : 1000;
    double density = (argc >= 4) ? atof(argv[3]) : 0.5;
    int threads = (argc >= 5) ? atoi(argv[4]) : 2;

    if (!validate_params(N, pasos, density, threads)) {
        fprintf(stderr, "Uso: %s <N> <pasos> <densidad> <hilos>\n", argv[0]);
        return 1;
    }

    omp_set_num_threads(threads);

    int warmup = pasos / 5;

    srand(42);

    int *road_a = (int *)malloc((N + 2) * sizeof(int));
    int *road_b = (int *)malloc((N + 2) * sizeof(int));

    if (road_a == NULL || road_b == NULL) {
        fprintf(stderr, "Error: No se pudo reservar memoria\n");
        free(road_a);
        free(road_b);
        return 1;
    }

    init_road(road_a, N, density);

    int ncars = count_cars(road_a, N);
    double real_density = (double)ncars / N;

    printf("================================================\n");
    printf("  Cellular Automaton - Trafico [OPENMP]\n");
    printf("================================================\n");
    printf("  N              : %d\n", N);
    printf("  Pasos          : %d\n", pasos);
    printf("  Densidad dada  : %.4f\n", density);
    printf("  Autos iniciales: %d\n", ncars);
    printf("  Densidad real  : %.4f\n", real_density);
    printf("  Warmup         : %d pasos\n", warmup);
    printf("  Hilos OpenMP   : %d\n", threads);
    printf("------------------------------------------------\n");

    int *old = road_a;
    int *new_road = road_b;

    double suma_vel = 0.0;
    int n_medidas = 0;

    double t_inicio = wall_time();

    for (int t = 0; t < pasos; t++) {
        int moved = update_road_openmp(old, new_road, N);

        int *tmp = old;
        old = new_road;
        new_road = tmp;

        // /*
        //  * Validación de conservación de carros.
        //  * Para pruebas finales de rendimiento, puedes desactivarla
        //  * porque agrega costo adicional.
        //  */
        // int current_cars = count_cars(old, N);
        // if (current_cars != ncars) {
        //     fprintf(stderr,
        //             "Error en paso %d: el numero de carros cambio. Inicial=%d Actual=%d\n",
        //             t, ncars, current_cars);
        //     free(road_a);
        //     free(road_b);
        //     return 1;
        // }

        if (t >= warmup) {
            double velocity = (ncars > 0) ? (double)moved / ncars : 0.0;
            suma_vel += velocity;
            n_medidas++;
        }
    }

    double t_fin = wall_time();

    double wall_s = t_fin - t_inicio;
    double vel_promedio = (n_medidas > 0) ? suma_vel / n_medidas : 0.0;
    double mcells_per_s = (double)N * pasos / wall_s / 1.0e6;

    printf("\n  -- RESULTADOS --\n");
    printf("  Wall time          : %.6f s\n", wall_s);
    printf("  Rendimiento        : %.2f MCeldas/s\n", mcells_per_s);
    printf("  Velocidad promedio : %.6f\n", vel_promedio);
    printf("  Carros finales     : %d\n", count_cars(old, N));
    printf("================================================\n");

    printf("\nCSV:\n");
    printf("version,hilos,N,pasos,densidad,densidad_real,tiempo_s,mceldas_s,velocidad\n");
    printf("openmp,%d,%d,%d,%.4f,%.4f,%.6f,%.2f,%.6f\n",
           threads, N, pasos, density, real_density,
           wall_s, mcells_per_s, vel_promedio);

    free(road_a);
    free(road_b);

    return 0;
}