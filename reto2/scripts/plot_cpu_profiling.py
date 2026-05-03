#!/usr/bin/env python3
"""Plot CPU profiling results extracted from gprof reports."""

from __future__ import annotations

import csv
from collections import defaultdict

from traffic_plot_utils import PLOTS_DIR, ensure_dirs, save_figure

import matplotlib.pyplot as plt
import numpy as np

from generate_cpu_profiling_tables import REPORTS, parse_gprof_flat_profile


TOP_N_FUNCTIONS = 6


def load_rows() -> list[dict[str, object]]:
    rows = []
    for version, path, _ in REPORTS:
        rows.extend(parse_gprof_flat_profile(path, version))
    return rows


def plot_total_cpu_by_variant(rows: list[dict[str, object]]) -> None:
    totals = defaultdict(float)
    for row in rows:
        totals[str(row["version"])] += float(row["segundos_propios"])

    wanted = ["Serial O0", "Serial O3", "Serial cache opt."]
    versions = [version for version in wanted if version in totals]
    values = [totals[version] for version in versions]

    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.bar(versions, values, color=["#1f77b4", "#2ca02c", "#ff7f0e"][: len(versions)])
    ax.set_title("Tiempo CPU total por variante (gprof)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Variante", fontsize=12)
    ax.set_ylabel("Tiempo propio acumulado (s)", fontsize=12)
    ax.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f} s",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    save_figure(fig, PLOTS_DIR / "cpu_tiempo_total_por_variante.png")


def plot_top_functions(rows: list[dict[str, object]]) -> None:
    by_function = defaultdict(float)
    by_version_function = defaultdict(float)

    for row in rows:
        version = str(row["version"])
        function = str(row["funcion"])
        seconds = float(row["segundos_propios"])
        by_function[function] += seconds
        by_version_function[(version, function)] += seconds

    top_functions = [
        function
        for function, _ in sorted(by_function.items(), key=lambda item: item[1], reverse=True)[
            :TOP_N_FUNCTIONS
        ]
    ]

    wanted_versions = ["Serial O0", "Serial O3", "Serial cache opt."]
    versions = sorted({str(row["version"]) for row in rows}, key=wanted_versions.index)
    x = np.arange(len(top_functions))
    width = 0.8 / max(len(versions), 1)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = {
        "Serial O0": "#1f77b4",
        "Serial O3": "#2ca02c",
        "Serial cache opt.": "#ff7f0e",
    }

    for idx, version in enumerate(versions):
        offset = (idx - (len(versions) - 1) / 2) * width
        values = [by_version_function[(version, function)] for function in top_functions]
        ax.bar(
            x + offset,
            values,
            width=width,
            label=version,
            color=colors.get(version),
        )

    ax.set_title("Funciones mas costosas por tiempo CPU propio", fontsize=14, fontweight="bold")
    ax.set_xlabel("Funcion", fontsize=12)
    ax.set_ylabel("Tiempo propio (s)", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(top_functions, rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=10)

    save_figure(fig, PLOTS_DIR / "cpu_funciones_mas_costosas.png")


def main() -> None:
    ensure_dirs()
    rows = load_rows()
    if not rows:
        raise ValueError("No se encontraron reportes de CPU profiling para graficar.")
    plot_total_cpu_by_variant(rows)
    plot_top_functions(rows)


if __name__ == "__main__":
    main()
