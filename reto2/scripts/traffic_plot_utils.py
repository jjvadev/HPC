#!/usr/bin/env python3
"""Helpers for plotting reto2 traffic model benchmark results."""

from __future__ import annotations

from pathlib import Path
import csv
import math
import os
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
TABLES_DIR = OUTPUT_DIR / "tables"
CACHE_DIR = OUTPUT_DIR / ".cache"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SERIAL_FILE = OUTPUT_DIR / "sizes_serial.txt"
O3_FILE = OUTPUT_DIR / "sizes_serial_o3.txt"
OMP_FILE = OUTPUT_DIR / "sizes_omp.txt"
DENSITY_FILE = OUTPUT_DIR / "density.txt"


THREAD_COUNTS = (2, 4, 8, 16)
COLORS = {
    "serial": "#1f77b4",
    "o3": "#2ca02c",
    "openmp_2": "#ff7f0e",
    "openmp_4": "#d62728",
    "openmp_8": "#9467bd",
    "openmp_16": "#8c564b",
    "density": "#1f77b4",
    "flow": "#ff7f0e",
}


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de resultados: {path}")

    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def as_int(row: dict[str, str], key: str) -> int:
    return int(float(row[key]))


def as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def average_by(path: Path, keys: tuple[str, ...]) -> list[dict[str, float]]:
    rows = read_rows(path)
    grouped: dict[tuple, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        group_key = tuple(row[k] for k in keys)
        grouped[group_key].append(row)

    averaged = []
    for group_key, group_rows in grouped.items():
        item: dict[str, float] = {}
        for i, key in enumerate(keys):
            if key in {"N", "hilos", "pasos", "trial"}:
                item[key] = int(float(group_key[i]))
            else:
                item[key] = float(group_key[i])

        for metric in ("densidad_real", "tiempo_s", "mceldas_s", "velocidad"):
            item[metric] = float(np.mean([as_float(row, metric) for row in group_rows]))

        item["std_tiempo_s"] = float(np.std([as_float(row, "tiempo_s") for row in group_rows], ddof=0))
        item["std_mceldas_s"] = float(np.std([as_float(row, "mceldas_s") for row in group_rows], ddof=0))
        item["trials"] = len(group_rows)
        averaged.append(item)

    return sorted(averaged, key=lambda r: tuple(r[k] for k in keys))


def write_csv(path: Path, rows: list[dict[str, float]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def format_cell(value) -> str:
    if value == "" or value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    if isinstance(value, float):
        abs_value = abs(value)
        if abs_value >= 1000:
            return f"{value:,.2f}".replace(",", ".")
        if abs_value >= 100:
            return f"{value:.2f}"
        if abs_value >= 10:
            return f"{value:.3f}"
        return f"{value:.4f}"
    return str(value)


def render_table_png(
    path: Path,
    rows: list[dict[str, float]],
    columns: list[tuple[str, str]],
    title: str,
) -> None:
    if not rows:
        raise ValueError(f"No hay filas para generar la tabla: {title}")

    labels = [label for _, label in columns]
    values = [[format_cell(row.get(key, "")) for key, _ in columns] for row in rows]

    width = max(10.0, min(22.0, 1.55 * len(columns)))
    height = max(2.8, 0.55 * len(rows) + 1.6)
    fig, ax = plt.subplots(figsize=(width, height))
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)

    table = ax.table(
        cellText=values,
        colLabels=labels,
        cellLoc="center",
        colLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.35)

    for (row_idx, _), cell in table.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if row_idx == 0:
            cell.set_facecolor("#2f3b52")
            cell.set_text_props(color="white", weight="bold")
        elif row_idx % 2 == 0:
            cell.set_facecolor("#f4f6f8")
        else:
            cell.set_facecolor("white")

    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Tabla PNG guardada: {path}")


def write_table_artifacts(
    csv_path: Path,
    png_path: Path,
    rows: list[dict[str, float]],
    fieldnames: list[str],
    title: str,
    labels: dict[str, str] | None = None,
) -> None:
    write_csv(csv_path, rows, fieldnames)
    print(f"Tabla CSV guardada: {csv_path}")
    label_map = labels or {}
    render_table_png(
        png_path,
        rows,
        [(field, label_map.get(field, field)) for field in fieldnames],
        title,
    )


def load_serial_times(path: Path = SERIAL_FILE) -> dict[int, float]:
    rows = average_by(path, ("N",))
    return {int(row["N"]): float(row["tiempo_s"]) for row in rows}


def load_serial_metric(path: Path, metric: str) -> dict[int, float]:
    rows = average_by(path, ("N",))
    return {int(row["N"]): float(row[metric]) for row in rows}


def load_omp_times(path: Path = OMP_FILE) -> dict[int, dict[int, float]]:
    rows = average_by(path, ("N", "hilos"))
    result: dict[int, dict[int, float]] = defaultdict(dict)
    for row in rows:
        result[int(row["N"])][int(row["hilos"])] = float(row["tiempo_s"])
    return dict(result)


def common_sizes(*maps: dict[int, object]) -> list[int]:
    if not maps:
        return []
    sizes = set(maps[0].keys())
    for mapping in maps[1:]:
        sizes &= set(mapping.keys())
    return sorted(sizes)


def size_labels(sizes: list[int]) -> list[str]:
    labels = []
    for n in sizes:
        exponent = math.log10(n) if n > 0 else 0
        if abs(exponent - round(exponent)) < 1e-9:
            labels.append(f"$10^{int(round(exponent))}$")
        else:
            labels.append(f"{n:,}".replace(",", "."))
    return labels


def apply_common_style(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10, loc="best")


def save_figure(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    print(f"Grafica guardada: {path}")
