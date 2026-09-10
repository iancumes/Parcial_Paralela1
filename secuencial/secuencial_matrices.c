#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N 100
#define M 100
#define P 100
#define Q 100

int matriz_a[N][M];
int matriz_b[P][Q];
int matriz_resultante[N][Q];

int main() {
    int n = N, m = M, p = P, q = Q;
    
    srand(time(NULL));

    if (m != p) {
        printf("Las matrices no se pueden multiplicar (columnas de A deben ser igual a filas de B).\n");
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

    printf("¡Matrices llenadas con exito!\n");

    for (int i = 0; i < n; i++) {          
        for (int j = 0; j < q; j++) {      
            int suma = 0;

            for (int r = 0; r < m; r++) { 
                suma = suma + (matriz_a[i][r] * matriz_b[r][j]);
            }

            matriz_resultante[i][j] = suma;
        }
    }

    for (int fi = 0; fi < n; fi++) {
        for (int fj = 0; fj < q; fj++) {
            printf("%d ", matriz_resultante[fi][fj]);
        }
        printf("\n");
    }

    return 0;
}
