# Contexto y datos de los problemas seleccionados

El equipo de RDI Solutions seleccionó los problemas de integración numérica mediante suma de Riemann y multiplicación de matrices densas. Ambos requieren una cantidad considerable de operaciones, por lo que permiten establecer una línea base secuencial y medir posteriormente el impacto de una implementación paralela.

## Problema 2: Integración numérica mediante suma de Riemann

El objetivo es aproximar el área bajo una función compleja \(f(x)\) dentro del intervalo \([a,b]\). Para lograr una aproximación de alta precisión, el intervalo se divide en \(n = 10^9\) rectángulos muy pequeños. El área aproximada se calcula sumando el área de cada rectángulo:

\[
\text{Área} \approx \sum_{i=0}^{n-1} f(a + i\Delta x)\Delta x,
\qquad
\Delta x = \frac{b-a}{n}.
\]

La propuesta secuencial recorre los \(10^9\) subintervalos uno por uno. En cada iteración calcula la posición \(x_i\), evalúa la función \(f(x_i)\) y agrega el área del rectángulo a un acumulador. Al finalizar, el acumulador representa la aproximación del área total bajo la curva.

Los datos de prueba están definidos por la función a integrar, los límites \(a\) y \(b\), y el número de subdivisiones. Se utilizarán \(10^9\) rectángulos, tal como indica el problema, porque esta cantidad genera una carga computacional suficientemente grande para obtener mediciones de tiempo significativas. No es necesario almacenar los rectángulos ni los valores intermedios: cada posición y su contribución se calculan directamente durante la iteración. Por ello, el algoritmo mantiene un consumo de memoria constante, usando principalmente variables numéricas de punto flotante para \(\Delta x\), la posición actual y el acumulador.

Para validar los resultados, se ejecutará la versión secuencial como referencia. Los resultados posteriores deberán conservar la misma aproximación dentro de una tolerancia numérica pequeña, ya que los cálculos con punto flotante pueden variar levemente según el orden de las operaciones.

## Problema 3: Multiplicación de matrices densas

El objetivo es calcular la matriz resultante \(C\) a partir de dos matrices cuadradas densas \(A\) y \(B\):

\[
C = A \times B.
\]

Cada celda de la matriz resultante se calcula mediante el producto punto de una fila de \(A\) y una columna de \(B\):

\[
C_{ij} = \sum_{k=0}^{n-1} A_{ik}B_{kj}.
\]

La propuesta secuencial utiliza tres ciclos anidados. Los dos ciclos externos recorren las posiciones \((i,j)\) de la matriz resultado, mientras que el ciclo interno recorre \(k\) para acumular los productos necesarios para calcular cada elemento \(C_{ij}\). El costo computacional aproximado es \(O(n^3)\), por lo que el tiempo de ejecución aumenta rápidamente al incrementar la dimensión de las matrices.

Aunque el enunciado describe matrices de un millón por un millón de elementos, este tamaño no es viable en una computadora convencional. Una matriz de \(10^6 \times 10^6\) con elementos de tipo `double` requeriría aproximadamente 8 TB de memoria; almacenar simultáneamente \(A\), \(B\) y \(C\) requeriría alrededor de 24 TB, sin considerar memoria adicional. Por esta razón, se utilizarán matrices cuadradas de tamaño escalable y compatible con el hardware disponible, comenzando con tamaños como 500 x 500, 1000 x 1000 o mayores si la memoria y el tiempo de ejecución lo permiten. Esto permite mantener una carga de trabajo representativa y repetir las mediciones de manera confiable.

Las matrices se generarán con valores numéricos controlados o aleatorios y se almacenarán en arreglos contiguos en memoria. Esta representación permite acceder a los elementos mediante índices y favorece el aprovechamiento de la caché. La matriz \(C\) se inicializa antes de realizar los cálculos para almacenar el resultado de cada producto punto.

Para validar la implementación, la matriz resultante obtenida en futuras ejecuciones deberá compararse con la matriz producida por la versión secuencial. Cada elemento correspondiente de ambas matrices debe coincidir o diferir únicamente dentro de una tolerancia pequeña de punto flotante.

## Datos de prueba utilizados en las mediciones

