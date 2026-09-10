#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

#ifndef NUM_RECTANGULOS
#define NUM_RECTANGULOS 1000000000ULL
#endif

/*
 * Funciones disponibles para la suma de Riemann.
 * Se puede agregar otra función incluyendo una nueva opción en este switch.
 */
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

/*
 * Calcula la integral analitica de las funciones del menu. Este valor no
 * participa en la suma: se utiliza unicamente para validar el resultado.
 */
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

/*
 * Algoritmo secuencial: cada iteracion calcula el area de un rectangulo.
 * No se utilizan hilos, OpenMP ni estructuras compartidas paralelas.
 */
static double suma_riemann_secuencial(double limite_a,
                                      double ancho,
                                      uint64_t n,
                                      int opcion)
{
    double suma_areas = 0.0;

    /* Ciclo masivo que se analizara para la futura paralelizacion. */
    for (uint64_t i = 0; i < n; i++) {
        const double x = limite_a + (double)i * ancho;
        const double y = evaluar_funcion(x, opcion);

        suma_areas = suma_areas + y * ancho;
    }

    return suma_areas;
}

int main(void)
{
    int opcion;
    double limite_a;
    double limite_b;

    /* 1. Ingresar la función f(x), el límite a y el límite b. */
    printf("Funciones disponibles:\n");
    printf("  1. f(x) = x^2\n");
    printf("  2. f(x) = x^3\n");
    printf("  3. f(x) = sin(x)\n");
    printf("  4. f(x) = cos(x)\n");
    printf("  5. f(x) = e^(-x^2)\n");
    printf("Seleccione una funcion: ");

    if (scanf("%d", &opcion) != 1 || opcion < 1 || opcion > 5) {
        fprintf(stderr, "Error: la opción de función no es válida.\n");
        return 1;
    }

    printf("Ingrese el limite inferior a: ");
    if (scanf("%lf", &limite_a) != 1) {
        fprintf(stderr, "Error: el limite a no es valido.\n");
        return 1;
    }

    printf("Ingrese el limite superior b: ");
    if (scanf("%lf", &limite_b) != 1) {
        fprintf(stderr, "Error: el limite b no es valido.\n");
        return 1;
    }

    if (!isfinite(limite_a) || !isfinite(limite_b) || limite_a >= limite_b) {
        fprintf(stderr,
                "Error: los limites deben ser números finitos y se debe "
                "cumplir a < b.\n");
        return 1;
    }

    /* 2. n = 10^9. */
    const uint64_t n = NUM_RECTANGULOS;

    /* 3. ancho = (b - a) / n. */
    const double ancho = (limite_b - limite_a) / (double)n;

    /* 4-7. Inicializar, recorrer los rectangulos y obtener el area. */
    const clock_t tiempo_inicio = clock();
    const double area =
        suma_riemann_secuencial(limite_a, ancho, n, opcion);
    const clock_t tiempo_fin = clock();

    /* 8. Imprimir el area y los datos que permiten validarla. */
    const double valor_exacto = integral_exacta(limite_a, limite_b, opcion);
    const double error_absoluto = fabs(area - valor_exacto);
    const double tiempo_segundos =
        (double)(tiempo_fin - tiempo_inicio) / (double)CLOCKS_PER_SEC;

    printf("\n--- Resultado secuencial ---\n");
    printf("Numero de rectangulos : %" PRIu64 "\n", n);
    printf("Ancho de rectangulo   : %.15e\n", ancho);
    printf("Area aproximada       : %.15f\n", area);
    printf("Valor analitico       : %.15f\n", valor_exacto);
    printf("Error absoluto        : %.15e\n", error_absoluto);
    printf("Tiempo secuencial     : %.6f segundos\n", tiempo_segundos);

    return 0;
}
