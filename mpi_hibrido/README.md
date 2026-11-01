# Tarea 3: combinar tableros y ramas

Implementación: [`hibrido_mpi.py`](hibrido_mpi.py). Reutiliza la búsqueda por ramas de [`../mpi_por_ramas/busqueda_ramas.py`](../mpi_por_ramas/busqueda_ramas.py).

## Diseño

Con N procesos se forman **G grupos** de `g` procesos cada uno (`N = G·g`).

- **Reparto de IDs entre grupos:** el grupo `k` resuelve los IDs cuyo índice `i` cumple `i % G == k`. Los grupos trabajan en paralelo sobre tableros distintos.
- **Reparto de ramas dentro del grupo:** los `g` procesos de un grupo resuelven cada uno de sus tableros con la misma estrategia de la versión por ramas.
- Los grupos se crean con `Split`, así que las sincronizaciones dentro de un grupo no bloquean a los demás.
- Al final, cada grupo envía sus resultados al proceso 0 con `gather`.

### Cómo se elige el tamaño de grupo

Por defecto, `g` es el **mayor divisor de N que no supera √N**. Con eso el número de grupos `G = N/g` queda cerca de `g`, de modo que hay suficientes grupos para repartir los IDs y suficientes procesos por grupo para repartir las ramas.

| N | g (por defecto) | G | Forma |
| --- | ---: | ---: | --- |
| 2 | 1 | 2 | 2 grupos de 1 |
| 3 | 1 | 3 | 3 grupos de 1 |
| 4 | 2 | 2 | 2 grupos de 2 |
| 6 | 2 | 3 | 3 grupos de 2 |
| 8 | 2 | 4 | 4 grupos de 2 |
| 9 | 3 | 3 | 3 grupos de 3 |

Con `--tamano-grupo` puedes fijar otro valor, siempre que divida a N.

**Limitación:** con N = 2 no hay forma de formar un grupo de 2 sin dejar un solo grupo, y entonces la versión híbrida se reduce a repartir IDs (dos grupos de 1). Por eso, con N = 2, la comparación más informativa es la de las versiones de tableros y de ramas.

## Ejecutar con el contenedor

Desde la carpeta raíz del proyecto. El ejemplo usa N = 2; para N = 4 con grupos de 2, cambia `-n 2` por `-n 4`.

**macOS / Linux**

```bash
# Un tablero
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 \
  python /app/mpi_hibrido/hibrido_mpi.py --id 7

# Los 30 tableros
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 \
  python /app/mpi_hibrido/hibrido_mpi.py --all
```

**Windows (PowerShell)**

```powershell
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 `
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 `
  python /app/mpi_hibrido/hibrido_mpi.py --all
```

## Verificación

Con `--all` se imprimen los 30 IDs, su estado y el tiempo parcial de cada uno, y al final el tiempo total con el número de grupos. Los estados deben coincidir con la versión secuencial.