Las descripciones anteriores corresponden al planteamiento original. Al pasar a la medición fue necesario fijar valores concretos, que se detallan a continuación.

Para la multiplicación de matrices se emplearon matrices cuadradas de \(500 \times 500\), \(1000 \times 1000\), \(1500 \times 1500\) y \(2000 \times 2000\). El límite superior lo impone el tiempo de ejecución y no la memoria: con elementos de tipo `int`, las tres matrices ocupan 48 MB en el caso más grande, mientras que el costo \(O(n^3)\) hace que una sola corrida secuencial supere los cinco segundos. El tamaño \(500 \times 500\) se conserva únicamente como referencia de carga pequeña, ya que su tiempo de cómputo es tan breve que el costo de crear el equipo de hilos alcanza a ser apreciable frente al trabajo útil. Las matrices se almacenan en arreglos bidimensionales estáticos de memoria contigua y se llenan con valores enteros pseudoaleatorios en el rango \([0, 9]\), generados con una semilla fija para que la versión secuencial y la paralela operen exactamente sobre los mismos datos.

Para la suma de Riemann se utilizaron \(10^8\), \(5 \times 10^8\) y \(10^9\) rectángulos, conservando el valor de \(10^9\) que indica el enunciado e incorporando dos tamaños menores para observar cómo varía el rendimiento con la carga. Se integraron dos funciones de costo distinto sobre el intervalo \([0, 1]\): \(f(x) = x^2\), que consiste en una sola multiplicación por iteración, y \(f(x) = \sin x\), que requiere una llamada a la biblioteca matemática y resulta aproximadamente ocho veces más costosa. Esta pareja permite distinguir los efectos atribuibles al paralelismo de aquellos que dependen de la cantidad de cómputo por iteración. Tal como se anticipó, el algoritmo no almacena los rectángulos y su consumo de memoria permanece constante.

La validación se resuelve de forma distinta en cada problema. En la multiplicación de matrices, ambas versiones calculan la suma de todos los elementos de la matriz resultante, y como se trata de aritmética entera exacta, los valores deben coincidir dígito por dígito. En la suma de Riemann esa exigencia no es aplicable: la suma en punto flotante no es asociativa y la reducción paralela acumula los términos en un orden distinto, de modo que la comparación se realiza con una tolerancia relativa de \(10^{-9}\) contra el valor secuencial, además de contrastar ambos resultados con la integral analítica de la función.

---

# Estrategia de paralelización

Ambos problemas se paralelizaron con OpenMP sobre el ciclo más externo que admite división independiente, procurando alterar lo menos posible la estructura del algoritmo secuencial. Esta decisión responde a un criterio de comparabilidad: si las dos versiones difirieran en algo más que la directiva, las diferencias de tiempo ya no podrían atribuirse únicamente a la paralelización.

## Multiplicación de matrices

La directiva empleada es la siguiente:

```c
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
```

Se paraleliza el ciclo sobre \(i\), es decir, sobre las filas de la matriz resultante. Cada fila de \(C\) depende de una fila de \(A\) y de la totalidad de \(B\), pero ambas se leen sin modificarse, y cada iteración escribe exclusivamente en las posiciones \(C_{ij}\) de su propia fila. En consecuencia, **no existe condición de carrera**: los hilos no comparten ninguna posición de escritura. No fue necesario emplear cláusulas `critical`, `atomic` ni `reduction`, cuyo costo de sincronización habría sido considerable dentro de un ciclo que se ejecuta \(n^3\) veces.

La variable acumuladora `suma` se declara dentro del ciclo, por lo que OpenMP la trata como privada de cada hilo de manera automática. Haberla declarado fuera habría provocado que todos los hilos compartieran el mismo acumulador, con resultados incorrectos difíciles de detectar.

Respecto al balanceo de carga se utilizó `schedule(static)`. La justificación es que el trabajo por iteración es **uniforme y conocido de antemano**: toda fila de \(C\) requiere exactamente \(q \times m\) multiplicaciones, sin ramificaciones ni caminos de ejecución variables. Bajo esas condiciones, la planificación estática reparte el trabajo en bloques contiguos una sola vez, antes de iniciar el ciclo, y no incurre en el costo de coordinación que exigirían `dynamic` o `guided`. Un reparto dinámico solo resultaría ventajoso si algunas iteraciones fueran sistemáticamente más lentas que otras, lo cual no ocurre en este algoritmo. La asignación de bloques contiguos presenta además la ventaja de que cada hilo recorre filas de \(A\) vecinas en memoria, lo que favorece la localidad de caché.

