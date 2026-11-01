"""Versión MPI por ramas: los tableros se procesan en orden y las ramas de cada uno se
reparten entre los procesos. Un tablero termina antes de empezar el siguiente.

Ejemplo (desde la carpeta del proyecto, con Docker):
  docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
    mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 \
    python /app/mpi_por_ramas/ramas_mpi.py --all
"""

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = Path(__file__).resolve().parent
for ruta in (RAIZ, CARPETA):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from mpi4py import MPI  # noqa: E402

from baseline_secuencial import leer_seeds  # noqa: E402
from busqueda_ramas import resolver_con_ramas  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Resuelve Sudokus con MPI repartiendo ramas.")
    parser.add_argument("--archivo", type=Path, default=RAIZ / "seeds.txt",
                        help="archivo de seeds (por defecto: seeds.txt de la raíz del proyecto)")
    seleccion = parser.add_mutually_exclusive_group()
    seleccion.add_argument("--id", "--seed", dest="id", help="resolver solo la seed con este ID")
    seleccion.add_argument("--all", action="store_true", help="resolver todos los seeds, en orden")
    args = parser.parse_args()

    comunicador = MPI.COMM_WORLD
    rango = comunicador.Get_rank()
    tamano = comunicador.Get_size()

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
    inicio_total = time.perf_counter()
    for nombre, original in seleccionados:
        tablero = [fila[:] for fila in original]
        solucion, segundos = resolver_con_ramas(comunicador, tablero)
        if rango == 0:
            print(f"\nID: {nombre}")
            print("Resuelto" if solucion is not None else "Sin solución")
            etiqueta = "Tiempo" if args.id else "Tiempo parcial"
            print(f"{etiqueta}: {segundos:.6f} segundos", flush=True)
    tiempo_total = time.perf_counter() - inicio_total

    if rango == 0 and not args.id:
        print(f"\nTiempo total ({tamano} procesos, {len(seleccionados)} IDs): "
              f"{tiempo_total:.6f} segundos")
    elif rango == 0:
        print(f"\nTiempo total ({tamano} procesos): {tiempo_total:.6f} segundos")


if __name__ == "__main__":
    main()
