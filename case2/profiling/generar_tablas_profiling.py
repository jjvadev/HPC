from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "output"
CACHE_DIR = BASE_DIR / ".matplotlib-cache"
CACHE_DIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

import matplotlib.pyplot as plt


VARIANTS = {
    "secuencial": {
        "label": "Secuencial",
        "cpu": "secuencial_CPU.txt",
        "mem": "secuencial_mem.txt",
    },
    "o3": {
        "label": "O3",
        "cpu": "o3_CPU.txt",
        "mem": "o3_mem.txt",
    },
    "cache": {
        "label": "Transpuesta/cache",
        "cpu": "cache_CPU.txt",
        "mem": "cache_mem.txt",
    },
}

CODE_SYMBOLS = {
    "matmul",
    "fill_random_matrices",
    "rand_i32",
    "zero_matrix",
    "checksum_matrix",
    "process_cpu_seconds",
    "wall_seconds_now",
}

IMPORTANT_MEM_SYMBOLS = (
    "matmul",
    "fill_random_matrices",
    "zero_matrix",
    "checksum_matrix",
)


TIME_RE = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>min|s|ms)\s+"
    r"(?P<pct>[\d,]+(?:\.\d+)?)\s*%"
)


@dataclass
class CpuRow:
    weight_s: float
    weight_pct: float
    self_s: float
    symbol: str


@dataclass
class CounterRow:
    l1d_load_misses: int
    l1d_load_pct: float
    l1d_store_misses: int
    l1d_store_pct: float
    l1dtlb_misses: int
    l1dtlb_pct: float
    symbol: str


def first_block(path: Path) -> list[str]:
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() and lines:
            break
        if raw_line.strip():
            lines.append(raw_line)
    return lines


def parse_decimal(value: str) -> float:
    return float(value.replace(",", "."))


def parse_time_to_seconds(value: str) -> float:
    stripped = value.strip()
    if stripped == "0 s":
        return 0.0

    match = re.match(r"^(\d+(?:\.\d+)?)\s*(min|s|ms)$", stripped)
    if not match:
        raise ValueError(f"Tiempo inesperado: {value!r}")

    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "min":
        return amount * 60
    if unit == "s":
        return amount
    if unit == "ms":
        return amount / 1000
    raise ValueError(f"Unidad inesperada: {unit}")


def parse_cpu_cell(cell: str) -> tuple[float, float]:
    normalized = cell.replace("\u00a0", " ").replace("\u2007", " ")
    match = TIME_RE.match(normalized)
    if not match:
        raise ValueError(f"Celda de CPU inesperada: {cell!r}")
    seconds = parse_time_to_seconds(f"{match.group('value')} {match.group('unit')}")
    percent = parse_decimal(match.group("pct"))
    return seconds, percent


def parse_cpu_file(path: Path) -> list[CpuRow]:
    rows: list[CpuRow] = []
    for line in first_block(path):
        if line.startswith("Weight"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        weight_s, weight_pct = parse_cpu_cell(parts[0])
        self_s = parse_time_to_seconds(parts[1])
        rows.append(CpuRow(weight_s, weight_pct, self_s, parts[2].strip()))
    return rows


def parse_counter_cell(cell: str) -> tuple[int, float]:
    normalized = cell.replace("\u00a0", " ").replace("\u2007", " ").strip()
    match = re.match(r"^(?P<count>[\d.]+)\s+(?P<pct>[\d,]+(?:\.\d+)?)\s*%", normalized)
    if not match:
        raise ValueError(f"Celda de contador inesperada: {cell!r}")
    count = int(match.group("count").replace(".", ""))
    percent = parse_decimal(match.group("pct"))
    return count, percent


def parse_counter_file(path: Path) -> list[CounterRow]:
    rows: list[CounterRow] = []
    for line in first_block(path):
        if line.startswith("L1DC"):
            continue
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        l1d_load_misses, l1d_load_pct = parse_counter_cell(parts[0])
        l1d_store_misses, l1d_store_pct = parse_counter_cell(parts[1])
        l1dtlb_misses, l1dtlb_pct = parse_counter_cell(parts[2])
        rows.append(
            CounterRow(
                l1d_load_misses,
                l1d_load_pct,
                l1d_store_misses,
                l1d_store_pct,
                l1dtlb_misses,
                l1dtlb_pct,
                parts[3].strip(),
            )
        )
    return rows


def write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)


