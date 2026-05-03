#!/usr/bin/env python3
"""Generate tables and plots from Cachegrind memory/cache profiling reports."""

from __future__ import annotations

import re

from traffic_plot_utils import (
    BASE_DIR,
    PLOTS_DIR,
    TABLES_DIR,
    ensure_dirs,
    save_figure,
    write_table_artifacts,
)

import matplotlib.pyplot as plt
import numpy as np


PROFILING_DIR = BASE_DIR / "profiling"
REPORTS = (
    (
        "Serial O0",
        (PROFILING_DIR / "cachegrind_serial_mem_report.txt", PROFILING_DIR / "serial_mem.txt"),
        "serial_o0",
    ),
    (
        "Serial O3",
        (PROFILING_DIR / "cachegrind_o3_mem_report.txt", PROFILING_DIR / "o3_mem.txt"),
        "serial_o3",
    ),
    (
        "Serial cache opt.",
        (PROFILING_DIR / "cachegrind_cache_mem_report.txt", PROFILING_DIR / "cache_mem.txt"),
        "serial_cache",
    ),
)

SUMMARY_VALUES = ("Ir", "Dr", "Dw", "D1mr", "D1mw", "DLmr", "DLmw")


def parse_int(value: str) -> int:
    return int(value.replace(",", ""))


def resolve_existing_path(paths) -> object | None:
    if isinstance(paths, (tuple, list)):
        for path in paths:
            if path.exists():
                return path
        return None
    return paths if paths.exists() else None


def parse_cachegrind_summary(paths, version: str, slug: str = "") -> dict[str, object] | None:
    path = resolve_existing_path(paths)
    if path is None:
        print(f"Saltando {version}: no existe ningun reporte esperado")
        return None

    metric_names = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "PROGRAM TOTALS" not in line:
            header_metrics = re.findall(r"\b(Ir|Dr|Dw|D1mr|D1mw|DLmr|DLmw)_+", line)
            if header_metrics:
                metric_names = header_metrics
            continue

        if "PROGRAM TOTALS" not in line:
            continue

        values = re.findall(r"([\d,]+)\s+\(", line)
        if not values:
            raise ValueError(f"No se pudieron extraer metricas de PROGRAM TOTALS en {path}")
        if not metric_names:
            metric_names = list(SUMMARY_VALUES[: len(values)])

        row = {"version": version, "slug": slug}
        for key, value in zip(metric_names, values):
            row[key] = parse_int(value)

        if {"Dr", "Dw", "D1mr", "D1mw", "DLmr", "DLmw"}.issubset(row):
            row["D_refs"] = row["Dr"] + row["Dw"]
            row["D1_misses"] = row["D1mr"] + row["D1mw"]
            row["DL_misses"] = row["DLmr"] + row["DLmw"]
            row["D1_miss_rate_pct"] = 100.0 * row["D1_misses"] / row["D_refs"]
            row["DL_miss_rate_pct"] = 100.0 * row["DL_misses"] / row["D_refs"]
            row["read_D1_miss_rate_pct"] = 100.0 * row["D1mr"] / row["Dr"]
            row["write_D1_miss_rate_pct"] = 100.0 * row["D1mw"] / row["Dw"]
        else:
            print(
                f"Advertencia: {path.name} solo contiene {', '.join(metric_names)}. "
                "Regenera con cg_annotate --show=Ir,Dr,Dw,D1mr,D1mw,DLmr,DLmw para tablas completas."
            )
        return row

    raise ValueError(f"No se encontro PROGRAM TOTALS en {path}")


def load_rows() -> list[dict[str, object]]:
    rows = []
    for version, paths, slug in REPORTS:
        row = parse_cachegrind_summary(paths, version, slug)
        if row is not None:
            rows.append(row)
    return rows


