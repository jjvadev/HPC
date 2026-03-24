#ifndef JACOBI_H
#define JACOBI_H

#include <stddef.h>

#define MAX_WORKERS 32

typedef struct {
    int n;              /* numero de subintervalos, por tanto hay n + 1 nodos en la malla */
    int nsweeps;        /* numero de iteraciones o barridos del metodo de Jacobi */
    int workers;        /* cantidad de hilos o procesos de las versiones paralelas */
    double h;           /* paso de malla: h = 1/n en el intervalo [0,1] */
    double h2;          /* h^2, aparece en la ecuacion discreta de Poisson */
    double *u;          /* aproximacion actual de la solucion */
    double *utmp;       /* aproximacion nueva calculada desde u */
    double *f;          /* termino fuente f(x) evaluado en cada punto de la malla */
} JacobiContext;

double wall_time_seconds(void);
int init_context_heap(JacobiContext *ctx, int n, int nsweeps, int workers);
void free_context_heap(JacobiContext *ctx);
void init_problem(JacobiContext *ctx);
void jacobi_seq(JacobiContext *ctx);
int jacobi_seq_mem(JacobiContext *ctx);
int jacobi_threads(JacobiContext *ctx);
int jacobi_processes(JacobiContext *ctx);

#endif
