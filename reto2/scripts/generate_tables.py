#!/usr/bin/env python3
"""Generate CSV and PNG tables for reto2 benchmark results."""

from pathlib import Path

from traffic_plot_utils import (
    O3_FILE,
    OMP_FILE,
    OUTPUT_DIR,
    SERIAL_FILE,
    TABLES_DIR,
    average_by,
    common_sizes,
    ensure_dirs,
    load_omp_times,
    load_serial_metric,
    load_serial_times,
    write_table_artifacts,
)


THREAD_COLUMNS = (2, 4, 8, 16)
CACHE_FILE = OUTPUT_DIR / "sizes_cache.txt"


def optional_metric(path: Path, metric: str) -> dict[int, float]:
    if not path.exists():
        return {}
    return load_serial_metric(path, metric)


def optional_times(path: Path) -> dict[int, float]:
    if not path.exists():
        return {}
    return load_serial_times(path)


def table_density() -> None:
    rows = average_by(OUTPUT_DIR / "density.txt", ("densidad",))
    for row in rows:
        row["flujo"] = row["densidad_real"] * row["velocidad"]

    fields = [
        "densidad",
        "densidad_real",
        "tiempo_s",
        "velocidad",
        "flujo",
        "std_tiempo_s",
        "trials",
    ]
    labels = {
        "densidad": "Densidad",
        "densidad_real": "Densidad real",
        "tiempo_s": "Tiempo prom. (s)",
        "velocidad": "Velocidad",
        "flujo": "Flujo",
        "std_tiempo_s": "Std tiempo",
        "trials": "Rep.",
    }
    write_table_artifacts(
        TABLES_DIR / "tabla_densidad.csv",
        TABLES_DIR / "tabla_densidad.png",
        rows,
        fields,
        "Resultados al variar densidad",
        labels,
    )


def table_serial_times() -> None:
    serial_base = load_serial_times(SERIAL_FILE)
    variants = [
        ("Serial O0", SERIAL_FILE, "tabla_tiempos_serial_o0"),
        ("Serial O3", O3_FILE, "tabla_tiempos_serial_o3"),
    ]
    if CACHE_FILE.exists():
        variants.append(("Serial cache opt.", CACHE_FILE, "tabla_tiempos_serial_cache"))

    fields = ["N", "version", "tiempo_s", "std_tiempo_s", "speedup_vs_serial_o0", "trials"]
    labels = {
        "N": "N",
        "version": "Version",
        "tiempo_s": "Tiempo prom. (s)",
        "std_tiempo_s": "Std tiempo",
        "speedup_vs_serial_o0": "Speedup vs O0",
        "trials": "Rep.",
    }

    combined_rows = []
    for version, path, stem in variants:
        rows = average_by(path, ("N",))
        for row in rows:
            row["version"] = version
            row["speedup_vs_serial_o0"] = serial_base[int(row["N"])] / row["tiempo_s"]
        combined_rows.extend(rows)
        write_table_artifacts(
            TABLES_DIR / f"{stem}.csv",
            TABLES_DIR / f"{stem}.png",
            rows,
            fields,
            f"Promedio de tiempos: {version}",
            labels,
        )

    combined_rows = sorted(combined_rows, key=lambda r: (int(r["N"]), str(r["version"])))
    write_table_artifacts(
        TABLES_DIR / "tabla_tiempos_seriales.csv",
        TABLES_DIR / "tabla_tiempos_seriales.png",
        combined_rows,
        fields,
        "Promedio de tiempos: versiones secuenciales",
        labels,
    )