## Suma de Riemann

La directiva empleada es la siguiente:

```c
#pragma omp parallel for reduction(+:suma_areas) schedule(static)
for (uint64_t i = 0; i < n; i++) {
    const double x = limite_a + (double)i * ancho;
    const double y = evaluar_funcion(x, opcion);
    suma_areas = suma_areas + y * ancho;
}
```

Este caso sí presenta una condición de carrera evidente: todos los hilos incrementan el mismo acumulador `suma_areas`. La operación `suma_areas = suma_areas + ...` no es atómica, ya que se compone de una lectura, una suma y una escritura; si dos hilos la ejecutan de manera simultánea, uno puede sobrescribir el resultado del otro y la contribución se pierde. El error resultante no sería determinista y variaría entre ejecuciones.

La solución adoptada es la cláusula **`reduction(+:suma_areas)`**, que otorga a cada hilo una copia privada del acumulador, inicializada en cero, y al finalizar el ciclo combina todas las copias mediante el operador indicado. Se prefirió sobre las alternativas disponibles por razones de rendimiento: `critical` o `atomic` habrían serializado la escritura en cada una de las \(10^9\) iteraciones, anulando en la práctica cualquier beneficio del paralelismo.

Un aspecto relevante es que la posición \(x_i\) se calcula como \(a + i\Delta x\) a partir del índice del ciclo, y no mediante un acumulador que se incremente en cada paso. Esta formulación elimina la dependencia entre iteraciones y es lo que permite que el ciclo sea paralelizable; una versión que arrastrara \(x\) de una iteración a la siguiente habría requerido reestructurarse antes de poder repartirse entre hilos.

También en este caso se utilizó `schedule(static)`, por el mismo motivo que en el problema anterior: el trabajo por iteración es idéntico en todas ellas, pues cada una evalúa la misma función sobre un punto distinto. No existe desbalance que corregir y, por lo tanto, tampoco justificación para asumir el costo de una planificación dinámica.

## Una consecuencia no evidente de las directivas

Durante la medición se observó que la directiva no solo distribuye el trabajo, sino que también modifica las optimizaciones que el compilador puede aplicar, y lo hace en sentidos opuestos en cada problema.

En la multiplicación de matrices, el `#pragma` **inhibe** la vectorización SIMD que `gcc` aplica al ciclo secuencial bajo `-O2`. La versión paralela ejecutada con un solo hilo resulta entre 1.7 y 2.5 veces más lenta que la secuencial, y se comprobó que compilar la versión secuencial con `-fno-tree-vectorize` reproduce ese mismo tiempo.

En la suma de Riemann ocurre lo contrario. La cláusula `reduction` autoriza al compilador a reasociar la suma, operación que de otro modo tendría prohibida por la no asociatividad de la aritmética de punto flotante, y ello **habilita** una vectorización que la versión secuencial no puede aprovechar. Con \(f(x) = x^2\) la versión paralela de un solo hilo resulta aproximadamente un 25 % más rápida que la secuencial. Con \(f(x) = \sin x\), en cambio, ambas coinciden, ya que la llamada a la biblioteca matemática no es vectorizable y el permiso de reasociación no produce ningún efecto.

Por esta razón, la sección de resultados reporta **dos medidas de speedup** en lugar de una: \(S_{sec} = T_{sec} / T_{par}(p)\), que corresponde a la definición formal frente al mejor algoritmo secuencial disponible, y \(S_{omp} = T_{par}(1) / T_{par}(p)\), que aísla la escalabilidad atribuible exclusivamente a OpenMP. La diferencia entre ambas curvas cuantifica el efecto de la vectorización.

---

# Resultados y métricas

## Metodología de medición

Las mediciones se obtuvieron mediante un script de barrido que compila ambas versiones de cada problema con banderas idénticas (`-O2 -fopenmp -Wall`), recorre todas las combinaciones de tamaño y número de hilos, y valida en cada ejecución que la versión paralela produzca el mismo resultado que la secuencial. El procedimiento completo y su documentación se encuentran en `scripts/`.

