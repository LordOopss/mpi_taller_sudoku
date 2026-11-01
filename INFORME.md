# Informe de resultados

Este informe compara el tiempo del Sudoku en versión secuencial con tres versiones hechas con MPI. Todas las pruebas usan el mismo archivo `seeds.txt` (30 tableros), la misma máquina y el contenedor del taller.

## Entorno

- Equipo: Windows con Docker Desktop (PowerShell), 8 procesadores lógicos (`nproc` = 8).
- Versión del contenedor: `augustosalazar/slim-mpi:2`, digest `sha256:a196b8fd2aec025fa393bc517ef7f541f4dbe70c8b42c06639289fbb9f7ff94d`.
- Repeticiones por medición: 3.
- Valor de `N` elegido: **8**. Lo dio `detectar_procesos_mpi.py`: con N = 1 la mediana fue 5,843 s, con N = 2 fue 3,323 s y con N = 8 fue 1,603 s. Por eso usamos N = 8 en las tres versiones MPI.

## Resultados

Usamos la mediana de las tres repeticiones. La aceleración se calcula como `tiempo secuencial / tiempo MPI`.

| Implementación | Caso | Procesos | Mediana (s) | Aceleración |
| --- | --- | ---: | ---: | ---: |
| Secuencial | Todos los IDs | 1 | 124,90 | 1,00 |
| MPI por tableros | Todos los IDs | 8 | 30,85 | 4,05 |
| MPI por ramas | Todos los IDs, uno después de otro | 8 | 36,39 | 3,43 |
| MPI híbrido | Todos los IDs (4 grupos de 2) | 8 | 35,26 | 3,54 |

Tiempos de cada repetición (s):

- Secuencial: 115,92 · 127,36 · 124,90
- MPI por tableros: 30,24 · 30,85 · 31,22
- MPI por ramas: 32,72 · 36,50 · 36,39
- MPI híbrido: 34,71 · 35,26 · 37,14

En las 12 ejecuciones se resolvieron los 30 tableros. El tiempo secuencial es la suma de los tiempos de búsqueda, como indica el baseline. El tiempo MPI se mide desde que se empieza a repartir el trabajo hasta que el proceso 0 recibe el último resultado.

## Conclusiones

**1. ¿Cuál fue la más rápida?**
La versión por tableros fue la más rápida: 30,85 s, unas 4 veces más rápida que la secuencial. Con 8 procesos, la eficiencia es de alrededor del 51 %. Además, sus tres repeticiones fueron más rápidas que todas las de las otras dos versiones. La más lenta de tableros (31,22 s) fue más rápida que la más rápida de ramas (32,72 s) y que la más rápida del híbrido (34,71 s).

**2. ¿Cómo afectaron la comunicación y la diferencia de tiempo entre tableros?**
- En tableros, cada tablero se envía como un mensaje pequeño. Cuando un trabajador termina, recibe el siguiente. Así los procesos casi no esperan, aunque cada tablero tarde distinto (unos 2 s o casi 15 s).
- En ramas, en cada uno de los 30 tableros hay que sincronizar todos los procesos. Además, el tiempo lo decide la rama más lenta. Por ejemplo, el tablero 6 tardó 0,04 s, pero el 17 tardó unos 2,7 s, y los demás procesos esperaban.
- En el híbrido pasa algo parecido dentro de cada grupo de 2 procesos, y además cada grupo termina en un momento distinto, así que algunos procesos esperan al final.

**3. ¿Cómo se comparó repartir tableros con repartir las ramas de cada uno?**
Repartir tableros fue unos 15 % más rápido que repartir ramas (30,85 s contra 36,39 s). Los 30 tableros son independientes y de tamaño parecido, así que dividir cada uno en ramas no ayuda. En cambio, la versión por ramas sí tendría sentido si un solo tablero fuera mucho más difícil que los demás, porque entonces los procesos libres podrían ayudarle.

**Nota:** la aceleración de 4 (y no de 8) puede deberse a que los 8 procesos lógicos comparten menos núcleos físicos, pero no lo comprobamos.
