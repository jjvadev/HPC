#!/usr/bin/env python3
"""Plot O3 speedup relative to the serial O0 version."""

from traffic_plot_utils import (
    COLORS,
    O3_FILE,
    PLOTS_DIR,
    TABLES_DIR,
    apply_common_style,
    common_sizes,
    ensure_dirs,
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
    sizes = common_sizes(serial, o3)

    speedups = [serial[n] / o3[n] for n in sizes]

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.axhline(y=1.0, color=COLORS["serial"], linewidth=2.2, label="Serial O0")
    ax.plot(
        sizes,
        speedups,
        marker="^",
        linewidth=2.5,
        markersize=8,
        label="Serial O3",
        color=COLORS["o3"],
    )
    ax.set_xscale("log")
    ax.set_xticks(sizes)
    ax.set_xticklabels(size_labels(sizes))
    apply_common_style(
        ax,
        "Speedup de O3 respecto a serial O0",
        "N celdas",
        "Speedup",
    )

    save_figure(fig, PLOTS_DIR / "traffic_speedup_o3.png")

    rows = [
        {
            "N": n,
            "tiempo_serial_s": serial[n],
            "tiempo_o3_s": o3[n],
            "speedup_o3": serial[n] / o3[n],
        }
        for n in sizes
    ]
    out_csv = TABLES_DIR / "traffic_speedup_o3.csv"
    write_table_artifacts(
        out_csv,
        TABLES_DIR / "traffic_speedup_o3.png",
        rows,
        ["N", "tiempo_serial_s", "tiempo_o3_s", "speedup_o3"],
        "Speedup O3",
        {
            "N": "N",
            "tiempo_serial_s": "Serial O0 (s)",
            "tiempo_o3_s": "Serial O3 (s)",
            "speedup_o3": "Speedup O3",
        },
    )


if __name__ == "__main__":
    main()