Se adoptaron tres decisiones metodológicas que conviene explicitar:

**Cada configuración se midió cinco veces y se conservó el tiempo mínimo.** Los tiempos varían cerca de un 25 % entre ejecuciones idénticas por efecto del turbo del procesador y de la planificación del sistema operativo; el mínimo constituye la estimación menos contaminada por ruido ajeno al programa.

**Las repeticiones se intercalan.** El ciclo externo del barrido corresponde a la repetición y el interno recorre todas las configuraciones. Si se midieran las cinco repeticiones de una misma configuración de forma consecutiva, el orden del barrido quedaría correlacionado con la temperatura del procesador y las últimas configuraciones aparecerían penalizadas por limitación térmica. Esta consideración no es teórica: una medición preliminar realizada sin intercalar, con el equipo previamente caliente, arrojó un speedup de 2.50x donde la medición correcta reporta 6.83x.

**El tiempo se mide con `omp_get_wtime()`.** La función `clock()` de la biblioteca estándar acumula el tiempo de CPU de todos los hilos, de modo que en una versión paralela informaría un valor varias veces superior al tiempo real transcurrido. Utilizarla habría producido speedups aparentemente inferiores a la unidad sin generar ningún mensaje de error.

---

## Integrante: Ricardo Arturo Godínez Sánchez

**Equipo de pruebas:** AMD Ryzen 7 5700U, 8 núcleos físicos y 16 hilos lógicos (SMT), compilador GCC 16.2.1 sobre Linux.

### Multiplicación de matrices

| \(n\) | Hilos | \(T_{sec}\) (s) | \(T_{par}\) (s) | \(S_{sec}\) | \(S_{omp}\) | \(E_{omp}\) |
|---|---|---|---|---|---|---|
| 500 | 1 | 0.0524 | 0.1117 | 0.47x | 1.00x | 100% |
| 500 | 2 | 0.0524 | 0.0567 | 0.93x | 1.97x | 99% |
| 500 | 4 | 0.0524 | 0.0292 | 1.80x | 3.83x | 96% |
| 500 | 8 | 0.0524 | 0.0156 | 3.35x | 7.14x | 89% |
| 500 | 16 | 0.0524 | 0.0189 | 2.78x | 5.92x | 37% |
| 1000 | 1 | 0.4882 | 1.2393 | 0.39x | 1.00x | 100% |
| 1000 | 2 | 0.4882 | 0.7243 | 0.67x | 1.71x | 86% |
| 1000 | 4 | 0.4882 | 0.3661 | 1.33x | 3.38x | 85% |
| 1000 | 8 | 0.4882 | 0.1799 | 2.71x | 6.89x | 86% |
| 1000 | 16 | 0.4882 | 0.1502 | 3.25x | 8.25x | 52% |
| 1500 | 1 | 3.8075 | 6.5149 | 0.58x | 1.00x | 100% |
| 1500 | 2 | 3.8075 | 3.2838 | 1.16x | 1.98x | 99% |
| 1500 | 4 | 3.8075 | 1.5994 | 2.38x | 4.07x | 102% |
| 1500 | 8 | 3.8075 | 0.7615 | 5.00x | 8.55x | 107% |
| 1500 | 16 | 3.8075 | 0.5572 | 6.83x | 11.69x | 73% |
| 2000 | 1 | 4.9936 | 8.8885 | 0.56x | 1.00x | 100% |
| 2000 | 2 | 4.9936 | 5.4846 | 0.91x | 1.62x | 81% |
| 2000 | 4 | 4.9936 | 2.7930 | 1.79x | 3.18x | 80% |
| 2000 | 8 | 4.9936 | 1.5513 | 3.22x | 5.73x | 72% |
| 2000 | 16 | 4.9936 | 1.2777 | 3.91x | 6.96x | 43% |

![Speedup de matrices](../img_ricardo/matrices_speedup_vs_hilos.png)

![Eficiencia de matrices](../img_ricardo/matrices_eficiencia_vs_hilos.png)

