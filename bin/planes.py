#!/usr/bin/env python3
"""planes.py — trocea las celdas elegidas en un plan por job.

    planes.py <dist/> <salida/> <n-shards> <celda> [<celda> ...]

Un plan de GitHub Actions corre UN job = UN lane con su [from, to). Las celdas de
L4 son 2^32 enteras y el limite de GitHub-hosted es 6 h por job, asi que hay que
trocear. Con 20 trozos y ~50.000 semillas/s por nucleo, cada trozo cae a ~1,2 h:
de margen de sobra.
"""
import json
import os
import sys

DIST, OUT, NSHARDS = sys.argv[1], sys.argv[2], int(sys.argv[3])
# GitHub Actions pasa inputs.cells como UN argumento con comas, no como varios.
# Separo por comas aqui para que da igual como llegue.
CELLS = [c.strip() for arg in sys.argv[4:] for c in arg.split(",") if c.strip()]
if not CELLS:
    raise SystemExit("no se paso ninguna celda")

cells = json.load(open(os.path.join(DIST, "queued_cells.json")))
by_name = {c["lane"]: c for c in cells}

os.makedirs(OUT, exist_ok=True)
hechas = []

for lane in CELLS:
    if lane not in by_name:
        raise SystemExit(f"celda desconocida: {lane}")
    c = by_name[lane]
    lo, hi = int(c["from"]), int(c["to"])
    span = (hi - lo) // NSHARDS
    if span <= 0:
        raise SystemExit(f"{lane}: {NSHARDS} trozos para un rango de {hi-lo}")
    for s in range(NSHARDS):
        a = lo + s * span
        b = hi if s == NSHARDS - 1 else a + span
        lane_plan = dict(c)
        # EL NOMBRE DEL LANE NO SE TOCA. grind28 compara strcmp(g.lane,
        # lanes[i].name) contra lo que declara el gate (grind28.c:1390) y se niega
        # a barrer si no coincide exactamente. Ponerle un sufijo .s00 al lane
        # hacia que el gate describiera otra celda y el motor imprimia
        #   REFUSING lane L4-php_mt_scale-pair.s00: gate file ... describes a
        #   DIFFERENT cell (L4-php_mt_scale-pair/php_mt_scale/o0)
        # Cada trozo es su propio run-dir, asi que los ficheros de salida NO
        # colisionan aunque los 20 trozos se llamen igual.
        lane_plan["from"], lane_plan["to"] = a, b
        lane_plan["gate"] = os.path.join(
            DIST, "gates", os.path.basename(c["gate"]))
        ruta = os.path.join(OUT, f"{lane}__{s}.json")   # SIN ceros: coincide con la matriz
        with open(ruta, "w") as f:
            json.dump([lane_plan], f, indent=1)
        hechas.append((lane, s, a, b, b - a))

total = sum(h[3] - h[2] for h in hechas)
print(f"{len(hechas)} planes, {total:,} semillas en total")
for lane in CELLS:
    sub = [h for h in hechas if h[0] == lane]
    print(f"  {lane:28s} {len(sub):2d} trozos, {sum(h[3]-h[2] for h in sub):,} semillas")
print(f"  por trozo: ~{hechas[0][3]-hechas[0][2]:,} semillas")