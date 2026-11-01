"""Versión MPI por tableros: cada ID es una tarea que se asigna a un proceso.

El proceso 0 coordina el reparto. Cuando un trabajador devuelve un resultado, recibe
el siguiente tablero pendiente. Si el proceso 0 no tiene que atender mensajes, también
resuelve tableros. Así un tablero difícil no retrasa a todo el grupo.

Ejemplo (desde la carpeta del proyecto, con Docker):
  docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
    mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 3 \
    python /app/mpi_por_tableros/tableros_mpi.py --all
"""

import argparse
import sys
import time
from collections import deque
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mpi4py import MPI  # noqa: E402

from baseline_secuencial import leer_seeds  # noqa: E402
from sudoku import resolver_con_tiempo  # noqa: E402

ETIQUETA_TAREA = 1
ETIQUETA_RESULTADO = 2


def resolver_id(identificador, tablero):
    copia = [fila[:] for fila in tablero]
    resuelto, segundos = resolver_con_tiempo(copia)
    return {"id": identificador, "resuelto": resuelto, "segundos": segundos}


def trabajar(comunicador):
    """Procesos 1..N-1: reciben un tablero, lo resuelven y devuelven el resultado."""
    while True:
        tarea = comunicador.recv(source=0, tag=ETIQUETA_TAREA)
        if tarea is None:
            return
        comunicador.send(resolver_id(*tarea), dest=0, tag=ETIQUETA_RESULTADO)


PROFUNDIDAD = 2  # tareas enviadas por adelantado a cada trabajador


def coordinar(comunicador, tareas):
    """Proceso 0: reparte tareas de forma dinámica y también resuelve.

    Cada trabajador tiene hasta PROFUNDIDAD tareas en cola. Así no se queda ocioso
    mientras el proceso 0 resuelve su propio tablero.
    """
    tamano = comunicador.Get_size()
    pendientes = deque(tareas)
    resultados = []
    en_curso = {trabajador: 0 for trabajador in range(1, tamano)}
    cerrados = set()

    def enviar(trabajador):
        comunicador.send(pendientes.popleft(), dest=trabajador, tag=ETIQUETA_TAREA)
        en_curso[trabajador] += 1

    def cerrar(trabajador):
        comunicador.send(None, dest=trabajador, tag=ETIQUETA_TAREA)
        cerrados.add(trabajador)

    for trabajador in en_curso:
        for _ in range(PROFUNDIDAD):
            if pendientes:
                enviar(trabajador)
        if en_curso[trabajador] == 0:
            cerrar(trabajador)

    while pendientes or any(en_curso.values()):
        if pendientes:
            resultados.append(resolver_id(*pendientes.popleft()))
        # Recoger los resultados que ya llegaron. Si no queda trabajo local, esperar.
        while any(en_curso.values()) and (not pendientes or comunicador.iprobe(
                source=MPI.ANY_SOURCE, tag=ETIQUETA_RESULTADO)):
            estado = MPI.Status()
            resultado = comunicador.recv(source=MPI.ANY_SOURCE,
                                         tag=ETIQUETA_RESULTADO, status=estado)
            resultados.append(resultado)
            trabajador = estado.Get_source()
            en_curso[trabajador] -= 1
            if pendientes:
                enviar(trabajador)
            elif en_curso[trabajador] == 0 and trabajador not in cerrados:
                cerrar(trabajador)
    return resultados


def main():
    parser = argparse.ArgumentParser(description="Resuelve Sudokus con MPI repartiendo tableros.")
    parser.add_argument("--archivo", type=Path, default=RAIZ / "seeds.txt",
                        help="archivo de seeds (por defecto: seeds.txt de la raíz del proyecto)")
    seleccion = parser.add_mutually_exclusive_group()
    seleccion.add_argument("--id", "--seed", dest="id", help="resolver solo la seed con este ID")
    seleccion.add_argument("--all", action="store_true", help="resolver todos los seeds")
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
        tareas = [(args.id, seeds[args.id])]
    else:
        tareas = list(seeds.items())

    comunicador.Barrier()
    inicio = time.perf_counter()
    if rango == 0:
        resultados = coordinar(comunicador, tareas)
        tiempo_total = time.perf_counter() - inicio
    else:
        trabajar(comunicador)
        return

    if len(resultados) != len(tareas):
        raise RuntimeError(f"se esperaban {len(tareas)} resultados y llegaron {len(resultados)}")

    for resultado in sorted(resultados, key=lambda r: (len(r["id"]), r["id"])):
        print(f"\nID: {resultado['id']}")
        print("Resuelto" if resultado["resuelto"] else "Sin solución")
        etiqueta = "Tiempo" if args.id else "Tiempo parcial"
        print(f"{etiqueta}: {resultado['segundos']:.6f} segundos", flush=True)

    if not args.id:
        print(f"\nIDs procesados: {len(resultados)} de {len(tareas)}")
    print(f"Tiempo total ({tamano} procesos): {tiempo_total:.6f} segundos")


if __name__ == "__main__":
    main()