![Tiempo de matrices según hilos](../img_ricardo/matrices_tiempo_vs_hilos.png)

![Tiempo de matrices según tamaño](../img_ricardo/matrices_tiempo_vs_tamano.png)

### Suma de Riemann

| \(f(x)\) | Rectángulos | Hilos | \(T_{sec}\) (s) | \(T_{par}\) (s) | \(S_{sec}\) | \(S_{omp}\) | \(E_{omp}\) |
|---|---|---|---|---|---|---|---|
| \(x^2\) | 100,000,000 | 1 | 0.1098 | 0.0810 | 1.36x | 1.00x | 100% |
| \(x^2\) | 100,000,000 | 2 | 0.1098 | 0.0410 | 2.68x | 1.98x | 99% |
| \(x^2\) | 100,000,000 | 4 | 0.1098 | 0.0225 | 4.87x | 3.59x | 90% |
| \(x^2\) | 100,000,000 | 8 | 0.1098 | 0.0170 | 6.45x | 4.76x | 59% |
| \(x^2\) | 100,000,000 | 16 | 0.1098 | 0.0111 | 9.90x | 7.30x | 46% |
| \(x^2\) | 500,000,000 | 1 | 0.5063 | 0.3970 | 1.28x | 1.00x | 100% |
| \(x^2\) | 500,000,000 | 2 | 0.5063 | 0.2052 | 2.47x | 1.93x | 97% |
| \(x^2\) | 500,000,000 | 4 | 0.5063 | 0.1016 | 4.99x | 3.91x | 98% |
| \(x^2\) | 500,000,000 | 8 | 0.5063 | 0.0754 | 6.72x | 5.27x | 66% |
| \(x^2\) | 500,000,000 | 16 | 0.5063 | 0.0444 | 11.40x | 8.94x | 56% |
| \(x^2\) | 1,000,000,000 | 1 | 1.0525 | 0.7700 | 1.37x | 1.00x | 100% |
| \(x^2\) | 1,000,000,000 | 2 | 1.0525 | 0.3943 | 2.67x | 1.95x | 98% |
| \(x^2\) | 1,000,000,000 | 4 | 1.0525 | 0.2004 | 5.25x | 3.84x | 96% |
| \(x^2\) | 1,000,000,000 | 8 | 1.0525 | 0.1118 | 9.41x | 6.89x | 86% |
| \(x^2\) | 1,000,000,000 | 16 | 1.0525 | 0.0885 | 11.89x | 8.70x | 54% |
| \(\sin x\) | 100,000,000 | 1 | 0.7994 | 0.7921 | 1.01x | 1.00x | 100% |
| \(\sin x\) | 100,000,000 | 2 | 0.7994 | 0.4141 | 1.93x | 1.91x | 96% |
| \(\sin x\) | 100,000,000 | 4 | 0.7994 | 0.2088 | 3.83x | 3.79x | 95% |
| \(\sin x\) | 100,000,000 | 8 | 0.7994 | 0.1270 | 6.30x | 6.24x | 78% |
| \(\sin x\) | 100,000,000 | 16 | 0.7994 | 0.1168 | 6.85x | 6.78x | 42% |
| \(\sin x\) | 500,000,000 | 1 | 3.9933 | 3.9427 | 1.01x | 1.00x | 100% |
| \(\sin x\) | 500,000,000 | 2 | 3.9933 | 2.1479 | 1.86x | 1.84x | 92% |
| \(\sin x\) | 500,000,000 | 4 | 3.9933 | 1.1094 | 3.60x | 3.55x | 89% |
| \(\sin x\) | 500,000,000 | 8 | 3.9933 | 0.6317 | 6.32x | 6.24x | 78% |
| \(\sin x\) | 500,000,000 | 16 | 3.9933 | 0.5526 | 7.23x | 7.13x | 45% |
| \(\sin x\) | 1,000,000,000 | 1 | 8.2302 | 8.0664 | 1.02x | 1.00x | 100% |
| \(\sin x\) | 1,000,000,000 | 2 | 8.2302 | 4.3554 | 1.89x | 1.85x | 93% |
| \(\sin x\) | 1,000,000,000 | 4 | 8.2302 | 2.3029 | 3.57x | 3.50x | 88% |
| \(\sin x\) | 1,000,000,000 | 8 | 8.2302 | 1.3583 | 6.06x | 5.94x | 74% |
| \(\sin x\) | 1,000,000,000 | 16 | 8.2302 | 1.1935 | 6.90x | 6.76x | 42% |