def render_table_png(
    path: Path,
    title: str,
    headers: list[str],
    rows: list[list[object]],
    *,
    font_size: int = 10,
    width_scale: float = 1.2,
    height_scale: float = 0.48,
    title_pad: int = 18,
) -> None:
    n_rows = len(rows) + 1
    n_cols = len(headers)
    fig_width = max(10, n_cols * width_scale)
    fig_height = max(3.5, n_rows * height_scale)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    table.scale(1.0, 1.25)

    for cell in table.get_celld().values():
        cell.get_text().set_parse_math(False)

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

    plt.title(title, fontsize=14, pad=title_pad)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def cpu_rows_to_table_rows(rows: list[CpuRow]) -> list[list[object]]:
    return [
        [f"{row.weight_s:.6f}", f"{row.self_s:.6f}", row.symbol]
        for row in rows
    ]


def write_cpu_profile_tables() -> None:
    for key, meta in VARIANTS.items():
        rows = parse_cpu_file(BASE_DIR / meta["cpu"])
        render_table_png(
            OUT_DIR / f"profiling_cpu_{key}.png",
            f"Profiling CPU - {meta['label']}",
            ["Weight (s)", "Self Weight (s)", "Symbol Names"],
            cpu_rows_to_table_rows(rows),
            font_size=9,
            width_scale=1.9,
            height_scale=0.34,
            title_pad=14,
        )


def build_simple_mem_table_rows(rows: list[CounterRow]) -> list[list[object]]:
    by_symbol = {row.symbol: row for row in rows}
    simple_rows: list[list[object]] = []

    total = rows[0]
    simple_rows.append(
        [
            "TOTAL",
            total.l1d_load_misses,
            total.l1d_store_misses,
            total.l1dtlb_misses,
        ]
    )

    for symbol in IMPORTANT_MEM_SYMBOLS:
        row = by_symbol.get(symbol)
        if row is None:
            simple_rows.append([symbol, 0, 0, 0])
            continue
        simple_rows.append(
            [
                symbol,
                row.l1d_load_misses,
                row.l1d_store_misses,
                row.l1dtlb_misses,
            ]
        )

    return simple_rows


def write_simple_mem_tables() -> None:
    for key, meta in VARIANTS.items():
        rows = parse_counter_file(BASE_DIR / meta["mem"])
        table_rows = build_simple_mem_table_rows(rows)
        headers = [
            "Funcion",
            "L1DC Ld Misses",
            "L1DC St Misses",
            "L1DTLB Misses",
        ]

        write_csv(
            OUT_DIR / f"profiling_mem_{key}_simple.csv",
            headers,
            table_rows,
        )

        render_table_png(
            OUT_DIR / f"profiling_mem_{key}_simple.png",
            f"Memoria (tabla simple) - {meta['label']}",
            headers,
            table_rows,
            font_size=10,
            width_scale=1.8,
            height_scale=0.62,
            title_pad=14,
        )


def build_cpu_summary() -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for key, meta in VARIANTS.items():
        rows = parse_cpu_file(BASE_DIR / meta["cpu"])
        total = rows[0]
        matmul_rows = [row for row in rows if row.symbol == "matmul"]
        matmul_weight_s = sum(row.weight_s for row in matmul_rows)
        matmul_self_s = sum(row.self_s for row in matmul_rows)
        summary.append(
            {
                "variant": key,
                "variant_label": meta["label"],
                "executable": total.symbol,
                "total_cpu_s": total.weight_s,
                "matmul_cpu_s": matmul_weight_s,
                "matmul_self_s": matmul_self_s,
                "matmul_pct_total": (matmul_weight_s / total.weight_s * 100)
                if total.weight_s
                else 0.0,
            }
        )
    return summary


