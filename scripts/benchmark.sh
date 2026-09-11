#!/usr/bin/env bash
#
# Barrido de metricas de los dos problemas del parcial, secuencial vs OpenMP:
#   - multiplicacion de matrices densas
#   - integracion numerica por suma de Riemann
#
# Compila un binario por configuracion (el tamano del problema es una constante
# de compilacion, ver los #ifndef en los .c), corre el barrido completo, valida
# que los resultados coincidan entre la version secuencial y la paralela, y
# guarda los tiempos crudos en CSV. Al final invoca graficar.py.
#
# Uso:  ./scripts/benchmark.sh [--etiqueta NOMBRE] [--solo matrices|riemann]
#                              [--pausa SEGUNDOS]
#
# Las repeticiones se INTERCALAN: el ciclo externo es la repeticion y el interno
# recorre todas las configuraciones. Si se midieran las 5 repeticiones de una
# configuracion seguidas, el orden del barrido quedaria correlacionado con la
# temperatura del CPU y las ultimas configuraciones saldrian penalizadas por
# throttling termico. Intercalando, cada configuracion se mide en 5 estados
# termicos distintos y el minimo de las 5 es representativo.
#
# --pausa agrega segundos de enfriamiento entre configuraciones. En un portatil
# conviene ademas arrancar con la maquina fria: con el CPU caliente las
# frecuencias caen a menos de la mitad y el speedup medido se desploma.
#
# La etiqueta separa las salidas por persona/maquina (resultados_<etiqueta>/ e
# img_<etiqueta>/), para que los tres integrantes midan en su propio equipo sin
# pisarse los resultados. Por defecto toma $ETIQUETA, y si no, el usuario del
# sistema.
#
set -euo pipefail

# ---------------------------------------------------------------- configuracion
HILOS=(1 2 4 8 16)
REPS=5
CFLAGS=(-O2 -fopenmp -Wall)

# matrices
TAMANOS=(500 1000 1500 2000)

# riemann
RECTANGULOS=(100000000 500000000 1000000000)
FUNCIONES=(1 3)          # 1 = x^2 (poco computo)   3 = sin(x) (3.4x mas caro)
LIMITE_A=0
LIMITE_B=1
TOLERANCIA=1e-9          # la suma flotante no es asociativa: se compara con
                         # tolerancia relativa, no por igualdad exacta

# Las banderas deben ser identicas para ambas versiones de cada problema: -O0 vs
# -O2 cambia los tiempos hasta 6x y cualquier diferencia invalida la comparacion.

# ------------------------------------------------------------------- argumentos
SOLO=""
PAUSA=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --etiqueta)
            [[ -n "${2:-}" ]] || { echo "--etiqueta necesita un nombre" >&2; exit 2; }
            ETIQUETA="$2"; shift 2 ;;
        --solo)
            [[ "${2:-}" == "matrices" || "${2:-}" == "riemann" ]] \
                || { echo "--solo acepta: matrices | riemann" >&2; exit 2; }
            SOLO="$2"; shift 2 ;;
        --pausa)
            [[ "${2:-}" =~ ^[0-9]+$ ]] || { echo "--pausa necesita un numero de segundos" >&2; exit 2; }
            PAUSA="$2"; shift 2 ;;
        *)
            echo "Argumento desconocido: $1" >&2
            echo "Uso: $0 [--etiqueta NOMBRE] [--solo matrices|riemann] [--pausa SEGUNDOS]" >&2
            exit 2 ;;
    esac
done

ETIQUETA="${ETIQUETA:-$(whoami)}"
export ETIQUETA   # graficar.py lo lee para resolver sus propias rutas

corre() { [[ -z "$SOLO" || "$SOLO" == "$1" ]]; }
enfriar() { (( PAUSA > 0 )) && sleep "$PAUSA" || true; }

# ---------------------------------------------------------------------- rutas
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

BUILD="$RAIZ/build"
RESULTADOS="$RAIZ/resultados_$ETIQUETA"
CRUDAS_MATRICES="$RESULTADOS/metricas_crudas_matrices.csv"
CRUDAS_RIEMANN="$RESULTADOS/metricas_crudas_riemann.csv"

mkdir -p "$BUILD" "$RESULTADOS"

log() { printf '%s\n' "$*" >&2; }

abortar() {
    log ""
    log "ERROR: $*"
    log "La version paralela no esta produciendo el mismo resultado que la secuencial."
    exit 1
}

log "Etiqueta: $ETIQUETA  ->  resultados_$ETIQUETA/  e  img_$ETIQUETA/"
log "Compilando con: gcc ${CFLAGS[*]}"