![Speedup de Riemann](../img_ricardo/riemann_speedup_vs_hilos.png)

![Eficiencia de Riemann](../img_ricardo/riemann_eficiencia_vs_hilos.png)

![Tiempo de Riemann según hilos](../img_ricardo/riemann_tiempo_vs_hilos.png)

![Tiempo de Riemann según rectángulos](../img_ricardo/riemann_tiempo_vs_tamano.png)

### Evidencia de ejecución

Resumen emitido por el script al finalizar el barrido:

```
MATRICES, con el maximo de hilos:
  n=500                  speedup vs sec  2.78x   vs par-1hilo  5.92x   eficiencia  37%   |  t_par(1)/t_sec = 2.13
  n=1000                 speedup vs sec  3.25x   vs par-1hilo  8.25x   eficiencia  52%   |  t_par(1)/t_sec = 2.54
  n=1500                 speedup vs sec  6.83x   vs par-1hilo 11.69x   eficiencia  73%   |  t_par(1)/t_sec = 1.71
  n=2000                 speedup vs sec  3.91x   vs par-1hilo  6.96x   eficiencia  43%   |  t_par(1)/t_sec = 1.78

RIEMANN, con el maximo de hilos:
  funcion=1, n=100000000  speedup vs sec  9.90x   vs par-1hilo  7.30x   eficiencia  46%   |  t_par(1)/t_sec = 0.74
  funcion=1, n=500000000  speedup vs sec 11.40x   vs par-1hilo  8.94x   eficiencia  56%   |  t_par(1)/t_sec = 0.78
  funcion=1, n=1000000000 speedup vs sec 11.89x   vs par-1hilo  8.70x   eficiencia  54%   |  t_par(1)/t_sec = 0.73
  funcion=3, n=100000000  speedup vs sec  6.85x   vs par-1hilo  6.78x   eficiencia  42%   |  t_par(1)/t_sec = 0.99
  funcion=3, n=500000000  speedup vs sec  7.23x   vs par-1hilo  7.13x   eficiencia  45%   |  t_par(1)/t_sec = 0.99
  funcion=3, n=1000000000 speedup vs sec  6.90x   vs par-1hilo  6.76x   eficiencia  42%   |  t_par(1)/t_sec = 0.98
```

Las 300 ejecuciones individuales quedaron registradas en `resultados_ricardo/metricas_crudas_matrices.csv` y `resultados_ricardo/metricas_crudas_riemann.csv`, con el resultado de validación de cada una.


### Análisis

El resultado más consistente es que **la eficiencia se desploma al superar los 8 hilos**, cifra que coincide exactamente con el número de núcleos físicos del procesador. En la multiplicación de matrices de \(1500 \times 1500\) la eficiencia pasa de 107 % con 8 hilos a 73 % con 16; en la suma de Riemann con \(10^9\) rectángulos, de 86 % a 54 %. El comportamiento se repite en los dos problemas, en todos los tamaños y con ambas funciones, lo que indica que se trata de una propiedad del hardware y no del algoritmo. La explicación es que los ocho hilos adicionales son lógicos y no físicos: el SMT resulta provechoso cuando un hilo permanece detenido esperando memoria y otro puede ocupar las unidades de ejecución libres, situación que no se presenta en estos ciclos, densos en operaciones aritméticas, donde ambos hilos lógicos compiten por las mismas unidades.

En cuanto al tamaño del problema, el speedup mejora conforme aumenta la carga, hasta cierto punto. El costo de crear y sincronizar el equipo de hilos es aproximadamente constante, de modo que cuanto mayor sea el trabajo asignado a cada hilo, mejor se amortiza. El caso de matrices de \(500 \times 500\) lo ilustra con claridad: con 16 hilos el tiempo absoluto (0.0189 s) resulta superior al obtenido con 8 (0.0156 s), es decir, agregar hilos empeora el desempeño. Existe por tanto un tamaño mínimo por debajo del cual paralelizar no compensa.