def table_openmp_times() -> None:
    omp_rows = average_by(OMP_FILE, ("N", "hilos"))
    by_n = {}
    by_threads = {}
    for row in omp_rows:
        by_n.setdefault(int(row["N"]), {})[int(row["hilos"])] = row
        by_threads.setdefault(int(row["hilos"]), []).append(row)

    rows = []
    for n in sorted(by_n):
        row = {"N": n}
        for threads in THREAD_COLUMNS:
            data = by_n[n].get(threads)
            row[f"h{threads}_tiempo_s"] = data["tiempo_s"] if data else ""
        rows.append(row)

    fields = ["N"]
    labels = {"N": "N"}
    for threads in THREAD_COLUMNS:
        fields.append(f"h{threads}_tiempo_s")
        labels[f"h{threads}_tiempo_s"] = f"{threads} hilos (s)"

    write_table_artifacts(
        TABLES_DIR / "tabla_tiempos_openmp.csv",
        TABLES_DIR / "tabla_tiempos_openmp.png",
        rows,
        fields,
        "Promedio de tiempos OpenMP",
        labels,
    )

    single_fields = ["N", "hilos", "tiempo_s", "std_tiempo_s", "trials"]
    single_labels = {
        "N": "N",
        "hilos": "Hilos",
        "tiempo_s": "Tiempo prom. (s)",
        "std_tiempo_s": "Std tiempo",
        "trials": "Rep.",
    }
    for threads in THREAD_COLUMNS:
        thread_rows = sorted(by_threads.get(threads, []), key=lambda r: int(r["N"]))
        if not thread_rows:
            continue
        write_table_artifacts(
            TABLES_DIR / f"tabla_tiempos_openmp_{threads}_hilos.csv",
            TABLES_DIR / f"tabla_tiempos_openmp_{threads}_hilos.png",
            thread_rows,
            single_fields,
            f"Promedio de tiempos OpenMP: {threads} hilos",
            single_labels,
        )


def table_speedups() -> None:
    serial = load_serial_times(SERIAL_FILE)
    o3 = load_serial_times(O3_FILE)
    cache = optional_times(CACHE_FILE)
    omp = load_omp_times(OMP_FILE)

    maps = [serial, o3, omp]
    if cache:
        maps.append(cache)
    sizes = common_sizes(*maps)

    rows = []
    for n in sizes:
        row = {
            "N": n,
            "serial_o0": 1.0,
            "serial_o3": serial[n] / o3[n],
        }
        if cache:
            row["serial_cache"] = serial[n] / cache[n]
        for threads in THREAD_COLUMNS:
            row[f"openmp_{threads}"] = serial[n] / omp[n][threads] if threads in omp[n] else ""
        rows.append(row)

    fields = ["N", "serial_o0", "serial_o3"]
    if cache:
        fields.append("serial_cache")
    fields.extend([f"openmp_{threads}" for threads in THREAD_COLUMNS])

    labels = {
        "N": "N",
        "serial_o0": "Serial O0",
        "serial_o3": "Serial O3",
        "serial_cache": "Cache opt.",
    }
    for threads in THREAD_COLUMNS:
        labels[f"openmp_{threads}"] = f"OpenMP {threads}"

    write_table_artifacts(
        TABLES_DIR / "tabla_speedup_promedio_por_N.csv",
        TABLES_DIR / "tabla_speedup_promedio_por_N.png",
        rows,
        fields,
        "Speedup promedio por tamano",
        labels,
    )

    summary = []
    for field in fields:
        if field == "N":
            continue
        values = [row[field] for row in rows if row.get(field, "") != ""]
        if not values:
            continue
        summary.append(
            {
                "version": labels.get(field, field),
                "speedup_promedio": sum(values) / len(values),
                "speedup_min": min(values),
                "speedup_max": max(values),
                "casos": len(values),
            }
        )

    write_table_artifacts(
        TABLES_DIR / "tabla_speedup_resumen_global.csv",
        TABLES_DIR / "tabla_speedup_resumen_global.png",
        summary,
        ["version", "speedup_promedio", "speedup_min", "speedup_max", "casos"],
        "Resumen global de speedup",
        {
            "version": "Version",
            "speedup_promedio": "Speedup prom.",
            "speedup_min": "Min",
            "speedup_max": "Max",
            "casos": "Casos",
        },
    )


def main() -> None:
    ensure_dirs()
    table_density()
    table_serial_times()
    table_openmp_times()
    table_speedups()


if __name__ == "__main__":
    main()
