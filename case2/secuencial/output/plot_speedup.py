from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent

FILES = {
    "Secuencial": BASE_DIR / "times_secuencial.txt",
    "Secuencial transpuesta": BASE_DIR / "times_secuencia_transpuesta.txt",
    "Secuencial O3": BASE_DIR / "times_secuencial_o3.txt",
}

OUTPUT_FIGURE = BASE_DIR / "speedup_comparado.png"


def load_average_wall_times(path: Path) -> dict[int, float]:
    grouped_times: dict[int, list[float]] = {}

    with path.open("r", encoding="utf-8") as file:
        next(file)  # Skip header
        for line_number, raw_line in enumerate(file, start=2):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()

            if len(parts) == 9:
                n_value = int(parts[0])
                wall_time = float(parts[3])
            elif len(parts) == 8:
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


def main() -> None:
    averaged_times = {
        label: load_average_wall_times(path)
        for label, path in FILES.items()
    }

    common_sizes = sorted(set.intersection(*(set(times) for times in averaged_times.values())))
    if not common_sizes:
        raise ValueError("No hay tamanos N en comun entre los tres archivos.")

    baseline_label = "Secuencial"
    baseline_times = averaged_times[baseline_label]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))
    x_positions = np.arange(len(common_sizes))

    for label, times_by_n in averaged_times.items():
        speedup = np.array(
            [baseline_times[n_value] / times_by_n[n_value] for n_value in common_sizes],
            dtype=float,
        )
        ax.plot(x_positions, speedup, marker="o", linewidth=2, label=label)

    ax.set_title("Speedup promedio por tamano de matriz")
    ax.set_xlabel("Tamano de matriz (N)")
    ax.set_ylabel("Speedup respecto a Secuencial")
    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(n_value) for n_value in common_sizes])
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE, dpi=300)

    print("Promedios de wall_s por archivo:")
    for label, times_by_n in averaged_times.items():
        print(f"\n{label}")
        for n_value, average_time in times_by_n.items():
            print(f"  N={n_value:<5d} promedio={average_time:.6f} s")

    print("\nSpeedup respecto a Secuencial:")
    for label, times_by_n in averaged_times.items():
        print(f"\n{label}")
        for n_value in common_sizes:
            speedup_value = baseline_times[n_value] / times_by_n[n_value]
            print(f"  N={n_value:<5d} speedup={speedup_value:.6f}")

    print(f"\nGrafica guardada en: {OUTPUT_FIGURE}")


if __name__ == "__main__":
    main()
