# Tarea 2: repartir ramas de cada tablero

Implementación: [`ramas_mpi.py`](ramas_mpi.py). Usa el módulo [`busqueda_ramas.py`](busqueda_ramas.py), que también reutiliza la versión híbrida.

## Diseño

Los tableros se procesan **en orden**, uno después de otro. Para cada tablero:

1. Todos los procesos sincronizan con `Barrier` y empieza el cronómetro.
2. Se generan ramas expandiendo las primeras casillas vacías, en orden de lectura, hasta tener al menos `2·N` ramas válidas. Las ramas sin opciones se descartan.
3. Las ramas se asignan por turnos: el proceso `r` explora las ramas `r`, `r+N`, `r+2N`… Cada proceso las recorre con backtracking.
4. **Cancelación:** cuando un proceso encuentra la solución, envía una señal a los demás. Los demás revisan esa señal cada 256 llamadas recursivas y dejan de buscar.
5. Se recogen los resultados con `allgather`. Se consume exactamente la cantidad de señales enviadas, para que no queden mensajes pendientes en el siguiente tablero.

El tiempo parcial de cada ID va desde el inicio del reparto hasta que todos tienen el resultado. El tiempo total de `--all` es el tiempo real de pared de los 30 tableros, medido por el proceso 0.

## Ejecutar con el contenedor

Desde la carpeta raíz del proyecto:

**macOS / Linux**

```bash
# Un tablero
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 \
  python /app/mpi_por_ramas/ramas_mpi.py --id 7

# Los 30 tableros
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 \
  python /app/mpi_por_ramas/ramas_mpi.py --all
```

**Windows (PowerShell)**

```powershell
# Un tablero
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 `
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 `
  python /app/mpi_por_ramas/ramas_mpi.py --id 7

# Los 30 tableros
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 `
  mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 2 `
  python /app/mpi_por_ramas/ramas_mpi.py --all
```

Cambia `-n 2` por el `N` elegido en la calibración del equipo.

## Verificación

Cada tablero imprime `Resuelto` o `Sin solución` y su tiempo parcial. Al final, con `--all`, se imprime el tiempo total de los 30 tableros. Los resultados deben coincidir con la versión secuencial (`baseline_secuencial.py`).
