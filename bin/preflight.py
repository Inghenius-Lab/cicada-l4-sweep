#!/usr/bin/env python3
"""preflight.py — comprueba lo que la cadena necesita, en 2 segundos.

    preflight.py <ruta-a-liber-primus-del-clon>

Por que existe: me costo un intento entero de Actions descubrir que faltaba
scipy, y se vio DESPUES de dos minutos de Monte Carlo. Esto hace que eso falle
alPrincipio del job.

DELIBERADAMENTE poco. La primera version importaba los 13 modulos de su grafo
y se rompia por culpa de la resolucion de rutas internas de SU codigo
(run_stats.py acaba pidiendo /data/krisyotam_runes.txt en absoluto). Eso es
problema suyo, no mio, y no hace falta para coger este fallo. Aqui solo se
comprueba lo que la cadena lee de disco y lo que necesita del sistema.
"""
import os
import shutil
import subprocess
import sys

LP = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")

FICHEROS = [
    "analysis/round19/I3/calib19.json",
    "analysis/round19/I3/run_i1i2.py",
    "analysis/round27/P0-spec/vectors.json",
    "analysis/round27/P0-spec/make_vectors.py",
    "analysis/round27/P1-engine/export_data.py",
    "analysis/round28/L4/grind28.c",
    "analysis/round28/L4/make_gates.py",
    "analysis/round28/L4/gen28.py",
    "analysis/round28/L4/ref_php.php",
    "src/lp/score.py",
    "data/krisyotam_runes.txt",
    "data/english_quadgrams.txt",
]

# El unico paquete de terceros que usa la cadena. scipy es el que falto.
PAQUETES = ["numpy", "scipy"]


def main():
    fallos = []

    for f in FICHEROS:
        if not os.path.isfile(os.path.join(LP, f)):
            fallos.append(f"falta el fichero {f}")

    for p in PAQUETES:
        r = subprocess.run([sys.executable, "-c", f"import {p}; print({p}.__version__)"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fallos.append(f"falta el paquete python3 {p}")
        else:
            print(f"  {p} {r.stdout.strip()}")

    for prog in ("php", "gcc"):
        if shutil.which(prog) is None:
            fallos.append(f"falta el programa {prog}")

    # models/ esta en el .gitignore del upstream: en un clon limpio no existe y
    # hay que poder crearlo para meter el panel.
    models = os.path.join(LP, "analysis", "round19", "I2", "models")
    try:
        os.makedirs(models, exist_ok=True)
    except Exception as e:
        fallos.append(f"no puedo crear {models}: {e}")

    if fallos:
        print("PREVIO FALLIDO:")
        for f in fallos:
            print("  -", f)
        return 1

    print(f"previo OK: {len(FICHEROS)} ficheros, {len(PAQUETES)} paquetes, "
          "php y gcc, models/ creable")
    return 0


if __name__ == "__main__":
    sys.exit(main())