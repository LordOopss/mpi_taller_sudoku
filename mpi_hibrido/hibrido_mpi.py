"""Versión híbrida: los procesos se dividen en grupos. Cada grupo resuelve sus propios IDs
y dentro de cada grupo las ramas del tablero se reparten entre sus procesos.

Reglas de reparto:
- El grupo k resuelve los IDs cuyo índice cumple i % G == k (G = número de grupos).
- Dentro del grupo, las ramas del tablero se reparten con el mismo método de la versión
  por ramas (busqueda_ramas.resolver_con_ramas).
- Por defecto el tamaño de grupo es el mayor divisor de N que no supera la raíz cuadrada
  de N. Así el número de grupos y de procesos por grupo quedan parejos. Puedes fijarlo
  con --tamano-grupo, siempre que divida a N.

Ejemplo con N = 4 (dos grupos de dos procesos), desde la carpeta del proyecto:
  docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
    mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 \
    python /app/mpi_hibrido/hibrido_mpi.py --all
"""

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_RAMAS = RAIZ / "mpi_por_ramas"
for ruta in (RAIZ, CARPETA_RAMAS):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from mpi4py import MPI  # noqa: E402

from baseline_secuencial import leer_seeds  # noqa: E402
from busqueda_ramas import resolver_con_ramas  # noqa: E402


def tamano_grupo_por_defecto(procesos):
    """Mayor divisor de `procesos` que no supera su raíz cuadrada."""
    mejor = 1
    for divisor in range(1, procesos + 1):
        if procesos % divisor == 0 and divisor * divisor <= procesos:
            mejor = divisor
    return mejor


def main():
    parser = argparse.ArgumentParser(description="Resuelve Sudokus con MPI: grupos de IDs y ramas.")
    parser.add_argument("--archivo", type=Path, default=RAIZ / "seeds.txt",
                        help="archivo de seeds (por defecto: seeds.txt de la raíz del proyecto)")
    parser.add_argument("--tamano-grupo", type=int, default=None,
                        help="procesos por grupo; debe dividir al número de procesos "
                             "(por defecto: mayor divisor no mayor que la raíz cuadrada de N)")
    seleccion = parser.add_mutually_exclusive_group()
    seleccion.add_argument("--id", "--seed", dest="id", help="resolver solo la seed con este ID")
    seleccion.add_argument("--all", action="store_true", help="resolver todos los seeds")
    args = parser.parse_args()

    comunicador = MPI.COMM_WORLD
    rango = comunicador.Get_rank()
    tamano = comunicador.Get_size()

    grupo_tamano = args.tamano_grupo or tamano_grupo_por_defecto(tamano)
    if grupo_tamano < 1 or tamano % grupo_tamano != 0:
        parser.error(f"--tamano-grupo={grupo_tamano} debe dividir al número de procesos ({tamano})")
    numero_grupos = tamano // grupo_tamano
    identificador_grupo = rango // grupo_tamano
    comunicador_grupo = comunicador.Split(color=identificador_grupo, key=rango)

    try:
        seeds = leer_seeds(args.archivo)
    except OSError as error:
        parser.error(f"no se pudo leer {args.archivo}: {error}")
    if not seeds:
        parser.error(f"no se encontraron seeds en {args.archivo}")
    if args.id:
        if args.id not in seeds:
            parser.error(f"ID '{args.id}' no existe. Disponibles: {', '.join(seeds)}")
        seleccionados = [(args.id, seeds[args.id])]
    else:
        seleccionados = list(seeds.items())

    comunicador.Barrier()
    inicio = time.perf_counter()

    locales = []
    for indice, (nombre, original) in enumerate(seleccionados):
        if indice % numero_grupos != identificador_grupo:
            continue
        tablero = [fila[:] for fila in original]
        solucion, segundos = resolver_con_ramas(comunicador_grupo, tablero)
        if comunicador_grupo.Get_rank() == 0:
            locales.append({"indice": indice, "id": nombre,
                            "resuelto": solucion is not None, "segundos": segundos})

    aportes = comunicador.gather(locales, root=0)
    if rango != 0:
        return

    tiempo_total = time.perf_counter() - inicio
    resultados = sorted((r for aporte in aportes for r in aporte), key=lambda r: r["indice"])
    if len(resultados) != len(seleccionados):
        raise RuntimeError(f"se esperaban {len(seleccionados)} resultados y llegaron {len(resultados)}")

    for resultado in resultados:
        print(f"\nID: {resultado['id']}")
        print("Resuelto" if resultado["resuelto"] else "Sin solución")
        etiqueta = "Tiempo" if args.id else "Tiempo parcial"
        print(f"{etiqueta}: {resultado['segundos']:.6f} segundos", flush=True)

    if not args.id:
        print(f"\nIDs procesados: {len(resultados)} de {len(seleccionados)}")
    print(f"Tiempo total ({tamano} procesos, {numero_grupos} grupos de {grupo_tamano}): "
          f"{tiempo_total:.6f} segundos")


if __name__ == "__main__":
    main()
