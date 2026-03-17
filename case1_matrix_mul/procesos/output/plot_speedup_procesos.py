from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
SEQUENTIAL_FILE = BASE_DIR.parent.parent / "secuencial" / "output" / "times_secuencial.txt"
PROCESSES_FILE = BASE_DIR / "output_procesos.txt"
OUTPUT_FIGURE = BASE_DIR / "speedup_procesos_vs_secuencial.png"
PROCESS_COUNTS = (2, 4, 8, 16)


def load_average_sequential_times(path: Path) -> dict[int, float]:
    grouped_times: dict[int, list[float]] = {}

    with path.open("r", encoding="utf-8") as file:
        next(file)
        for line_number, raw_line in enumerate(file, start=2):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) == 9:
                n_value = int(parts[0])
                wall_time = float(parts[3])
            elif len(parts) == 6:
                n_value = int(parts[0])
                wall_time = float(parts[2])
            else:
                raise ValueError(
                    f"Formato inesperado en {path.name}:{line_number}: {line}"
                )

            grouped_times.setdefault(n_value, []).append(wall_time)

    return {
        n_value: float(np.mean(times))
        for n_value, times in sorted(grouped_times.items())
    }


def load_average_process_times(path: Path) -> dict[int, dict[int, float]]:
    grouped_times: dict[int, dict[int, list[float]]] = {}

    with path.open("r", encoding="utf-8") as file:
        next(file)
        for line_number, raw_line in enumerate(file, start=2):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) == 9:
                n_value = int(parts[0])
                process_count = int(parts[1])
                wall_time = float(parts[3])
            elif len(parts) == 6:
                n_value = int(parts[0])
                process_count = int(parts[1])
                wall_time = float(parts[3])
            else:
                raise ValueError(
                    f"Formato inesperado en {path.name}:{line_number}: {line}"
                )

            if process_count not in PROCESS_COUNTS:
                continue

            grouped_times.setdefault(n_value, {}).setdefault(process_count, []).append(wall_time)

    averaged: dict[int, dict[int, float]] = {}
    for n_value, process_map in sorted(grouped_times.items()):
        averaged[n_value] = {
            process_count: float(np.mean(times))
            for process_count, times in sorted(process_map.items())
        }

    return averaged


def main() -> None:
    sequential_times = load_average_sequential_times(SEQUENTIAL_FILE)
    process_times = load_average_process_times(PROCESSES_FILE)

    common_sizes = sorted(set(sequential_times) & set(process_times))
    if not common_sizes:
        raise ValueError("No hay tamanos N en comun entre la corrida secuencial y la de procesos.")

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))
    x_positions = np.arange(len(common_sizes))

    for process_count in PROCESS_COUNTS:
        valid_sizes = [
            n_value
            for n_value in common_sizes
            if process_count in process_times[n_value]
        ]
        if not valid_sizes:
            continue

        valid_positions = [
            common_sizes.index(n_value)
            for n_value in valid_sizes
        ]
        speedup = np.array(
            [
                sequential_times[n_value] / process_times[n_value][process_count]
                for n_value in valid_sizes
            ],
            dtype=float,
        )
        ax.plot(valid_positions, speedup, marker="o", linewidth=2, label=f"{process_count} procesos")

    ax.set_title("Speedup de procesos respecto a secuencial")
    ax.set_xlabel("Tamano de matriz (N)")
    ax.set_ylabel("Speedup")
    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(n_value) for n_value in common_sizes])
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE, dpi=300)

    print("Promedios secuenciales (wall_s):")
    for n_value in common_sizes:
        print(f"  N={n_value:<5d} secuencial={sequential_times[n_value]:.6f} s")

    print("\nPromedios por numero de procesos (wall_s):")
    for process_count in PROCESS_COUNTS:
        available_sizes = [
            n_value for n_value in common_sizes if process_count in process_times[n_value]
        ]
        if not available_sizes:
            continue

        print(f"\n{process_count} procesos")
        for n_value in available_sizes:
            print(f"  N={n_value:<5d} promedio={process_times[n_value][process_count]:.6f} s")

    print(f"\nGrafica guardada en: {OUTPUT_FIGURE}")


if __name__ == "__main__":
    main()
