#include <stdlib.h>
#include <stdint.h>

/*
  Genera un número pseudoaleatorio de 32 bits con signo, usando rand().

  El rango de salida es aproximadamente [-1e9, +1e9], lo que ayuda a evitar
  desbordamientos en la multiplicación de enteros de 32 bits.

  La función rand() típicamente devuelve un entero entre 0 y RAND_MAX (al menos
  32767). Para obtener un número de 32 bits, se combinan varias llamadas a
  rand().
*/


static int32_t rand_i32(void) {
  uint32_t r = 0;
  r ^= (uint32_t)(rand() & 0x7fff);
  r <<= 15;
  r ^= (uint32_t)(rand() & 0x7fff);
  r <<= 1;
  r ^= (uint32_t)(rand() & 0x0001);
  // Ajustar el rango a [-1e9, +1e9]
  return (int32_t)(r) - (int32_t)0x3fffffff;
}

/*
  Para matrices de tamaño N x N, se necesitan N*N elementos. Cada elemento es un
  int32_t (4 bytes), por lo que cada matriz ocupa N*N*4 bytes.

  Para N=1000, cada matriz ocupa aproximadamente 3.8 MB, lo que es razonable.
  Para N=50000, cada matriz ocuparía aproximadamente 9.3 GB, lo que puede ser
  demasiado grande para la mayoría de los sistemas.

  La función allocate_matrices intenta asignar memoria para las tres matrices A,
  B y C. Si alguna asignación falla, libera cualquier memoria ya asignada y
  devuelve un error.
*/

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

/*

*/
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