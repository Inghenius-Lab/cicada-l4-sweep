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
CELLS = sys.argv[4:]

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
        lane_plan["lane"] = f"{lane}.s{s:02d}"   # sin '#': va a nombres de fichero
        lane_plan["from"], lane_plan["to"] = a, b
        lane_plan["gate"] = os.path.join(
            DIST, "gates", os.path.basename(c["gate"]))
        ruta = os.path.join(OUT, f"{lane}__{s:02d}.json")
        with open(ruta, "w") as f:
            json.dump([lane_plan], f, indent=1)
        hechas.append((lane, s, a, b, b - a))

total = sum(h[3] - h[2] for h in hechas)
print(f"{len(hechas)} planes, {total:,} semillas en total")
for lane in CELLS:
    sub = [h for h in hechas if h[0] == lane]
    print(f"  {lane:28s} {len(sub):2d} trozos, {sum(h[3]-h[2] for h in sub):,} semillas")
print(f"  por trozo: ~{hechas[0][3]-hechas[0][2]:,} semillas")