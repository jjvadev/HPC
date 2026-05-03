#!/usr/bin/env python3
"""Plot O3 and OpenMP speedups together relative to serial O0."""

from traffic_plot_utils import (
    COLORS,
    O3_FILE,
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
from traffic_plot_utils import load_serial_times as load_times
import matplotlib.pyplot as plt


def main() -> None:
    ensure_dirs()
    serial = load_serial_times()
    o3 = load_times(O3_FILE)
    omp = load_omp_times()
    sizes = common_sizes(serial, o3, omp)

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.axhline(y=1.0, color=COLORS["serial"], linewidth=2.0, label="Serial O0")
    ax.plot(
        sizes,
        [serial[n] / o3[n] for n in sizes],
        marker="^",
        linewidth=2.5,
        markersize=8,
        label="Serial O3",
        color=COLORS["o3"],
    )

    for threads in THREAD_COUNTS:
        valid = [n for n in sizes if threads in omp[n]]
        ax.plot(
            valid,
            [serial[n] / omp[n][threads] for n in valid],
            marker="o",
            linewidth=2.2,
            markersize=7,
            label=f"OpenMP {threads} hilos",
            color=COLORS[f"openmp_{threads}"],
        )

    ax.set_xscale("log")
    ax.set_xticks(sizes)
    ax.set_xticklabels(size_labels(sizes))
    apply_common_style(
        ax,
        "Comparacion global de speedup",
        "N celdas",
        "Speedup respecto a serial O0",
    )

    save_figure(fig, PLOTS_DIR / "traffic_speedup_global_o3_openmp.png")

    table_rows = []
    for n in sizes:
        row = {
            "N": n,
            "speedup_serial_o0": 1.0,
            "speedup_o3": serial[n] / o3[n],
        }
        for threads in THREAD_COUNTS:
            row[f"speedup_openmp_{threads}"] = (
                serial[n] / omp[n][threads] if threads in omp[n] else ""
            )
        table_rows.append(row)

    fields = ["N", "speedup_serial_o0", "speedup_o3"]
    fields.extend([f"speedup_openmp_{threads}" for threads in THREAD_COUNTS])
    out_csv = TABLES_DIR / "traffic_speedup_global.csv"
    labels = {
        "N": "N",
        "speedup_serial_o0": "Serial O0",
        "speedup_o3": "Serial O3",
    }
    for threads in THREAD_COUNTS:
        labels[f"speedup_openmp_{threads}"] = f"OpenMP {threads}"
    write_table_artifacts(
        out_csv,
        TABLES_DIR / "traffic_speedup_global.png",
        table_rows,
        fields,
        "Comparacion global de speedup",
        labels,
    )


if __name__ == "__main__":
    main()
