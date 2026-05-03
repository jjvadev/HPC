#!/usr/bin/env python3
"""Plot traffic model behavior when varying density."""

from traffic_plot_utils import (
    COLORS,
    DENSITY_FILE,
    PLOTS_DIR,
    TABLES_DIR,
    apply_common_style,
    average_by,
    ensure_dirs,
    save_figure,
    write_table_artifacts,
)
import matplotlib.pyplot as plt


def main() -> None:
    ensure_dirs()
    rows = average_by(DENSITY_FILE, ("densidad",))

    for row in rows:
        row["flujo"] = row["densidad_real"] * row["velocidad"]

    densities = [row["densidad"] for row in rows]
    velocities = [row["velocidad"] for row in rows]
    flows = [row["flujo"] for row in rows]
    throughput = [row["mceldas_s"] for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8))

    axes[0].plot(
        densities,
        velocities,
        marker="o",
        linewidth=2.5,
        markersize=8,
        color=COLORS["density"],
        label="Velocidad promedio",
    )
    axes[0].plot(
        densities,
        flows,
        marker="s",
        linewidth=2.5,
        markersize=8,
        color=COLORS["flow"],
        label="Flujo = densidad x velocidad",
    )
    apply_common_style(
        axes[0],
        "Modelo de trafico: velocidad y flujo",
        "Densidad inicial",
        "Valor promedio",
    )

    axes[1].plot(
        densities,
        throughput,
        marker="^",
        linewidth=2.5,
        markersize=8,
        color="#2ca02c",
        label="MCeldas/s",
    )
    apply_common_style(
        axes[1],
        "Rendimiento al variar densidad",
        "Densidad inicial",
        "Millones de celdas por segundo",
    )

    out_png = PLOTS_DIR / "traffic_density_velocity_flow.png"
    save_figure(fig, out_png)

    out_csv = TABLES_DIR / "traffic_density_summary.csv"
    write_table_artifacts(
        out_csv,
        TABLES_DIR / "traffic_density_summary.png",
        rows,
        [
            "densidad",
            "densidad_real",
            "tiempo_s",
            "velocidad",
            "flujo",
            "std_tiempo_s",
            "trials",
        ],
        "Resumen de densidad",
        {
            "densidad": "Densidad",
            "densidad_real": "Densidad real",
            "tiempo_s": "Tiempo (s)",
            "velocidad": "Velocidad",
            "flujo": "Flujo",
            "std_tiempo_s": "Std tiempo",
            "trials": "Rep.",
        },
    )


if __name__ == "__main__":
    main()
