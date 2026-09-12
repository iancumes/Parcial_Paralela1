# Scripts de métricas

Dos scripts. `benchmark.sh` mide, `graficar.py` dibuja.

```
benchmark.sh   compila -> corre el barrido -> valida -> escribe los CSV -> llama a graficar.py
graficar.py    lee los CSV -> calcula speedup y eficiencia -> escribe el resumen y las figuras
```

---

## 1. Cómo correrlos

```sh
./scripts/benchmark.sh --etiqueta ian                    # los dos problemas (~10 min)
./scripts/benchmark.sh --etiqueta ian --solo riemann     # solo la suma de Riemann
./scripts/benchmark.sh --etiqueta ian --solo matrices    # solo matrices
```

Si el equipo no tiene 8 nucleos fisicos, se debe indicar el valor para que la
linea vertical de las graficas quede correctamente rotulada. Por ejemplo:

```sh
NUCLEOS_FISICOS=14 ./scripts/benchmark.sh --etiqueta ian
```

| Bandera | Qué hace |
|---|---|
| `--etiqueta NOMBRE` | Separa tus salidas de las de los demás: escribe en `resultados_NOMBRE/` e `img_NOMBRE/`. Si no la pasas, usa tu usuario del sistema. |
| `--solo matrices\|riemann` | Corre un solo problema. Útil para iterar sin pagar el barrido completo. |
| `--pausa SEGUNDOS` | Espera ese tiempo entre mediciones para que el CPU se enfríe. Alarga bastante el barrido. |

Para volver a dibujar las figuras sin medir de nuevo (por ejemplo si cambias un color o un título):

```sh
python3 scripts/graficar.py --etiqueta ian
```

Requisitos: `gcc` con OpenMP, y Python con `pandas` y `matplotlib`.

---

## 2. Qué genera

```
resultados_<etiqueta>/
  metricas_crudas_matrices.csv    todas las corridas, sin promediar
  metricas_crudas_riemann.csv
  metricas_matrices.csv           resumen: speedup y eficiencia
  metricas_riemann.csv

img_<etiqueta>/
  matrices_speedup_vs_hilos.png       riemann_speedup_vs_hilos.png
  matrices_eficiencia_vs_hilos.png    riemann_eficiencia_vs_hilos.png
  matrices_tiempo_vs_hilos.png        riemann_tiempo_vs_hilos.png
  matrices_tiempo_vs_tamano.png       riemann_tiempo_vs_tamano.png
```

Los CSV crudos guardan **cada** corrida, así que se puede rehacer el análisis sin volver a medir.

### Las columnas del resumen

| Columna | Qué es |
|---|---|
| `t_sec`, `t_par` | Tiempo del secuencial y del paralelo, en segundos |
| `speedup_real` | `t_sec / t_par` — contra el secuencial. Es la definición formal de speedup |
| `speedup_omp` | `t_par(1 hilo) / t_par` — contra el paralelo con un hilo. Aísla la escalabilidad de OpenMP |
| `eficiencia_real`, `eficiencia_omp` | Cada speedup dividido entre el número de hilos |

**Hay dos speedups a propósito**, y conviene reportar los dos. Ver la sección 3.

---

## 3. Cómo está hecho

Cosas que no se ven leyendo el código de corrido:

**El tamaño del problema es constante de compilación.** Los `.c` lo toman de `#ifndef N` / `#ifndef
NUM_RECTANGULOS`, así que el script compila **un binario por tamaño** en `build/` (ignorado por git). Por eso
el barrido empieza con una tanda de `gcc`.

**Las repeticiones se intercalan.** El ciclo externo es la repetición y el interno recorre todas las
configuraciones. Si se midieran las 5 repeticiones de una configuración seguidas, el orden del barrido
quedaría correlacionado con la temperatura del CPU y las últimas configuraciones saldrían penalizadas por
throttling. Intercalando, cada configuración se mide en 5 estados térmicos distintos.

**Se toma el mínimo, no el promedio.** Los tiempos varían ~25% entre corridas idénticas por turbo y
scheduling del sistema operativo. El mínimo es la estimación menos contaminada por ruido ajeno al programa.

