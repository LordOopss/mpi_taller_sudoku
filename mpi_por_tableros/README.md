# Tarea 1: repartir tableros

Implementación: [`tableros_mpi.py`](tableros_mpi.py).

## Diseño

Cada ID de `seeds.txt` es una tarea independiente.

- El proceso 0 **coordina** el reparto de forma dinámica: cada trabajador recibe un tablero, y cuando devuelve el resultado recibe el siguiente pendiente. Como los tableros tardan entre 2 y 10 s, un reparto fijo por bloques dejaría procesos ociosos.
- El proceso 0 también **resuelve tableros** cuando no tiene resultados que atender. Con N procesos hay N-1 trabajadores más el coordinador que trabaja, de modo que los N procesos hacen trabajo útil.
- Cada tarea reutiliza `resolver_con_tiempo()` de `../sudoku.py`.
- El coordinador reúne los estados de los 30 IDs, comprueba que llegaron todos y muestra el tiempo total de la ejecución. El tiempo mide desde el inicio del reparto hasta recibir el último resultado.

Con `--id` se resuelve solo un tablero.

## Ejecutar con el contenedor

Desde la carpeta raíz del proyecto (la que contiene `seeds.txt`):

**macOS / Linux**

```bash
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 \
  python /app/mpi_por_tableros/tableros_mpi.py --all
```

**Windows (PowerShell)**

```powershell
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 `
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 `
  python /app/mpi_por_tableros/tableros_mpi.py --all
```

Para un solo tablero, reemplaza `--all` por `--id 7`. Para cambiar el número de procesos, modifica `-n 2` con el valor `N` elegido en la calibración del equipo.

## Verificación

La salida muestra cada ID con su estado, el tiempo parcial de cada tablero y, al final, `IDs procesados: 30 de 30` y el tiempo total. Si no llegan los 30 resultados, el programa termina con error.
