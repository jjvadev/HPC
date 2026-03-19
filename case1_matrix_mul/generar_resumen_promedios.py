from __future__ import annotations

from pathlib import Path
import csv

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "resumen"
OUTPUT_CSV = OUTPUT_DIR / "tabla_resumen_promedios.csv"
OUTPUT_PNG = OUTPUT_DIR / "tabla_resumen_promedios.png"

SOURCES: list[tuple[str, Path]] = [
    (
        "Secuencial",
        BASE_DIR / "secuencial" / "output" / "tables" / "tabla_secuencial.csv",
    ),
    (
        "Transpuesta",
        BASE_DIR
        / "secuencial"
        / "output"
        / "tables"
        / "tabla_secuencia_transpuesta.csv",
    ),
    (
        "O3",
        BASE_DIR / "secuencial" / "output" / "tables" / "tabla_secuencial_o3.csv",
    ),
    ("Hilos 2", BASE_DIR / "hilos" / "tables" / "tabla_hilos_2.csv"),
    ("Hilos 4", BASE_DIR / "hilos" / "tables" / "tabla_hilos_4.csv"),
    ("Hilos 8", BASE_DIR / "hilos" / "tables" / "tabla_hilos_8.csv"),
    ("Hilos 16", BASE_DIR / "hilos" / "tables" / "tabla_hilos_16.csv"),
    ("Procesos 2", BASE_DIR / "procesos" / "tables" / "tabla_procesos_2.csv"),
    ("Procesos 4", BASE_DIR / "procesos" / "tables" / "tabla_procesos_4.csv"),
    ("Procesos 8", BASE_DIR / "procesos" / "tables" / "tabla_procesos_8.csv"),
    ("Procesos 16", BASE_DIR / "procesos" / "tables" / "tabla_procesos_16.csv"),
]


def read_promedio_row(csv_path: Path) -> tuple[list[str], dict[str, float]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe archivo: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))

    if not rows:
        raise ValueError(f"CSV vacio: {csv_path}")

    headers = [cell.strip() for cell in rows[0]]
    if len(headers) < 2:
        raise ValueError(f"Encabezado invalido en {csv_path}")

    promedio_values: list[str] | None = None
    for row in rows[1:]:
        if not row:
            continue

        first = row[0].strip().lower()
        if first.startswith("promedio"):
            promedio_values = row
            break

    if promedio_values is None:
        raise ValueError(f"No se encontro la fila de promedio en: {csv_path}")

    matrix_sizes = headers[1:]
    if len(promedio_values) < len(headers):
        raise ValueError(f"Fila promedio incompleta en: {csv_path}")

    promedio_by_size: dict[str, float] = {}
    for i, size in enumerate(matrix_sizes, start=1):
        promedio_by_size[size] = float(promedio_values[i])

    return matrix_sizes, promedio_by_size


def write_summary_csv(sizes: list[str], summary_rows: list[list[str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Prueba"] + sizes)
        writer.writerows(summary_rows)


def write_summary_png() -> None:
    with OUTPUT_CSV.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))

    headers = rows[0]
    data_rows = rows[1:]

    n_rows = len(data_rows) + 1
    n_cols = len(headers)
    fig_width = max(12, n_cols * 1.35)
    fig_height = max(6, n_rows * 0.52)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=data_rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 1.38)

    for col_idx in range(n_cols):
        cell = table[(0, col_idx)]
        cell.set_facecolor("#D9EAF7")
        cell.set_text_props(weight="bold")

    for row_idx in range(1, n_rows):
        label_cell = table[(row_idx, 0)]
        label_cell.set_text_props(weight="bold")
        if row_idx % 2 == 0:
            for col_idx in range(n_cols):
                table[(row_idx, col_idx)].set_facecolor("#F7F7F7")

    plt.title("Tabla resumen de promedios (wall_s) por prueba", fontsize=14, pad=18)
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    expected_sizes: list[str] | None = None
    summary_rows: list[list[str]] = []

    for label, csv_path in SOURCES:
        sizes, promedio_by_size = read_promedio_row(csv_path)

        if expected_sizes is None:
            expected_sizes = sizes
        elif sizes != expected_sizes:
            raise ValueError(
                "Las dimensiones de matriz no coinciden entre archivos. "
                f"Archivo conflictivo: {csv_path}"
            )

        row = [label] + [f"{promedio_by_size[size]:.6f}" for size in expected_sizes]
        summary_rows.append(row)

    if expected_sizes is None:
        raise ValueError("No se encontraron fuentes para consolidar")

    write_summary_csv(expected_sizes, summary_rows)
    write_summary_png()

    print(f"CSV resumen generado: {OUTPUT_CSV}")
    print(f"PNG resumen generado: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()