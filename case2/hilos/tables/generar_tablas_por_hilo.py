from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import csv

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
HILOS_INPUT = BASE_DIR.parent / "output" / "output_hilos.txt"
SECUENCIAL_INPUT = BASE_DIR.parent.parent / "secuencial" / "output" / "times_secuencial.txt"
THREAD_COUNTS = (2, 4, 8, 16)


def load_hilos_wall_times(path: Path) -> dict[int, dict[int, list[float]]]:
    data: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    with path.open("r", encoding="utf-8") as file:
        header_skipped = False
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()
            if not line:
                continue

            if not header_skipped:
                header_skipped = True
                continue

            parts = line.split()
            if len(parts) != 9:
                raise ValueError(
                    f"Formato inesperado en {path.name}:{line_number}: {line}"
                )

            n_value = int(parts[0])
            threads = int(parts[1])
            wall_s = float(parts[3])

            if threads in THREAD_COUNTS:
                data[threads][n_value].append(wall_s)

    return {thread: dict(sorted(by_n.items())) for thread, by_n in data.items()}


def load_sequential_means(path: Path) -> dict[int, float]:
    grouped: dict[int, list[float]] = defaultdict(list)

    with path.open("r", encoding="utf-8") as file:
        next(file)
        for line_number, raw_line in enumerate(file, start=2):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) != 9:
                raise ValueError(
                    f"Formato inesperado en {path.name}:{line_number}: {line}"
                )

            n_value = int(parts[0])
            wall_s = float(parts[3])
            grouped[n_value].append(wall_s)

    return {
        n_value: (sum(times) / len(times))
        for n_value, times in sorted(grouped.items())
    }


def build_round_table(by_n: dict[int, list[float]]) -> tuple[list[int], list[list[str]]]:
    sizes = sorted(by_n.keys())
    rounds = min(len(by_n[n_value]) for n_value in sizes)

    rows: list[list[str]] = []
    for round_index in range(rounds):
        row = [str(round_index + 1)]
        for n_value in sizes:
            row.append(f"{by_n[n_value][round_index]:.6f}")
        rows.append(row)

    return sizes, rows


def compute_means(by_n: dict[int, list[float]], sizes: list[int]) -> dict[int, float]:
    return {n_value: sum(by_n[n_value]) / len(by_n[n_value]) for n_value in sizes}


def compute_speedups(
    hilos_means: dict[int, float],
    secuencial_means: dict[int, float],
    sizes: list[int],
) -> dict[int, float]:
    speedups: dict[int, float] = {}
    for n_value in sizes:
        base = secuencial_means.get(n_value)
        if base is None:
            raise ValueError(f"No existe N={n_value} en tiempos secuenciales")

        speedups[n_value] = base / hilos_means[n_value]

    return speedups


def write_csv(
    thread_count: int,
    sizes: list[int],
    rows: list[list[str]],
    means: dict[int, float],
    speedups: dict[int, float],
) -> Path:
    out_csv = BASE_DIR / f"tabla_hilos_{thread_count}.csv"
    headers = ["Ronda"] + [str(n_value) for n_value in sizes]

    with out_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)
        writer.writerow(["Promedio"] + [f"{means[n_value]:.6f}" for n_value in sizes])
        writer.writerow(["Speedup (vs secuencial)"] + [f"{speedups[n_value]:.6f}" for n_value in sizes])

    return out_csv


def write_png(thread_count: int, csv_path: Path) -> Path:
    out_png = BASE_DIR / f"tabla_hilos_{thread_count}.png"

    with csv_path.open("r", encoding="utf-8") as file:
        reader = csv.reader(file)
        all_rows = list(reader)

    headers = all_rows[0]
    data_rows = all_rows[1:]

    n_rows = len(data_rows) + 1
    n_cols = len(headers)
    fig_width = max(12, n_cols * 1.3)
    fig_height = max(6, n_rows * 0.45)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=data_rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.35)

    for col_idx in range(n_cols):
        cell = table[(0, col_idx)]
        cell.set_facecolor("#D9EAF7")
        cell.set_text_props(weight="bold")

    for row_idx, row in enumerate(data_rows, start=1):
        label = row[0]
        if label.startswith("Promedio") or label.startswith("Speedup"):
            for col_idx in range(n_cols):
                cell = table[(row_idx, col_idx)]
                cell.set_facecolor("#F4F4F4")
                if col_idx == 0:
                    cell.set_text_props(weight="bold")

    plt.title(f"Tiempos por ronda - {thread_count} hilos", fontsize=13, pad=16)
    fig.tight_layout()
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    return out_png


def main() -> None:
    if not HILOS_INPUT.exists():
        raise FileNotFoundError(f"No existe archivo de hilos: {HILOS_INPUT}")

    if not SECUENCIAL_INPUT.exists():
        raise FileNotFoundError(f"No existe archivo secuencial: {SECUENCIAL_INPUT}")

    hilos_data = load_hilos_wall_times(HILOS_INPUT)
    secuencial_means = load_sequential_means(SECUENCIAL_INPUT)

    for thread_count in THREAD_COUNTS:
        by_n = hilos_data.get(thread_count)
        if not by_n:
            print(f"Sin datos para {thread_count} hilos, se omite")
            continue

        sizes, rows = build_round_table(by_n)
        means = compute_means(by_n, sizes)
        speedups = compute_speedups(means, secuencial_means, sizes)

        out_csv = write_csv(thread_count, sizes, rows, means, speedups)
        out_png = write_png(thread_count, out_csv)

        print(f"CSV generado: {out_csv}")
        print(f"PNG generado: {out_png}")


if __name__ == "__main__":
    main()
