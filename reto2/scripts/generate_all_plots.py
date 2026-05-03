#!/usr/bin/env python3
"""Generate all reto2 traffic plots."""

import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS = (
    "plot_density.py",
    "plot_size_performance.py",
    "plot_speedup_threads.py",
    "plot_speedup_o3.py",
    "plot_speedup_global.py",
    "generate_tables.py",
    "generate_cpu_profiling_tables.py",
    "plot_cpu_profiling.py",
    "generate_memory_profiling.py",
)


def main() -> None:
    for script in SCRIPTS:
        print(f"\n== {script} ==", flush=True)
        subprocess.run([sys.executable, str(SCRIPT_DIR / script)], check=True)


if __name__ == "__main__":
    main()
