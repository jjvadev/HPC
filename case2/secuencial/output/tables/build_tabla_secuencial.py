from pathlib import Path
import csv
from collections import defaultdict


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR.parent / "times_secuencial.txt"
OUT_MD = BASE_DIR / "tabla_secuencial.md"
OUT_CSV = BASE_DIR / "tabla_secuencial.csv"


def load_sequential_wall_times(path: Path) -> dict[int, list[float]]:
    grouped: dict[int, list[float]] = defaultdict(list)

    with path.open("r", encoding="utf-8") as file:
        next(file)  # header
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

    return dict(sorted(grouped.items()))


def build_round_table(grouped: dict[int, list[float]]) -> tuple[list[int], list[list[float]]]:
    sizes = sorted(grouped.keys())
    rounds = min(len(grouped[n]) for n in sizes)

    table: list[list[float]] = []
    for round_index in range(rounds):
        row = [float(round_index + 1)]
        row.extend(grouped[n][round_index] for n in sizes)
        table.append(row)

    return sizes, table


def compute_means(grouped: dict[int, list[float]], sizes: list[int]) -> dict[int, float]:
    return {n: sum(grouped[n]) / len(grouped[n]) for n in sizes}


def write_markdown(sizes: list[int], table: list[list[float]], means: dict[int, float]) -> None:
    headers = ["Ronda"] + [str(n) for n in sizes]
    lines: list[str] = []

    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in table:
        round_label = str(int(row[0]))
        values = [f"{value:.6f}" for value in row[1:]]
        lines.append("| " + " | ".join([round_label] + values) + " |")

    mean_values = [f"{means[n]:.6f}" for n in sizes]
    lines.append("| Promedio | " + " | ".join(mean_values) + " |")

    speedup_values = ["1.000000" for _ in sizes]
    lines.append("| Speedup (vs secuencial) | " + " | ".join(speedup_values) + " |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv_file(sizes: list[int], table: list[list[float]], means: dict[int, float]) -> None:
    headers = ["Ronda"] + [str(n) for n in sizes]

    with OUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for row in table:
            writer.writerow([int(row[0])] + [f"{value:.6f}" for value in row[1:]])

        writer.writerow(["Promedio"] + [f"{means[n]:.6f}" for n in sizes])
        writer.writerow(["Speedup (vs secuencial)"] + ["1.000000" for _ in sizes])


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {INPUT_FILE}")

    grouped = load_sequential_wall_times(INPUT_FILE)
    if not grouped:
        raise ValueError("No se encontraron datos validos en times_secuencial.txt")

    sizes, table = build_round_table(grouped)
    means = compute_means(grouped, sizes)

    write_markdown(sizes, table, means)
    write_csv_file(sizes, table, means)

    print(f"Tabla Markdown: {OUT_MD}")
    print(f"Tabla CSV: {OUT_CSV}")


if __name__ == "__main__":
    main()
