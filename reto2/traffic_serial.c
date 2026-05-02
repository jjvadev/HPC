/*
 * ================================================================
 * Cellular Automaton - Flujo de Trafico (VERSION SERIAL)
 * ================================================================
 * Modelo: carretera de N celdas, valores 0/1
 * Reglas:
 *   - Si celda[i]=1 y celda[i+1]=0  -> auto avanza (celda[i]=0)
 *   - Si celda[i]=1 y celda[i+1]=1  -> auto se queda
 *   - Si celda[i]=0 y celda[i-1]=1  -> auto de atras llega
 * Frontera periodica: celda[0]=celda[N], celda[N+1]=celda[1]
 *
 * Medicion de rendimiento: wall time con clock_gettime
 * ================================================================
 * Compilar:
 *   gcc traffic_serial.c -o traffic_serial
 *
 * Uso:
 *   ./traffic_serial <N> <pasos> <densidad>
 *   Ejemplo: ./traffic_serial 5000 1000 0.5
 * ================================================================
 */

#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* ----------------------------------------------------------------
 * Retorna tiempo actual en segundos (alta resolucion)
 * ---------------------------------------------------------------- */
static double wall_time(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* ----------------------------------------------------------------
 * Inicializar carretera con densidad dada
 * ---------------------------------------------------------------- */
static void init_road(int *road, int N, double density) {
    for (int i = 1; i <= N; i++) {
        double r = (double)rand() / ((double)RAND_MAX + 1.0);
        if (r < density){
            road[i] = 1;
        } else {
            road[i] = 0;
        }
    }
    road[0]   = road[N];
    road[N+1] = road[1];
}


/* ----------------------------------------------------------------
 * Contar autos totales
 * ---------------------------------------------------------------- */
static int count_cars(const int *road, int N) {
    int total = 0;
    for (int i = 1; i <= N; i++) {
        total += road[i];
    }
    return total;
}

/* ----------------------------------------------------------------
 * Un paso de tiempo: aplica reglas y retorna autos que se movieron
 reglas:
 * - Si hay carro y adelante está libre, avanza.
 * - Si hay carro y adelante está ocupado, se queda.
 * - Si una celda está vacía y atrás había carro, el carro llega.
 * 
 * retorna el número de autos que se movieron (para calcular velocidad)
 * ---------------------------------------------------------------- */
static int update_road(const int *old, int *new_road, int N) {
    int moved = 0;

    
    for (int i = 1; i <= N; i++) {
        int curr = old[i];
        int right = old[i+1];
        int left = old[i-1];
        if (curr == 1 && right == 0) {
            new_road[i] = 0;  // auto avanza
            moved++;
        } else if (curr == 0 && left == 1) {
            new_road[i] = 1;  // auto llega
        } else {
            new_road[i] = curr; // se queda igual
        }
    }
    
    new_road[0]   = new_road[N];
    new_road[N+1] = new_road[1];
    return moved;
}

/* ----------------------------------------------------------------
 * Validadr parametros de entrada
 * ---------------------------------------------------------------- */

static int validate_params(int N, int pasos, double density) {
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
    return 1;
}

/* ================================================================
 * MAIN
 * ================================================================ */
int main(int argc, char *argv[]) {

    /* --- Parametros --- */
    int    N       = (argc >= 2) ? atoi(argv[1]) : 5000;
    int    pasos   = (argc >= 3) ? atoi(argv[2]) : 1000;
    double density = (argc >= 4) ? atof(argv[3]) : 0.5;
    
    if (!validate_params(N, pasos, density)) {
        fprintf(stderr, "Uso: %s <N> <pasos> <densidad>\n", argv[0]);
        return 1;
    }
    int    warmup  = pasos / 5;   /* 20% de pasos como calentamiento */

    srand(42);   /* semilla fija para reproducibilidad */

    /* --- Reservar memoria --- */
    int *road_a = (int *)malloc((N + 2) * sizeof(int));
    int *road_b = (int *)malloc((N + 2) * sizeof(int));

    if (road_a == NULL || road_b == NULL) {
        fprintf(stderr, "Error: No se pudo reservar memoria\n");
        free(road_a);
        free(road_b);
        return 1;
    }

    /* --- Inicializar --- */
    init_road(road_a, N, density);

    // Contar autos iniciales y densidad real
    int ncars = count_cars(road_a, N);
    double real_density = (double)ncars / N;

    printf("================================================\n");
    printf("  Cellular Automaton - Trafico [SERIAL]\n");
    printf("================================================\n");
    printf("  N              : %d\n", N);
    printf("  Pasos          : %d\n", pasos);
    printf("  Densidad dada  : %.4f\n", density);
    printf("  Autos iniciales: %d\n", ncars);
    printf("  Densidad real  : %.4f\n", real_density);
    printf("  Warmup         : %d pasos\n", warmup);
    printf("------------------------------------------------\n");

    /* ============================================================
     * INICIO MEDICION WALL TIME
     * ============================================================ */
    
    int *old   = road_a;
    int *new_road = road_b;
    
    double suma_vel  = 0.0;
    int    n_medidas = 0;
    
    double t_inicio = wall_time();

    for (int t = 0; t < pasos; t++) {
        int moved = update_road(old, new_road, N);

        /* Intercambio de punteros (evita memcpy O(N) en cada paso) */
        int *tmp = old; 
        old = new_road; 
        new_road = tmp;

        /* Acumular velocidad solo despues del warmup */
        if (t >= warmup) {
            double velocity = (ncars > 0) ? (double)moved / ncars : 0.0;
            suma_vel += velocity;
            n_medidas++;
        }
    }

    double t_fin = wall_time();
    /* ============================================================
     * FIN MEDICION WALL TIME
     * ============================================================ */

    double wall_s        = t_fin - t_inicio;
    double vel_promedio  = (n_medidas > 0) ? suma_vel / n_medidas : 0.0;
    double mcells_per_s  = (double)N * pasos / wall_s / 1.0e6;

    printf("\n  -- RESULTADOS --\n");
    printf("  Wall time          : %.6f s\n", wall_s);
    printf("  Rendimiento        : %.2f MCeldas/s\n", mcells_per_s);
    printf("  Velocidad promedio : %.6f\n", vel_promedio);
    printf("  Carros finales     : %d\n", count_cars(old, N));
    printf("================================================\n");

    printf("\nCSV:\n");
    printf("version,hilos,N,pasos,densidad,densidad_real,tiempo_s,mceldas_s,velocidad\n");
    printf("serial,1,%d,%d,%.4f,%.4f,%.6f,%.2f,%.6f\n",
       N, pasos, density, real_density,
           wall_s, mcells_per_s, vel_promedio);


    free(road_a);
    free(road_b);
    return 0;
}