# ==============================================================================
# Matrices
# ==============================================================================
if corre matrices; then
    for s in "${TAMANOS[@]}"; do
        gcc "${CFLAGS[@]}" -DN="$s" -DM="$s" -DP="$s" -DQ="$s" \
            secuencial/secuencial_matrices.c -o "$BUILD/mat_sec_$s"
        gcc "${CFLAGS[@]}" -DN="$s" -DM="$s" -DP="$s" -DQ="$s" \
            paralelo/matrices_openmp.c -o "$BUILD/mat_par_$s"
        log "  matrices n=$s"
    done

    echo "programa,n,hilos,rep,tiempo,checksum" > "$CRUDAS_MATRICES"

    # checksum de referencia por tamano: enteros, se comparan por igualdad exacta
    declare -A REF_MATRICES

    # UNA medicion. $1 programa  $2 tamano  $3 binario  $4 repeticion
    medir_matrices() {
        local programa="$1" s="$2" binario="$3" rep="$4"
        local n hilos tiempo checksum

        # el binario emite exactamente: n,hilos,tiempo,checksum
        IFS=, read -r n hilos tiempo checksum < <("$binario")
        echo "$programa,$n,$hilos,$rep,$tiempo,$checksum" >> "$CRUDAS_MATRICES"

        if [[ -z "${REF_MATRICES[$s]:-}" ]]; then
            REF_MATRICES[$s]="$checksum"
        elif [[ "$checksum" != "${REF_MATRICES[$s]}" ]]; then
            abortar "checksum inconsistente en n=$s ($programa, hilos=$hilos, rep $rep):" \
                    "esperado ${REF_MATRICES[$s]}, obtenido $checksum"
        fi
        enfriar
    }

    for rep in $(seq 1 "$REPS"); do
        log "[matrices] repeticion $rep/$REPS"
        for s in "${TAMANOS[@]}"; do
            OMP_NUM_THREADS=1 medir_matrices secuencial "$s" "$BUILD/mat_sec_$s" "$rep"
            for h in "${HILOS[@]}"; do
                OMP_NUM_THREADS="$h" medir_matrices paralelo "$s" "$BUILD/mat_par_$s" "$rep"
            done
        done
    done

    log "Checksums validados: la matriz resultante es identica en todas las configuraciones."
    log "  -> ${CRUDAS_MATRICES#$RAIZ/}"
fi

# ==============================================================================
# Riemann
# ==============================================================================
if corre riemann; then
    for n in "${RECTANGULOS[@]}"; do
        gcc "${CFLAGS[@]}" -DNUM_RECTANGULOS="${n}ULL" \
            secuencial/riemann_secuencial.c -o "$BUILD/rie_sec_$n" -lm
        gcc "${CFLAGS[@]}" -DNUM_RECTANGULOS="${n}ULL" \
            paralelo/riemann_openmp.c -o "$BUILD/rie_par_$n" -lm
        log "  riemann n=$n"
    done

    echo "programa,n,hilos,funcion,a,b,rep,tiempo,area,error" > "$CRUDAS_RIEMANN"

    # area de referencia por (rectangulos, funcion). A diferencia de matrices no
    # se puede exigir igualdad exacta: la reduccion paralela suma en otro orden.
    declare -A REF_RIEMANN

    # UNA medicion. $1 programa  $2 binario  $3 funcion  $4 repeticion
    medir_riemann() {
        local programa="$1" binario="$2" f="$3" rep="$4"
        local n hilos funcion a b tiempo area error clave

        # el binario emite: n,hilos,funcion,a,b,tiempo,area,error
        IFS=, read -r n hilos funcion a b tiempo area error \
            < <("$binario" "$f" "$LIMITE_A" "$LIMITE_B")
        echo "$programa,$n,$hilos,$funcion,$a,$b,$rep,$tiempo,$area,$error" \
            >> "$CRUDAS_RIEMANN"

        clave="${n}_${f}"
        if [[ -z "${REF_RIEMANN[$clave]:-}" ]]; then
            REF_RIEMANN[$clave]="$area"
        else
            # la comparacion flotante la hace awk; bash no hace aritmetica real
            awk -v a="$area" -v r="${REF_RIEMANN[$clave]}" -v tol="$TOLERANCIA" \
                'BEGIN { exit (r == 0 ? (a == 0) : ((a-r < 0 ? r-a : a-r) / (r < 0 ? -r : r) <= tol)) ? 0 : 1 }' \
                || abortar "area fuera de tolerancia en n=$n f=$f ($programa, hilos=$hilos, rep $rep):" \
                           "referencia ${REF_RIEMANN[$clave]}, obtenida $area (tolerancia relativa $TOLERANCIA)"
        fi
        enfriar
    }

    for rep in $(seq 1 "$REPS"); do
        log "[riemann] repeticion $rep/$REPS"
        for f in "${FUNCIONES[@]}"; do
            for n in "${RECTANGULOS[@]}"; do
                OMP_NUM_THREADS=1 medir_riemann secuencial "$BUILD/rie_sec_$n" "$f" "$rep"
                for h in "${HILOS[@]}"; do
                    OMP_NUM_THREADS="$h" medir_riemann paralelo "$BUILD/rie_par_$n" "$f" "$rep"
                done
            done
        done
    done

    log "Areas validadas dentro de $TOLERANCIA relativo en todas las configuraciones."
    log "  -> ${CRUDAS_RIEMANN#$RAIZ/}"
fi

log ""

# ------------------------------------------------------------------- graficos
exec python3 "$RAIZ/scripts/graficar.py"