**Cada problema se valida distinto.** Matrices compara un checksum entero por **igualdad exacta**. Riemann no
puede: la reducción paralela suma en otro orden y la suma en punto flotante no es asociativa, así que compara
el área con **tolerancia relativa** (`TOLERANCIA`, hoy `1e-9`). Si la validación falla, el barrido aborta y
dice qué configuración falló.

**Por qué dos líneas base de speedup.** El `#pragma` cambia lo que gcc puede optimizar, así que el paralelo
con 1 hilo **no** equivale al secuencial — y en los dos problemas pasa, pero en sentidos opuestos:

| | `t_par(1) / t_sec` | Por qué |
|---|---|---|
| Matrices | ~2.4 (más lento) | El pragma **inhibe** la vectorización SIMD que gcc aplica al ciclo secuencial |
| Riemann con `x²` | ~0.75 (más rápido) | `reduction(+:)` autoriza reasociar la suma, lo que **habilita** una vectorización que el secuencial tiene prohibida |
| Riemann con `sin(x)` | ~0.99 (igual) | `sin()` es una llamada a `libm` que no se vectoriza, así que el permiso no sirve de nada |

Medir solo contra el secuencial mezcla el efecto del paralelismo con el de la vectorización. Medir solo
contra el paralelo de 1 hilo esconde que la versión paralela arranca de otro punto. Por eso van los dos.

---

## 4. Cómo modificarlo

Todo lo ajustable está en el bloque de configuración, al inicio de `benchmark.sh`:

```bash
HILOS=(1 2 4 8 16)
REPS=5
CFLAGS=(-O2 -fopenmp -Wall)

TAMANOS=(500 1000 1500 2000)                          # matrices

RECTANGULOS=(100000000 500000000 1000000000)          # riemann
FUNCIONES=(1 3)
LIMITE_A=0
LIMITE_B=1
TOLERANCIA=1e-9
```

- **Agregar un tamaño o un conteo de hilos**: añadirlo al array. Nada más; el script compila y barre lo que
  encuentre, y `graficar.py` toma los valores del CSV, no de una lista fija.
- **Agregar una función a Riemann**: las cinco opciones ya existen en el `switch` de `evaluar_funcion()`
  (1=x², 2=x³, 3=sin, 4=cos, 5=e^(-x²)). Basta con ponerla en `FUNCIONES`. Si quieres una función nueva,
  hay que agregarle también su caso en `integral_exacta()`, porque sin el valor analítico no se puede validar.
- **`CFLAGS` debe ser idéntico para las dos versiones de un problema.** `-O0` contra `-O2` cambia los tiempos
  hasta 6x, y cualquier diferencia entre secuencial y paralelo invalida la comparación.
- Los tamaños chicos no sirven para medir: con matrices de 500×500 el barrido tarda 0.05 s y el costo de
  crear el equipo de hilos domina. De 1000 para arriba.

---

## 5. Advertencias al medir

**Arrancar con la máquina fría.** Con el CPU caliente las frecuencias caen a menos de la mitad (medimos
1.5 GHz contra 4.3 GHz de boost) y el speedup se desploma: la misma configuración dio 2.50x en caliente donde
en frío daba 6.83x. El intercalado evita que el sesgo caiga sobre una configuración en particular, pero los
tiempos absolutos siguen dependiendo de la temperatura.

**No conectar la salida a `head` ni a nada que cierre el pipe.** El script muere por SIGPIPE a media corrida
y deja el CSV truncado **sin ningún mensaje de error**. Para guardar el log:

```sh
./scripts/benchmark.sh --etiqueta ian > log.txt 2>&1
```

**No usar la máquina para otra cosa mientras mide.** Cualquier proceso pesado en paralelo compite por los
mismos núcleos y contamina los tiempos.

**Los tiempos solo son comparables entre máquinas** si las tres corren con el mismo `CFLAGS`. El número de
hilos donde la eficiencia se desploma debería coincidir con los **núcleos físicos** de cada equipo, que no
son los mismos en las tres.
