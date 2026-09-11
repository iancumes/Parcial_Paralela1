# RDI Solutions

## Problemas escogidos
Suma de Riemann y Multiplicacion de Matrices

## Como correr las metricas

```sh
./scripts/benchmark.sh --etiqueta ian                    # los dos problemas
./scripts/benchmark.sh --etiqueta ian --solo riemann     # solo la suma de Riemann
./scripts/benchmark.sh --etiqueta ian --solo matrices    # solo matrices
```

Cada integrante usa su propia etiqueta (`ian`, `diego`, `ricardo`) y sus salidas caen en
`resultados_<etiqueta>/` e `img_<etiqueta>/`, para poder comparar las tres maquinas.

La guia completa esta en **[scripts/README.md](scripts/README.md)**: que genera cada script,
como esta hecho el barrido, como agregar tamanos o funciones, y las advertencias al medir.

## Ian Rodrigo Cumes Valdez

## Diego Jose Lopez Campos

## Ricardo Arturo Godinez Sanchez