def build_cpu_function_summary() -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for key, meta in VARIANTS.items():
        rows = parse_cpu_file(BASE_DIR / meta["cpu"])
        total_s = rows[0].weight_s
        grouped: dict[str, dict[str, object]] = {}

        for row in rows[1:]:
            if row.symbol not in CODE_SYMBOLS:
                continue
            if row.symbol not in grouped:
                grouped[row.symbol] = {
                    "variant": key,
                    "variant_label": meta["label"],
                    "symbol": row.symbol,
                    "cpu_weight_s": 0.0,
                    "cpu_self_s": 0.0,
                    "occurrences": 0,
                }
            grouped_row = grouped[row.symbol]
            grouped_row["cpu_weight_s"] += row.weight_s
            grouped_row["cpu_self_s"] += row.self_s
            grouped_row["occurrences"] += 1

        for row in grouped.values():
            row["cpu_pct_total"] = (
                row["cpu_weight_s"] / total_s * 100 if total_s else 0.0
            )
            summary.append(row)

    variant_order = {key: index for index, key in enumerate(VARIANTS)}
    return sorted(
        summary,
        key=lambda row: (
            variant_order[row["variant"]],
            -row["cpu_weight_s"],
            row["symbol"],
        ),
    )


def build_counter_summary() -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for key, meta in VARIANTS.items():
        rows = parse_counter_file(BASE_DIR / meta["mem"])
        total = rows[0]
        matmul = next(row for row in rows if row.symbol == "matmul")
        summary.append(
            {
                "variant": key,
                "variant_label": meta["label"],
                "executable": total.symbol,
                "total_l1d_load_misses": total.l1d_load_misses,
                "total_l1d_store_misses": total.l1d_store_misses,
                "total_l1dtlb_misses": total.l1dtlb_misses,
                "matmul_l1d_load_misses": matmul.l1d_load_misses,
                "matmul_l1d_load_pct": matmul.l1d_load_pct,
                "matmul_l1d_store_misses": matmul.l1d_store_misses,
                "matmul_l1d_store_pct": matmul.l1d_store_pct,
                "matmul_l1dtlb_misses": matmul.l1dtlb_misses,
                "matmul_l1dtlb_pct": matmul.l1dtlb_pct,
            }
        )
    return summary


def add_speedups(
    cpu_summary: list[dict[str, object]], counter_summary: list[dict[str, object]]
) -> list[dict[str, object]]:
    baseline_cpu = next(row for row in cpu_summary if row["variant"] == "secuencial")
    baseline_counter = next(row for row in counter_summary if row["variant"] == "secuencial")

    rows: list[dict[str, object]] = []
    for cpu_row, counter_row in zip(cpu_summary, counter_summary, strict=True):
        rows.append(
            {
                "variant": cpu_row["variant"],
                "variant_label": cpu_row["variant_label"],
                "cpu_speedup_vs_secuencial": baseline_cpu["total_cpu_s"]
                / cpu_row["total_cpu_s"],
                "matmul_speedup_vs_secuencial": baseline_cpu["matmul_cpu_s"]
                / cpu_row["matmul_cpu_s"],
                "l1d_load_reduction_vs_secuencial_pct": (
                    1
                    - counter_row["matmul_l1d_load_misses"]
                    / baseline_counter["matmul_l1d_load_misses"]
                )
                * 100,
                "l1dtlb_reduction_vs_secuencial_pct": (
                    1
                    - counter_row["matmul_l1dtlb_misses"]
                    / baseline_counter["matmul_l1dtlb_misses"]
                )
                * 100,
            }
        )
    return rows


def plot_cpu_functions(function_summary: list[dict[str, object]]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)
    for ax, (variant_key, meta) in zip(axes, VARIANTS.items(), strict=True):
        rows = [
            row for row in function_summary if row["variant"] == variant_key
        ]
        rows = sorted(rows, key=lambda row: row["cpu_weight_s"], reverse=True)[:6]
        labels = [row["symbol"] for row in rows]
        values = [row["cpu_weight_s"] for row in rows]
        ax.barh(labels, values, color="#F28E2B")
        ax.invert_yaxis()
        ax.set_title(meta["label"])
        ax.set_xlabel("Segundos CPU")
        ax.grid(axis="x", alpha=0.25)

    fig.suptitle("Funciones mas costosas segun Time Profiler")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "profiling_cpu_funciones.png", dpi=180)
    plt.close(fig)


