"""Búsqueda de un tablero repartiendo sus ramas entre los procesos de un comunicador.

Lo usan la versión por ramas y la versión híbrida. Cada proceso explora las ramas
que le tocan con backtracking. Si alguno encuentra la solución, envía una señal a
los demás para que dejen de buscar ese tablero.
"""

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mpi4py import MPI  # noqa: E402

from sudoku import puede_colocar  # noqa: E402

ETIQUETA_CANCELAR = 11
# Cada cuántas llamadas recursivas se revisa si debe detenerse la búsqueda.
VISITAS_ENTRE_CONTROLES = 256


class Cancelado(Exception):
    """Otro proceso ya encontró la solución de este tablero."""


class Buscador:
    """Backtracking igual al de sudoku.py, pero que puede detenerse a mitad de camino."""

    def __init__(self, detener):
        self.detener = detener
        self.visitas = 0

    def resolver(self, tablero):
        self.visitas += 1
        if self.visitas % VISITAS_ENTRE_CONTROLES == 0 and self.detener():
            raise Cancelado()
        for fila in range(9):
            for columna in range(9):
                if tablero[fila][columna] == 0:
                    for valor in range(1, 10):
                        if puede_colocar(tablero, fila, columna, valor):
                            tablero[fila][columna] = valor
                            if self.resolver(tablero):
                                return True
                            tablero[fila][columna] = 0
                    return False
        return True


def generar_ramas(tablero, minimo):
    """Expande las primeras casillas vacías hasta tener al menos `minimo` ramas válidas.

    Devuelve una lista de tableros parciales. Si el tablero no tiene solución, la lista
    queda vacía. Si el tablero ya está completo, devuelve una sola rama.
    """
    vacias = [(f, c) for f in range(9) for c in range(9) if tablero[f][c] == 0]
    ramas = [[fila[:] for fila in tablero]]
    for fila, columna in vacias:
        if len(ramas) >= minimo:
            break
        nuevas = []
        for rama in ramas:
            for valor in range(1, 10):
                if puede_colocar(rama, fila, columna, valor):
                    copia = [f[:] for f in rama]
                    copia[fila][columna] = valor
                    nuevas.append(copia)
        ramas = nuevas
        if not ramas:
            break
    return ramas


def resolver_con_ramas(comunicador, tablero):
    """Resuelve `tablero` repartiendo sus ramas entre los procesos de `comunicador`.

    Todos los procesos del comunicador deben llamar a esta función con el mismo tablero.
    Devuelve (solución o None si no tiene solución, segundos). El tiempo se mide desde
    que empieza el reparto hasta que todos los procesos tienen el resultado.
    """
    rango = comunicador.Get_rank()
    tamano = comunicador.Get_size()

    comunicador.Barrier()
    inicio = time.perf_counter()

    ramas = generar_ramas(tablero, minimo=2 * tamano)

    def detener():
        return comunicador.iprobe(source=MPI.ANY_SOURCE, tag=ETIQUETA_CANCELAR)

    buscador = Buscador(detener)
    local = None
    for rama in ramas[rango::tamano]:
        if detener():
            break
        copia = [fila[:] for fila in rama]
        try:
            if buscador.resolver(copia):
                local = copia
                break
        except Cancelado:
            break

    if local is not None:
        for otro in range(tamano):
            if otro != rango:
                comunicador.send(True, dest=otro, tag=ETIQUETA_CANCELAR)

    soluciones = comunicador.allgather(local)
    encontrados = sum(1 for s in soluciones if s is not None)
    propio = 1 if local is not None else 0
    # Cada proceso que encontró solución envió una señal a los demás.
    # Se consume exactamente esa cantidad para no dejar mensajes pendientes.
    for _ in range(encontrados - propio):
        comunicador.recv(source=MPI.ANY_SOURCE, tag=ETIQUETA_CANCELAR)

    solucion = next((s for s in soluciones if s is not None), None)
    segundos = time.perf_counter() - inicio
    return solucion, segundos
