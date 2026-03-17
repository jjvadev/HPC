from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent

SECUENCIAL_FILE = BASE_DIR / "times_secuencial.txt"
SECUENCIAL_TRANSPUESTA_FILE = BASE_DIR / "times_secuencia_transpuesta.txt"
SECUENCIAL_O3_FILE = BASE_DIR / "times_secuencial_o3.txt"
HILOS_FILE = BASE_DIR.parent.parent / "hilos" / "output" / "output_hilos.txt"
PROCESOS_FILE = BASE_DIR.parent.parent / "procesos" / "output" / "output_procesos_8-16.txt"

OUTPUT_FIGURE = BASE_DIR / "speedup_comparacion_mem_opt_hilos_procesos.png"
TARGET_HILOS = (8, 16)
TARGET_PROCESOS = (8, 16)


def parse_line_generic(parts: list[str], file_name: str, line_number: int) -> tuple[int, int, float]:
    if len(parts) == 9:
        n_value = int(parts[0])
        workers = int(parts[1])
        wall_s = float(parts[3])
        return n_value, workers, wall_s

    if len(parts) == 8:
        n_value = int(parts[0])
        workers = int(parts[1])
        wall_s = float(parts[2])
        return n_value, workers, wall_s

    if len(parts) == 6:
        n_value = int(parts[0])
        workers = int(parts[1])
        wall_s = float(parts[3])
        return n_value, workers, wall_s

    raise ValueError(f"Formato inesperado en {file_name}:{line_number}: {' '.join(parts)}")


def load_average_sequential(path: Path) -> dict[int, float]:
    grouped: dict[int, list[float]] = {}

    with path.open("r", encoding="utf-8") as file:
        next(file)
        for line_number, raw_line in enumerate(file, start=2):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()
            n_value, _workers, wall_s = parse_line_generic(parts, path.name, line_number)
            grouped.setdefault(n_value, []).append(wall_s)

    return {n: float(np.mean(times)) for n, times in sorted(grouped.items())}


def load_average_filtered(path: Path, accepted_workers: tuple[int, ...]) -> dict[int, dict[int, float]]:
    grouped: dict[int, dict[int, list[float]]] = {}

    with path.open("r", encoding="utf-8") as file:
        next(file)
        for line_number, raw_line in enumerate(file, start=2):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()
            n_value, workers, wall_s = parse_line_generic(parts, path.name, line_number)

            if workers not in accepted_workers:
                continue

            grouped.setdefault(n_value, {}).setdefault(workers, []).append(wall_s)

    averaged: dict[int, dict[int, float]] = {}
    for n_value, by_workers in sorted(grouped.items()):
        averaged[n_value] = {
            workers: float(np.mean(times))
            for workers, times in sorted(by_workers.items())
        }

    return averaged


def speedup_curve(
    baseline: dict[int, float],
    source: dict[int, float],
    sizes: list[int],
) -> np.ndarray:
    return np.array([baseline[n] / source[n] for n in sizes], dtype=float)


def main() -> None:
    secuencial = load_average_sequential(SECUENCIAL_FILE)
    secuencial_transpuesta = load_average_sequential(SECUENCIAL_TRANSPUESTA_FILE)
    secuencial_o3 = load_average_sequential(SECUENCIAL_O3_FILE)

    hilos = load_average_filtered(HILOS_FILE, TARGET_HILOS)
    procesos = load_average_filtered(PROCESOS_FILE, TARGET_PROCESOS)

    common_sizes = sorted(
        set(secuencial)
        & set(secuencial_transpuesta)
        & set(secuencial_o3)
        & set(hilos)
        & set(procesos)
    )
    if not common_sizes:
        raise ValueError("No hay tamanos N en comun entre todas las series.")

    for n_value in common_sizes:
        for workers in TARGET_HILOS:
            if workers not in hilos[n_value]:
                raise ValueError(f"Faltan datos de hilos={workers} para N={n_value}.")
        for workers in TARGET_PROCESOS:
            if workers not in procesos[n_value]:
                raise ValueError(f"Faltan datos de procesos={workers} para N={n_value}.")

    x_positions = np.arange(len(common_sizes))

    sec_line = np.ones(len(common_sizes), dtype=float)
    trans_line = speedup_curve(secuencial, secuencial_transpuesta, common_sizes)
    o3_line = speedup_curve(secuencial, secuencial_o3, common_sizes)
    h8_line = np.array([secuencial[n] / hilos[n][8] for n in common_sizes], dtype=float)
    h16_line = np.array([secuencial[n] / hilos[n][16] for n in common_sizes], dtype=float)
    p8_line = np.array([secuencial[n] / procesos[n][8] for n in common_sizes], dtype=float)
    p16_line = np.array([secuencial[n] / procesos[n][16] for n in common_sizes], dtype=float)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(11, 6.5))

    ax.plot(x_positions, sec_line, marker="o", linewidth=2.0, label="Secuencial (base)")
    ax.plot(x_positions, trans_line, marker="o", linewidth=2.0, label="Secuencial transpuesta (memoria)")
    ax.plot(x_positions, o3_line, marker="o", linewidth=2.0, label="Secuencial O3 (optimizacion)")
    ax.plot(x_positions, h8_line, marker="o", linewidth=2.2, label="Hilos 8")
    ax.plot(x_positions, h16_line, marker="o", linewidth=2.2, label="Hilos 16")
    ax.plot(x_positions, p8_line, marker="o", linewidth=2.2, label="Procesos 8")
    ax.plot(x_positions, p16_line, marker="o", linewidth=2.2, label="Procesos 16")

    ax.set_title("Comparacion de speedup: memoria, optimizacion, hilos y procesos")
    ax.set_xlabel("Tamano de matriz (N)")
    ax.set_ylabel("Speedup respecto a secuencial")
    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(n) for n in common_sizes])
    ax.legend(loc="best")

    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE, dpi=300)

    print("Grafica guardada en:")
    print(f"  {OUTPUT_FIGURE}")


if __name__ == "__main__":
    main()
