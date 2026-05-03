#!/usr/bin/env python3
"""Generate CSV and PNG tables from gprof CPU profiling reports."""

from __future__ import annotations

from pathlib import Path
import re

from traffic_plot_utils import BASE_DIR, TABLES_DIR, ensure_dirs, write_table_artifacts


PROFILING_DIR = BASE_DIR / "profiling"
REPORTS = (
    ("Serial O0", PROFILING_DIR / "serial_CPU.txt", "serial_o0"),
    ("Serial O3", PROFILING_DIR / "o3_CPU.txt", "serial_o3"),
    ("Serial cache opt.", PROFILING_DIR / "cache_CPU.txt", "serial_cache"),
)

MAX_FUNCTIONS = 12
PROFILE_LINE = re.compile(
    r"^\s*"
    r"(?P<percent>\d+(?:\.\d+)?)\s+"
    r"(?P<cumulative>\d+(?:\.\d+)?)\s+"
    r"(?P<self_seconds>\d+(?:\.\d+)?)"
    r"(?:\s+(?P<calls>\d+))?"
    r"(?:\s+(?P<self_ms>\d+(?:\.\d+)?))?"
    r"(?:\s+(?P<total_ms>\d+(?:\.\d+)?))?"
    r"\s+(?P<name>[A-Za-z_.$][\w.$@~<>:]*)\s*$"
)


def parse_optional_number(value: str | None):
    if value is None:
        return ""
    return float(value)


def parse_optional_int(value: str | None):
    if value is None:
        return ""
    return int(value)


def parse_gprof_flat_profile(path: Path, version: str) -> list[dict[str, object]]:
    if not path.exists():
        return []

    rows = []
    in_flat_profile = False
    started_rows = False

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Flat profile:"):
            in_flat_profile = True
            continue

        if not in_flat_profile:
            continue

        if line.startswith(" %         the percentage"):
            break

        match = PROFILE_LINE.match(line)
        if not match:
            continue

        started_rows = True
        data = match.groupdict()
        rows.append(
            {
                "version": version,
                "funcion": data["name"],
                "porcentaje_tiempo": float(data["percent"]),
                "segundos_acumulados": float(data["cumulative"]),
                "segundos_propios": float(data["self_seconds"]),
                "llamadas": parse_optional_int(data["calls"]),
                "ms_por_llamada": parse_optional_number(data["self_ms"]),
                "ms_total_por_llamada": parse_optional_number(data["total_ms"]),
            }
        )

    if in_flat_profile and not started_rows:
        raise ValueError(f"No se pudo parsear el Flat profile de {path}")

    return rows


def write_version_table(version: str, path: Path, slug: str) -> list[dict[str, object]]:
    rows = parse_gprof_flat_profile(path, version)
    if not rows:
        print(f"Saltando {version}: no existe {path}")
        return []

    rows = rows[:MAX_FUNCTIONS]
    fields = [
        "version",
        "funcion",
        "porcentaje_tiempo",
        "segundos_propios",
        "segundos_acumulados",
        "llamadas",
        "ms_por_llamada",
        "ms_total_por_llamada",
    ]
    labels = {
        "version": "Version",
        "funcion": "Funcion",
        "porcentaje_tiempo": "% tiempo",
        "segundos_propios": "Seg. propios",
        "segundos_acumulados": "Seg. acum.",
        "llamadas": "Llamadas",
        "ms_por_llamada": "ms/llamada",
        "ms_total_por_llamada": "ms total/llamada",
    }
    write_table_artifacts(
        TABLES_DIR / f"tabla_cpu_profiling_{slug}.csv",
        TABLES_DIR / f"tabla_cpu_profiling_{slug}.png",
        rows,
        fields,
        f"Profiling CPU gprof: {version}",
        labels,
    )
    return rows


def write_global_tables(all_rows: list[dict[str, object]]) -> None:
    if not all_rows:
        return

    fields = [
        "version",
        "funcion",
        "porcentaje_tiempo",
        "segundos_propios",
        "llamadas",
        "ms_por_llamada",
    ]
    labels = {
        "version": "Version",
        "funcion": "Funcion",
        "porcentaje_tiempo": "% tiempo",
        "segundos_propios": "Seg. propios",
        "llamadas": "Llamadas",
        "ms_por_llamada": "ms/llamada",
    }

    top_rows = sorted(all_rows, key=lambda r: float(r["segundos_propios"]), reverse=True)[:MAX_FUNCTIONS]
    write_table_artifacts(
        TABLES_DIR / "tabla_cpu_profiling_global.csv",
        TABLES_DIR / "tabla_cpu_profiling_global.png",
        top_rows,
        fields,
        "Profiling CPU gprof: funciones principales",
        labels,
    )

    update_rows = [row for row in all_rows if row["funcion"] == "update_road"]
    if update_rows:
        write_table_artifacts(
            TABLES_DIR / "tabla_cpu_profiling_update_road.csv",
            TABLES_DIR / "tabla_cpu_profiling_update_road.png",
            update_rows,
            fields,
            "Profiling CPU gprof: update_road",
            labels,
        )


def main() -> None:
    ensure_dirs()
    all_rows = []
    for version, path, slug in REPORTS:
        all_rows.extend(write_version_table(version, path, slug))
    write_global_tables(all_rows)


if __name__ == "__main__":
    main()