def plot_cpu(cpu_summary: list[dict[str, object]], speedups: list[dict[str, object]]) -> None:
    labels = [row["variant_label"] for row in cpu_summary]
    total = [row["total_cpu_s"] for row in cpu_summary]
    matmul = [row["matmul_cpu_s"] for row in cpu_summary]
    speedup = [row["cpu_speedup_vs_secuencial"] for row in speedups]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    x_positions = range(len(labels))
    width = 0.36

    axes[0].bar([x - width / 2 for x in x_positions], total, width, label="Total")
    axes[0].bar([x + width / 2 for x in x_positions], matmul, width, label="matmul")
    axes[0].set_title("Tiempo CPU por variante")
    axes[0].set_ylabel("Segundos")
    axes[0].set_xticks(list(x_positions), labels, rotation=15, ha="right")
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].bar(labels, speedup, color="#4C78A8")
    axes[1].set_title("Speedup CPU vs secuencial")
    axes[1].set_ylabel("x veces")
    axes[1].set_xticks(list(x_positions), labels, rotation=15, ha="right")
    axes[1].axhline(1.0, color="black", linewidth=0.8)
    axes[1].grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "profiling_cpu_comparacion.png", dpi=180)
    plt.close(fig)


def plot_counters(counter_summary: list[dict[str, object]]) -> None:
    labels = [row["variant_label"] for row in counter_summary]
    metrics = [
        ("matmul_l1d_load_misses", "L1D load misses"),
        ("matmul_l1d_store_misses", "L1D store misses"),
        ("matmul_l1dtlb_misses", "L1D TLB misses"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, (key, title) in zip(axes, metrics, strict=True):
        values = [row[key] for row in counter_summary]
        ax.bar(labels, values, color="#59A14F")
        ax.set_title(title)
        ax.set_yscale("log")
        ax.set_xticks(range(len(labels)), labels, rotation=15, ha="right")
        ax.grid(axis="y", alpha=0.25)

    fig.suptitle("CPU Counters: misses en matmul (escala log)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "profiling_l1d_misses_comparacion.png", dpi=180)
    plt.close(fig)


def plot_cache_reduction(speedups: list[dict[str, object]]) -> None:
    labels = [row["variant_label"] for row in speedups]
    load_reduction = [row["l1d_load_reduction_vs_secuencial_pct"] for row in speedups]
    tlb_reduction = [row["l1dtlb_reduction_vs_secuencial_pct"] for row in speedups]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    x_positions = range(len(labels))
    width = 0.36
    ax.bar(
        [x - width / 2 for x in x_positions],
        load_reduction,
        width,
        label="L1D load misses",
    )
    ax.bar(
        [x + width / 2 for x in x_positions],
        tlb_reduction,
        width,
        label="L1D TLB misses",
    )
    ax.set_title("Reduccion de misses vs secuencial en matmul")
    ax.set_ylabel("% reduccion")
    ax.set_xticks(list(x_positions), labels, rotation=15, ha="right")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "profiling_reduccion_misses.png", dpi=180)
    plt.close(fig)


def write_report_snippet(
    cpu_summary: list[dict[str, object]],
    function_summary: list[dict[str, object]],
    counter_summary: list[dict[str, object]],
    speedups: list[dict[str, object]],
) -> None:
    lines = [
        "# Resumen de profiling - caso de estudio 2",
        "",
        "Fuente de CPU: Instruments Time Profiler.",
        "Fuente de memoria/cache: Instruments CPU Counters con eventos L1D/L1DTLB misses.",
        "",
        "## CPU",
        "",
        "| Variante | CPU total (s) | CPU matmul (s) | % matmul | Speedup total |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for cpu_row, speedup_row in zip(cpu_summary, speedups, strict=True):
        merged = {**speedup_row, **cpu_row}
        lines.append(
            "| {variant_label} | {total_cpu_s:.3f} | {matmul_cpu_s:.3f} | "
            "{matmul_pct_total:.2f}% | {cpu_speedup_vs_secuencial:.3f}x |".format(
                **merged
            )
        )

    lines.extend(
        [
            "",
            "## Funciones mas costosas en CPU",
            "",
            "| Variante | Funcion | CPU acumulado (s) | Self CPU (s) | % del total | Apariciones |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    variant_order = {key: index for index, key in enumerate(VARIANTS)}
    for row in sorted(
        function_summary,
        key=lambda item: (
            variant_order[item["variant"]],
            -item["cpu_weight_s"],
            item["symbol"],
        ),
    ):
        lines.append(
            "| {variant_label} | `{symbol}` | {cpu_weight_s:.3f} | "
            "{cpu_self_s:.3f} | {cpu_pct_total:.2f}% | {occurrences} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Nota: los tiempos por funcion son inclusivos segun el arbol de llamadas "
            "de Time Profiler. Sirven para ubicar las funciones dominantes, no para "
            "sumarlos como si fueran partes disjuntas del tiempo total.",
        ]
    )

    lines.extend(
        [
            "",
            "## CPU Counters",
            "",
            "| Variante | L1D load misses matmul | L1D store misses matmul | "
            "L1DTLB misses matmul | Reduccion L1D load | Reduccion L1DTLB |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for counter_row, speedup_row in zip(counter_summary, speedups, strict=True):
        merged = {**speedup_row, **counter_row}
        lines.append(
            "| {variant_label} | {matmul_l1d_load_misses} | "
            "{matmul_l1d_store_misses} | {matmul_l1dtlb_misses} | "
            "{l1d_load_reduction_vs_secuencial_pct:.2f}% | "
            "{l1dtlb_reduction_vs_secuencial_pct:.2f}% |".format(
                **merged
            )
        )

    lines.extend(
        [
            "",
            "Interpretacion breve: O3 reduce el tiempo de CPU frente al secuencial, "
            "mientras que la version con matriz transpuesta reduce de forma marcada "
            "los misses L1D/L1DTLB de `matmul`, lo que confirma mejor localidad de cache.",
            "",
        ]
    )
    (OUT_DIR / "resumen_profiling.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    write_cpu_profile_tables()
    write_simple_mem_tables()

    cpu_summary = build_cpu_summary()
    function_summary = build_cpu_function_summary()
    counter_summary = build_counter_summary()
    speedups = add_speedups(cpu_summary, counter_summary)

    write_csv(
        OUT_DIR / "profiling_cpu_summary.csv",
        [
            "variante",
            "ejecutable",
            "cpu_total_s",
            "cpu_matmul_s",
            "cpu_self_matmul_s",
            "porcentaje_cpu_matmul",
        ],
        [
            [
                row["variant_label"],
                row["executable"],
                f"{row['total_cpu_s']:.6f}",
                f"{row['matmul_cpu_s']:.6f}",
                f"{row['matmul_self_s']:.6f}",
                f"{row['matmul_pct_total']:.6f}",
            ]
            for row in cpu_summary
        ],
    )

    render_table_png(
        OUT_DIR / "profiling_cpu_summary.png",
        "Tabla resumen CPU por variante",
        [
            "Variante",
            "Ejecutable",
            "CPU total (s)",
            "CPU matmul (s)",
            "Self CPU matmul (s)",
            "% matmul",
        ],
        [
            [
                row["variant_label"],
                row["executable"],
                f"{row['total_cpu_s']:.6f}",
                f"{row['matmul_cpu_s']:.6f}",
                f"{row['matmul_self_s']:.6f}",
                f"{row['matmul_pct_total']:.6f}",
            ]
            for row in cpu_summary
        ],
        font_size=10,
        width_scale=1.55,
        height_scale=0.48,
    )

    write_csv(
        OUT_DIR / "profiling_cpu_funciones.csv",
        [
            "variante",
            "funcion",
            "cpu_acumulado_s",
            "self_cpu_s",
            "porcentaje_cpu_total",
            "apariciones_en_arbol",
        ],
        [
            [
                row["variant_label"],
                row["symbol"],
                f"{row['cpu_weight_s']:.6f}",
                f"{row['cpu_self_s']:.6f}",
                f"{row['cpu_pct_total']:.6f}",
                row["occurrences"],
            ]
            for row in function_summary
        ],
    )

    render_table_png(
        OUT_DIR / "profiling_cpu_funciones.png",
        "Tabla de funciones mas costosas en CPU",
        [
            "Variante",
            "Funcion",
            "CPU acumulado (s)",
            "Self CPU (s)",
            "% del total",
            "Apariciones",
        ],
        [
            [
                row["variant_label"],
                row["symbol"],
                f"{row['cpu_weight_s']:.6f}",
                f"{row['cpu_self_s']:.6f}",
                f"{row['cpu_pct_total']:.6f}",
                row["occurrences"],
            ]
            for row in function_summary
        ],
        font_size=9,
        width_scale=1.55,
        height_scale=0.38,
    )

    write_csv(
        OUT_DIR / "profiling_l1d_summary.csv",
        [
            "variante",
            "ejecutable",
            "total_l1d_load_misses",
            "total_l1d_store_misses",
            "total_l1dtlb_misses",
            "matmul_l1d_load_misses",
            "matmul_l1d_load_pct",
            "matmul_l1d_store_misses",
            "matmul_l1d_store_pct",
            "matmul_l1dtlb_misses",
            "matmul_l1dtlb_pct",
        ],
        [
            [
                row["variant_label"],
                row["executable"],
                row["total_l1d_load_misses"],
                row["total_l1d_store_misses"],
                row["total_l1dtlb_misses"],
                row["matmul_l1d_load_misses"],
                f"{row['matmul_l1d_load_pct']:.6f}",
                row["matmul_l1d_store_misses"],
                f"{row['matmul_l1d_store_pct']:.6f}",
                row["matmul_l1dtlb_misses"],
                f"{row['matmul_l1dtlb_pct']:.6f}",
            ]
            for row in counter_summary
        ],
    )

    render_table_png(
        OUT_DIR / "profiling_l1d_summary.png",
        "Tabla resumen de L1D/L1DTLB en matmul",
        [
            "Variante",
            "Ejecutable",
            "Total L1D load",
            "Total L1D store",
            "Total L1DTLB",
            "Matmul L1D load",
            "% load",
            "Matmul L1D store",
            "% store",
            "Matmul L1DTLB",
            "% TLB",
        ],
        [
            [
                row["variant_label"],
                row["executable"],
                row["total_l1d_load_misses"],
                row["total_l1d_store_misses"],
                row["total_l1dtlb_misses"],
                row["matmul_l1d_load_misses"],
                f"{row['matmul_l1d_load_pct']:.6f}",
                row["matmul_l1d_store_misses"],
                f"{row['matmul_l1d_store_pct']:.6f}",
                row["matmul_l1dtlb_misses"],
                f"{row['matmul_l1dtlb_pct']:.6f}",
            ]
            for row in counter_summary
        ],
        font_size=8,
        width_scale=1.25,
        height_scale=0.42,
    )

    write_csv(
        OUT_DIR / "profiling_comparacion_vs_secuencial.csv",
        [
            "variante",
            "speedup_cpu_total_vs_secuencial",
            "speedup_cpu_matmul_vs_secuencial",
            "reduccion_l1d_load_misses_matmul_pct",
            "reduccion_l1dtlb_misses_matmul_pct",
        ],
        [
            [
                row["variant_label"],
                f"{row['cpu_speedup_vs_secuencial']:.6f}",
                f"{row['matmul_speedup_vs_secuencial']:.6f}",
                f"{row['l1d_load_reduction_vs_secuencial_pct']:.6f}",
                f"{row['l1dtlb_reduction_vs_secuencial_pct']:.6f}",
            ]
            for row in speedups
        ],
    )

    render_table_png(
        OUT_DIR / "profiling_comparacion_vs_secuencial.png",
        "Comparacion de profiling vs secuencial",
        [
            "Variante",
            "Speedup CPU total",
            "Speedup CPU matmul",
            "Reduccion L1D load (%)",
            "Reduccion L1DTLB (%)",
        ],
        [
            [
                row["variant_label"],
                f"{row['cpu_speedup_vs_secuencial']:.6f}",
                f"{row['matmul_speedup_vs_secuencial']:.6f}",
                f"{row['l1d_load_reduction_vs_secuencial_pct']:.6f}",
                f"{row['l1dtlb_reduction_vs_secuencial_pct']:.6f}",
            ]
            for row in speedups
        ],
        font_size=10,
        width_scale=1.55,
        height_scale=0.52,
    )

    plot_cpu(cpu_summary, speedups)
    plot_cpu_functions(function_summary)
    plot_counters(counter_summary)
    plot_cache_reduction(speedups)
    write_report_snippet(cpu_summary, function_summary, counter_summary, speedups)

    print(f"Archivos generados en: {OUT_DIR}")


if __name__ == "__main__":
    main()
