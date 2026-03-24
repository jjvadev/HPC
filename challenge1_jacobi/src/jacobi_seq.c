#include "jacobi.h"

void jacobi_seq(JacobiContext *ctx) {
    int sweep;
    int i;

    /*
     * Discretizacion de la ecuacion de Poisson 1D:
     *
     *     -u''(x) = f(x)
     *
     * Usando diferencias finitas centrales en un punto interior x_i:
     *
     *     -(u[i-1] - 2u[i] + u[i+1]) / h^2 = f[i]
     *
     * Despejando u[i]:
     *
     *     u[i] = 0.5 * (u[i-1] + u[i+1] + h^2 * f[i])
     *
     * El metodo de Jacobi usa esta formula iterativamente:
     * la nueva aproximacion se calcula siempre a partir de la anterior.
     */
    for (sweep = 0; sweep < ctx->nsweeps; ++sweep) {
        if ((sweep & 1) == 0) {
            /*
             * Barrido par:
             *   leemos la aproximacion vieja desde ctx->u
             *   escribimos la nueva aproximacion en ctx->utmp
             *
             * Solo recorremos los puntos interiores 1..n-1.
             * Los puntos 0 y n son frontera y ya estan fijados.
             */
            for (i = 1; i < ctx->n; ++i) {
                /*
                 * Aplicacion directa de la ecuacion discreta de Poisson:
                 *
                 *   nuevo_valor = promedio_de_vecinos + aporte_de_la_fuente
                 *
                 * donde:
                 *   - ctx->u[i - 1] y ctx->u[i + 1] son los vecinos del nodo i
                 *   - ctx->h2 * ctx->f[i] representa el termino fuente escalado
                 *   - 0.5 aparece al despejar 2*u[i]
                 */
                ctx->utmp[i] = 0.5 * (ctx->u[i - 1] + ctx->u[i + 1] + ctx->h2 * ctx->f[i]);
            }
        } else {
            /*
             * Barrido impar:
             * ahora la aproximacion mas reciente esta en utmp,
             * asi que calculamos el siguiente barrido de vuelta sobre u.
             */
            for (i = 1; i < ctx->n; ++i) {
                ctx->u[i] = 0.5 * (ctx->utmp[i - 1] + ctx->utmp[i + 1] + ctx->h2 * ctx->f[i]);
            }
        }
    }

    /*
     * Si el numero total de barridos es impar, la ultima iteracion escribio
     * en utmp. Se copia a u para que el resultado final quede siempre en ctx->u.
     */
    if ((ctx->nsweeps & 1) != 0) {
        for (i = 1; i < ctx->n; ++i) {
            ctx->u[i] = ctx->utmp[i];
        }
    }
}
