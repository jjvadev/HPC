#!/usr/bin/env python3
"""Plot time and throughput when varying road size."""

from traffic_plot_utils import (
    COLORS,
    O3_FILE,
    OMP_FILE,
    PLOTS_DIR,
    SERIAL_FILE,
    TABLES_DIR,
    THREAD_COUNTS,
    apply_common_style,
    average_by,
    common_sizes,
    ensure_dirs,
    save_figure,
    size_labels,
    write_table_artifacts,
)
import matplotlib.pyplot as plt


def by_size(rows, metric):
    return {int(row["N"]): float(row[metric]) for row in rows}


def by_size_threads(rows, metric):
    result = {}
    for row in rows:
        result.setdefault(int(row["N"]), {})[int(row["hilos"])] = float(row[metric])
    return result


def main() -> None:
    ensure_dirs()

    serial_rows = average_by(SERIAL_FILE, ("N",))
    o3_rows = average_by(O3_FILE, ("N",))
    omp_rows = average_by(OMP_FILE, ("N", "hilos"))

    serial_time = by_size(serial_rows, "tiempo_s")
    o3_time = by_size(o3_rows, "tiempo_s")
    omp_time = by_size_threads(omp_rows, "tiempo_s")
    serial_rate = by_size(serial_rows, "mceldas_s")
    o3_rate = by_size(o3_rows, "mceldas_s")
    omp_rate = by_size_threads(omp_rows, "mceldas_s")

    sizes = common_sizes(serial_time, o3_time, omp_time)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    axes[0].plot(sizes, [serial_time[n] for n in sizes], marker="o", linewidth=2.2,
                 label="Serial O0", color=COLORS["serial"])
    axes[0].plot(sizes, [o3_time[n] for n in sizes], marker="^", linewidth=2.2,
                 label="Serial O3", color=COLORS["o3"])
    for threads in THREAD_COUNTS:
        valid = [n for n in sizes if threads in omp_time[n]]
        axes[0].plot(
            valid,
            [omp_time[n][threads] for n in valid],
            marker="s",
            linewidth=1.8,
            label=f"OpenMP {threads} hilos",
            color=COLORS[f"openmp_{threads}"],
        )
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xticks(sizes)
    axes[0].set_xticklabels(size_labels(sizes))
    apply_common_style(axes[0], "Tiempo de ejecucion por tamano", "N celdas", "Tiempo promedio (s)")

    axes[1].plot(sizes, [serial_rate[n] for n in sizes], marker="o", linewidth=2.2,
                 label="Serial O0", color=COLORS["serial"])
    axes[1].plot(sizes, [o3_rate[n] for n in sizes], marker="^", linewidth=2.2,
                 label="Serial O3", color=COLORS["o3"])
    for threads in THREAD_COUNTS:
        valid = [n for n in sizes if threads in omp_rate[n]]
        axes[1].plot(
            valid,
            [omp_rate[n][threads] for n in valid],
            marker="s",
            linewidth=1.8,
            label=f"OpenMP {threads} hilos",
            color=COLORS[f"openmp_{threads}"],
        )
    axes[1].set_xscale("log")
    axes[1].set_xticks(sizes)
    axes[1].set_xticklabels(size_labels(sizes))
    apply_common_style(
        axes[1],
        "Rendimiento por tamano",
        "N celdas",
        "Millones de celdas por segundo",
    )

    save_figure(fig, PLOTS_DIR / "traffic_size_time_throughput.png")

    table_rows = []
    for n in sizes:
        row = {
            "N": n,
            "serial_tiempo_s": serial_time[n],
            "o3_tiempo_s": o3_time[n],
        }
        for threads in THREAD_COUNTS:
            row[f"openmp_{threads}_tiempo_s"] = omp_time[n].get(threads, "")
        table_rows.append(row)

    fields = [
        "N",
        "serial_tiempo_s",
        "o3_tiempo_s",
    ]
    for threads in THREAD_COUNTS:
        fields.append(f"openmp_{threads}_tiempo_s")
    out_csv = TABLES_DIR / "traffic_size_performance_summary.csv"
    labels = {
        "N": "N",
        "serial_tiempo_s": "Serial O0 (s)",
        "o3_tiempo_s": "Serial O3 (s)",
    }
    for threads in THREAD_COUNTS:
        labels[f"openmp_{threads}_tiempo_s"] = f"OMP {threads} (s)"
    write_table_artifacts(
        out_csv,
        TABLES_DIR / "traffic_size_performance_summary.png",
        table_rows,
        fields,
        "Resumen de rendimiento por tamano",
        labels,
    )


if __name__ == "__main__":
    main()
