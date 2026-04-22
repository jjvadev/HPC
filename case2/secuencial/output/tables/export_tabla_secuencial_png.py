from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "tabla_secuencial.csv"
OUTPUT_PNG = BASE_DIR / "tabla_secuencial.png"


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"No existe: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")

    n_rows, n_cols = df.shape
    fig_width = max(12, n_cols * 1.4)
    fig_height = max(6, n_rows * 0.45)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.4)

    # Encabezado
    for col_idx in range(n_cols):
        cell = table[(0, col_idx)]
        cell.set_facecolor("#D9EAF7")
        cell.set_text_props(weight="bold")

    # Resaltar filas resumen (Promedio y Speedup)
    for row_idx in range(1, n_rows + 1):
        first_value = str(df.iloc[row_idx - 1, 0])
        if first_value.startswith("Promedio") or first_value.startswith("Speedup"):
            for col_idx in range(n_cols):
                cell = table[(row_idx, col_idx)]
                cell.set_facecolor("#F4F4F4")
                if col_idx == 0:
                    cell.set_text_props(weight="bold")

    plt.title("Tabla de tiempos secuencial (wall_s)", fontsize=13, pad=20)
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")

    print(f"Imagen generada: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
