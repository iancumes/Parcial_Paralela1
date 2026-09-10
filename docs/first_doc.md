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
