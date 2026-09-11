#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef N
#define N 500
#endif
#ifndef M
#define M 500
#endif
#ifndef P
#define P 500
#endif
#ifndef Q
#define Q 500
#endif

int matriz_a[N][M];
int matriz_b[P][Q];
int matriz_resultante[N][Q];

int main(void) {
    int n = N, m = M, p = P, q = Q;
    int hilos = omp_get_max_threads();
    double inicio, fin, tiempo_total;
    long long checksum = 0;

    srand(42);

    if (m != p) {
        fprintf(stderr, "Las matrices no se pueden multiplicar (columnas de A deben ser igual a filas de B).\n");
        return 1;
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            matriz_a[i][j] = rand() % 10;
        }
    }

    for (int i = 0; i < p; i++) {
        for (int j = 0; j < q; j++) {
            matriz_b[i][j] = rand() % 10;
        }
    }

    // INICIO DE LA MEDICION DE TIEMPO
    inicio = omp_get_wtime();

    #pragma omp parallel for schedule(static)
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < q; j++) {
            int suma = 0;

            for (int r = 0; r < m; r++) {
                suma += matriz_a[i][r] * matriz_b[r][j];
            }

            matriz_resultante[i][j] = suma;
        }
    }

    // FIN DE LA MEDICION DE TIEMPO
    fin = omp_get_wtime();
    tiempo_total = fin - inicio;

    // Checksum para validar contra la version secuencial (fuera de la medicion)
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < q; j++) {
            checksum += matriz_resultante[i][j];
        }
    }

    // n,hilos,tiempo,checksum
    printf("%d,%d,%f,%lld\n", n, hilos, tiempo_total, checksum);

    return 0;
}
