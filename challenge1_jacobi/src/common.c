#include "jacobi.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double rhs_value(double x) {
    /*
     * Termino fuente del problema:
     *
     *     -u''(x) = f(x),   x in (0,1)
     *
     * En esta implementacion se usa f(x) = x.
     * Si el enunciado pide otra funcion, este es el lugar para cambiarla.
     */
    return x;
}

double wall_time_seconds(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}

int init_context_heap(JacobiContext *ctx, int n, int nsweeps, int workers) {
    size_t bytes;

    if (ctx == NULL || n <= 1 || nsweeps <= 0 || workers <= 0 || workers > MAX_WORKERS) {
        return -1;
    }

    memset(ctx, 0, sizeof(*ctx));
    ctx->n = n;
    ctx->nsweeps = nsweeps;
    ctx->workers = workers;
    /*
     * Discretizacion uniforme del intervalo [0,1]:
     *
     *     x_i = i h,   con h = 1/n,   i = 0,1,...,n
     *
     * Esto produce n+1 nodos y n-1 puntos interiores donde realmente
     * se aplica la ecuacion discreta.
     */
    ctx->h = 1.0 / (double)n;
    ctx->h2 = ctx->h * ctx->h;

    bytes = (size_t)(n + 1) * sizeof(double);
    /*
     * Jacobi necesita dos arreglos de solucion:
     *   - u    : valores de la iteracion k
     *   - utmp : valores de la iteracion k+1
     *
     * Esto evita sobrescribir un valor viejo que todavia se necesita
     * para calcular otros nodos del mismo barrido.
     */
    ctx->u = (double *)malloc(bytes);
    ctx->utmp = (double *)malloc(bytes);
    ctx->f = (double *)malloc(bytes);

    if (ctx->u == NULL || ctx->utmp == NULL || ctx->f == NULL) {
        free_context_heap(ctx);
        return -1;
    }

    init_problem(ctx);
    return 0;
}

void init_problem(JacobiContext *ctx) {
    int i;
    double x;

    /*
     * Condiciones de frontera de Dirichlet:
     *
     *     u(0) = 0
     *     u(1) = 0
     *
     * En la malla esto corresponde a fijar los extremos del vector.
     * Esos nodos no se actualizan en Jacobi; permanecen constantes.
     */
    ctx->u[0] = 0.0;
    ctx->u[ctx->n] = 0.0;
    ctx->utmp[0] = 0.0;
    ctx->utmp[ctx->n] = 0.0;

    /* Aproximacion inicial: se comienza en cero en todos los puntos interiores. */
    for (i = 1; i < ctx->n; ++i) {
        ctx->u[i] = 0.0;
        ctx->utmp[i] = 0.0;
    }

    /*
     * Evaluacion del termino fuente f(x) en cada nodo x_i.
     * Esto construye el lado derecho del problema discreto.
     */
    for (i = 0; i <= ctx->n; ++i) {
        x = (double)i * ctx->h;
        ctx->f[i] = rhs_value(x);
    }
}

void free_context_heap(JacobiContext *ctx) {
    if (ctx == NULL) {
        return;
    }

    free(ctx->u);
    free(ctx->utmp);
    free(ctx->f);

    ctx->u = NULL;
    ctx->utmp = NULL;
    ctx->f = NULL;
}
