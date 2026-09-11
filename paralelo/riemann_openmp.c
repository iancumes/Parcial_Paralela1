#include <inttypes.h>
#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef NUM_RECTANGULOS
#define NUM_RECTANGULOS 1000000000ULL
#endif

// Funciones disponibles: para agregar otra, se anade un caso a este switch
static inline double evaluar_funcion(double x, int opcion)
{
    switch (opcion) {
        case 1:
            return x * x;
        case 2:
            return x * x * x;
        case 3:
            return sin(x);
        case 4:
            return cos(x);
        case 5:
            return exp(-(x * x));
        default:
            return 0.0;
    }
}

// Integral analitica, solo para validar el resultado
static double integral_exacta(double limite_a, double limite_b, int opcion)
{
    switch (opcion) {
        case 1:
            return (pow(limite_b, 3.0) - pow(limite_a, 3.0)) / 3.0;
        case 2:
            return (pow(limite_b, 4.0) - pow(limite_a, 4.0)) / 4.0;
        case 3:
            return cos(limite_a) - cos(limite_b);
        case 4:
            return sin(limite_b) - sin(limite_a);
        case 5: {
            const double raiz_pi_sobre_dos = sqrt(acos(-1.0)) / 2.0;
            return raiz_pi_sobre_dos * (erf(limite_b) - erf(limite_a));
        }
        default:
            return NAN;
    }
}

// reduction(+:) da a cada hilo su suma parcial y las combina al final,
// evitando la condicion de carrera sobre un acumulador compartido
static double suma_riemann_paralela(double limite_a,
                                    double ancho,
                                    uint64_t n,
                                    int opcion)
{
    double suma_areas = 0.0;

    // Ciclo masivo, repartido entre los hilos
    #pragma omp parallel for reduction(+:suma_areas) schedule(static)
    for (uint64_t i = 0; i < n; i++) {
        const double x = limite_a + (double)i * ancho;
        const double y = evaluar_funcion(x, opcion);

        suma_areas = suma_areas + y * ancho;
    }

    return suma_areas;
}

static void uso(const char *programa)
{
    fprintf(stderr, "Uso: %s <funcion> <a> <b>\n", programa);
    fprintf(stderr, "  funcion: 1=x^2  2=x^3  3=sin(x)  4=cos(x)  5=e^(-x^2)\n");
    fprintf(stderr, "  a, b   : limites de integracion, con a < b\n");
}

int main(int argc, char *argv[])
{
    if (argc != 4) {
        uso(argv[0]);
        return 1;
    }

    // La funcion y los limites llegan como argumentos, no por teclado:
    // el barrido de metricas no puede alimentar una entrada interactiva
    const int hilos = omp_get_max_threads();
    const int opcion = atoi(argv[1]);
    const double limite_a = atof(argv[2]);
    const double limite_b = atof(argv[3]);

    if (opcion < 1 || opcion > 5) {
        fprintf(stderr, "Error: la opcion de funcion no es valida.\n");
        uso(argv[0]);
        return 1;
    }

    if (!isfinite(limite_a) || !isfinite(limite_b) || limite_a >= limite_b) {
        fprintf(stderr,
                "Error: los limites deben ser numeros finitos y se debe "
                "cumplir a < b.\n");
        return 1;
    }

    // 10^9 por defecto, ajustable con -DNUM_RECTANGULOS
    const uint64_t n = NUM_RECTANGULOS;

    // ancho = (b - a) / n
    const double ancho = (limite_b - limite_a) / (double)n;

    // INICIO DE LA MEDICION DE TIEMPO
    // omp_get_wtime y no clock(): clock() suma el tiempo de todos los hilos
    const double inicio = omp_get_wtime();
    const double area =
        suma_riemann_paralela(limite_a, ancho, n, opcion);
    const double fin = omp_get_wtime();
    // FIN DE LA MEDICION DE TIEMPO

    // La suma flotante no es asociativa: el paralelo da un area ligeramente
    // distinta, por eso se compara con tolerancia y no por igualdad
    const double valor_exacto = integral_exacta(limite_a, limite_b, opcion);
    const double error_absoluto = fabs(area - valor_exacto);

    // n,hilos,funcion,a,b,tiempo,area,error
    printf("%" PRIu64 ",%d,%d,%g,%g,%f,%.15f,%.15e\n",
           n, hilos, opcion, limite_a, limite_b, fin - inicio, area, error_absoluto);

    return 0;
}
