#!/usr/bin/env python3
"""Plot OpenMP speedup relative to the serial O0 version."""

from traffic_plot_utils import (
    COLORS,
    PLOTS_DIR,
    TABLES_DIR,
    THREAD_COUNTS,
    apply_common_style,
    common_sizes,
    ensure_dirs,
    load_omp_times,
    load_serial_times,
    save_figure,
    size_labels,
    write_table_artifacts,
)
import matplotlib.pyplot as plt


def main() -> None:
    ensure_dirs()
    serial = load_serial_times()
    omp = load_omp_times()
    sizes = common_sizes(serial, omp)

    fig, ax = plt.subplots(figsize=(12, 7))
    table_rows = []

    for threads in THREAD_COUNTS:
        valid = [n for n in sizes if threads in omp[n]]
        speedups = [serial[n] / omp[n][threads] for n in valid]
        ax.plot(
            valid,
            speedups,
            marker="o",
            linewidth=2.5,
            markersize=8,
            label=f"{threads} hilos",
            color=COLORS[f"openmp_{threads}"],
        )
        for n, speedup in zip(valid, speedups):
            table_rows.append(
                {
                    "N": n,
                    "hilos": threads,
                    "tiempo_serial_s": serial[n],
                    "tiempo_openmp_s": omp[n][threads],
                    "speedup": speedup,
                    "eficiencia": speedup / threads,
                }
            )

    ax.axhline(y=1.0, color="#555555", linewidth=1.5, linestyle="--", label="Serial O0")
    ax.set_xscale("log")
    ax.set_xticks(sizes)
    ax.set_xticklabels(size_labels(sizes))
    apply_common_style(
        ax,
        "Speedup OpenMP respecto a serial O0",
        "N celdas",
        "Speedup",
    )

    save_figure(fig, PLOTS_DIR / "traffic_speedup_openmp_threads.png")

    out_csv = TABLES_DIR / "traffic_speedup_openmp_threads.csv"
    write_table_artifacts(
        out_csv,
        TABLES_DIR / "traffic_speedup_openmp_threads.png",
        table_rows,
        ["N", "hilos", "tiempo_serial_s", "tiempo_openmp_s", "speedup", "eficiencia"],
        "Speedup OpenMP por hilos",
        {
            "N": "N",
            "hilos": "Hilos",
            "tiempo_serial_s": "Serial (s)",
            "tiempo_openmp_s": "OpenMP (s)",
            "speedup": "Speedup",
            "eficiencia": "Eficiencia",
        },
    )


if __name__ == "__main__":
    main()