def write_tables(rows: list[dict[str, object]]) -> None:
    has_full_cache_metrics = all("D_refs" in row for row in rows)
    fields = ["version", "Ir"]
    if has_full_cache_metrics:
        fields.extend(
            [
                "Dr",
                "Dw",
                "D_refs",
                "D1mr",
                "D1mw",
                "D1_misses",
                "DLmr",
                "DLmw",
                "DL_misses",
                "D1_miss_rate_pct",
                "DL_miss_rate_pct",
            ]
        )
    labels = {
        "version": "Version",
        "Ir": "Instr.",
        "Dr": "Lecturas",
        "Dw": "Escrituras",
        "D_refs": "Refs. datos",
        "D1mr": "L1D miss lectura",
        "D1mw": "L1D miss escritura",
        "D1_misses": "L1D misses",
        "DLmr": "LL miss lectura",
        "DLmw": "LL miss escritura",
        "DL_misses": "LL misses",
        "D1_miss_rate_pct": "L1D miss %",
        "DL_miss_rate_pct": "LL miss %",
    }
    write_table_artifacts(
        TABLES_DIR / "tabla_memory_profiling_cachegrind.csv",
        TABLES_DIR / "tabla_memory_profiling_cachegrind.png",
        rows,
        fields,
        "Profiling de memoria/cache con Cachegrind",
        labels,
    )

    for row in rows:
        slug = str(row.get("slug", "version"))
        single_row = [row]
        write_table_artifacts(
            TABLES_DIR / f"tabla_memory_profiling_{slug}.csv",
            TABLES_DIR / f"tabla_memory_profiling_{slug}.png",
            single_row,
            fields,
            f"Profiling memoria/cache: {row['version']}",
            labels,
        )

    if has_full_cache_metrics:
        compact_fields = [
            "version",
            "D_refs",
            "D1_misses",
            "DL_misses",
            "D1_miss_rate_pct",
            "DL_miss_rate_pct",
        ]
        write_table_artifacts(
            TABLES_DIR / "tabla_memory_profiling_resumen.csv",
            TABLES_DIR / "tabla_memory_profiling_resumen.png",
            rows,
            compact_fields,
            "Resumen de misses de cache",
            labels,
        )


def plot_memory_bars(rows: list[dict[str, object]]) -> None:
    if not all("D_refs" in row for row in rows):
        print("Saltando grafica de eventos de cache: faltan metricas Dr/Dw/D1/DL completas.")
        return
    versions = [str(row["version"]) for row in rows]
    x = np.arange(len(versions))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width, [row["D_refs"] for row in rows], width, label="Refs. datos", color="#1f77b4")
    ax.bar(x, [row["D1_misses"] for row in rows], width, label="L1D misses", color="#ff7f0e")
    ax.bar(x + width, [row["DL_misses"] for row in rows], width, label="LL misses", color="#2ca02c")

    ax.set_title("Referencias y misses de cache por variante", fontsize=14, fontweight="bold")
    ax.set_xlabel("Variante", fontsize=12)
    ax.set_ylabel("Conteo de eventos", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(versions)
    ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=10)
    save_figure(fig, PLOTS_DIR / "memory_cache_eventos_por_variante.png")


def plot_miss_rates(rows: list[dict[str, object]]) -> None:
    if not all("D1_miss_rate_pct" in row for row in rows):
        print("Saltando grafica de miss rates: faltan metricas Dr/Dw/D1/DL completas.")
        return
    versions = [str(row["version"]) for row in rows]
    x = np.arange(len(versions))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.bar(
        x - width / 2,
        [row["D1_miss_rate_pct"] for row in rows],
        width,
        label="L1D miss rate",
        color="#d62728",
    )
    ax.bar(
        x + width / 2,
        [row["DL_miss_rate_pct"] for row in rows],
        width,
        label="LL miss rate",
        color="#9467bd",
    )

    ax.set_title("Tasa de misses de cache por variante", fontsize=14, fontweight="bold")
    ax.set_xlabel("Variante", fontsize=12)
    ax.set_ylabel("Miss rate sobre referencias a datos (%)", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(versions)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=10)
    save_figure(fig, PLOTS_DIR / "memory_cache_miss_rates_por_variante.png")


def main() -> None:
    ensure_dirs()
    rows = load_rows()
    if not rows:
        raise ValueError("No se encontraron reportes de Cachegrind para procesar.")
    write_tables(rows)
    plot_memory_bars(rows)
    plot_miss_rates(rows)


if __name__ == "__main__":
    main()
