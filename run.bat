@echo off
setlocal EnableExtensions

set "DIR=C:\Users\juanv\OneDrive\Escritorio\HPC"
set "EXE=%DIR%\mul.exe"
set "OUT=%DIR%\times2.txt"

REM Encabezado
echo round N threads trial wall_s user_s kernel_s cpu_total_s checksum seed > "%OUT%"

REM Lista de tamaños (ajústala a lo que necesitas)
set NS=400 2000 3000 4000

REM 10 rondas (for invertido: ronda afuera, N adentro)
for /L %%R in (1,1,10) do (
  for %%N in (%NS%) do (
    "%EXE%" %%N 1 1 123456789 >> "%OUT%"
  )
)

endlocal
echo Listo: "%OUT%"