Se observan eficiencias superiores al 100 %, o speedup superlineal, en las matrices de \(1500 \times 1500\) con 4 y 8 hilos. No se trata de un error de medición sino de un efecto de caché: al repartir las filas, cada hilo opera sobre un bloque de datos que sí cabe en su caché privada, mientras que un hilo único recorre la matriz completa y desaloja continuamente su contenido. La suma de Riemann no exhibe este fenómeno, lo cual es coherente, ya que no manipula ningún arreglo que pueda repartirse de esa manera.

El caso de \(2000 \times 2000\) se aparta de la tendencia, con una eficiencia de 72 % frente al 107 % obtenido con \(1500 \times 1500\). La causa se verificó midiendo tamaños vecinos: el ciclo interno recorre `matriz_b[r][j]` por columnas, con un salto de \(n \times 4\) bytes entre accesos consecutivos, y cuando ese salto resulta múltiplo de potencias de dos grandes, las filas de una misma columna se asignan al mismo conjunto de caché y se expulsan entre sí. El efecto es pronunciado: con \(n = 2048\) el tiempo secuencial alcanza 19.3 s, frente a los 4.3 s que predice el crecimiento \(O(n^3)\). Se trata de una limitación del patrón de acceso a memoria y no del esquema de paralelización.

Finalmente, la comparación entre ambos problemas resulta ilustrativa. La suma de Riemann alcanza speedups superiores frente al secuencial —hasta 11.89x con \(f(x) = x^2\)— pero ello se debe en parte a la vectorización adicional que habilita la cláusula `reduction`. Medida en términos de escalabilidad estricta, la multiplicación de matrices escala mejor (107 % de eficiencia con 8 hilos frente a 86 %), aunque ese margen incluye el beneficio de caché descrito anteriormente. Ambas cifras son legítimas siempre que se declare qué está midiendo cada una.

---

## Integrante: Ian Rodrigo Cumes Valdez

**Equipo de pruebas:** _(pendiente: modelo de procesador, núcleos físicos, hilos lógicos, compilador y sistema operativo)_

Para generar estos resultados:

```sh
./scripts/benchmark.sh --etiqueta ian
```

### Multiplicación de matrices

> **Pendiente:** tabla de tiempos, speedup y eficiencia, tomada de `resultados_ian/metricas_matrices.csv`.

> **Pendiente:** insertar las figuras de `img_ian/matrices_*.png`.

### Suma de Riemann

> **Pendiente:** tabla de tiempos, speedup y eficiencia, tomada de `resultados_ian/metricas_riemann.csv`.

> **Pendiente:** insertar las figuras de `img_ian/riemann_*.png`.

### Evidencia de ejecución

> **Pendiente:** captura de pantalla o video de la ejecución del barrido.

### Análisis

> **Pendiente:** comentar en qué número de hilos cae la eficiencia y si coincide con los núcleos físicos del equipo.

---

## Integrante: Diego José López Campos

**Equipo de pruebas:** _(pendiente: modelo de procesador, núcleos físicos, hilos lógicos, compilador y sistema operativo)_

Para generar estos resultados:

```sh
./scripts/benchmark.sh --etiqueta diego
```

### Multiplicación de matrices

> **Pendiente:** tabla de tiempos, speedup y eficiencia, tomada de `resultados_diego/metricas_matrices.csv`.

> **Pendiente:** insertar las figuras de `img_diego/matrices_*.png`.

### Suma de Riemann

> **Pendiente:** tabla de tiempos, speedup y eficiencia, tomada de `resultados_diego/metricas_riemann.csv`.

> **Pendiente:** insertar las figuras de `img_diego/riemann_*.png`.

### Evidencia de ejecución

> **Pendiente:** captura de pantalla o video de la ejecución del barrido.

### Análisis

> **Pendiente:** comentar en qué número de hilos cae la eficiencia y si coincide con los núcleos físicos del equipo.

---

## Comparación entre los tres equipos

> **Pendiente:** completar cuando estén disponibles las tres mediciones. La hipótesis a contrastar es que el punto donde se desploma la eficiencia coincida, en cada equipo, con su número de núcleos físicos y no con el de hilos lógicos.
