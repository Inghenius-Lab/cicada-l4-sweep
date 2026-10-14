#!/usr/bin/env python3
"""planes.py — trocea las celdas elegidas en un plan por job.

    planes.py <dist/> <salida/> <n-shards> <prefijo-gates> <celdas> [--max-seeds N]

`<prefijo-gates>` es DONDE viviran las puertas cuando el job de barrido las lea, y
se escribe dentro del plan. Va antes de las celdas y separado por posicion a
proposito: las celdas SI pueden llegar como un argumento con comas (eso hace
GitHub Actions con inputs.cells), y un prefijo nunca lleva comas. Un argumento
que empieza por `--` es opcion.

Importa, y no es cosmetico: si se pasa la ruta de construccion (`work/dist`), el
plan lleva `work/dist/gates/...` y el job de barrido -que corre desde la raiz del
repo, donde no existe `work/`- muere con

    FATAL: cannot open gate file work/dist/gates/cellgate_....dat

`--max-seeds N` corta cada trozo en N semillas. NO produce datos: solo sirve para
comprobar que la cadena entera va bien en minutos. Sin ese modo, probar un
cambio de workflow cuesta 8 h; con el, cuesta 3.

Ademas escribe `matriz.json` al lado de los planes: la lista real de
{celda, trozo} que el workflow pasa a `strategy.matrix`, para que la matriz
nunca se pueda desincronizar de los planes.
"""
import json
import os
import sys

argv = sys.argv[1:]
MAX_SEEDS = 0
if "--max-seeds" in argv:
    i = argv.index("--max-seeds")
    MAX_SEEDS = int(argv[i + 1])
    del argv[i:i + 2]

if len(argv) < 5:
    raise SystemExit(
        "uso: planes.py <dist/> <salida/> <n-shards> <prefijo-gates> <celdas> "
        "[--max-seeds N]")

DIST, OUT, NSHARDS = argv[0], argv[1], int(argv[2])
PREFIX_GATES = argv[3]
CELLS = [c.strip() for arg in argv[4:] for c in arg.split(",") if c.strip()]

if not CELLS:
    raise SystemExit("no se paso ninguna celda")
if "," in PREFIX_GATES:
    raise SystemExit(f"el prefijo de las puertas no puede llevar comas: {PREFIX_GATES!r}")
if MAX_SEEDS and NSHARDS != 1:
    raise SystemExit("--max-seeds solo tiene sentido con 1 trozo por celda")

cells = json.load(open(os.path.join(DIST, "queued_cells.json")))
by_name = {c["lane"]: c for c in cells}

os.makedirs(OUT, exist_ok=True)
hechas = []

for lane in CELLS:
    if lane not in by_name:
        raise SystemExit(f"celda desconocida: {lane}")
    c = by_name[lane]
    lo, hi = int(c["from"]), int(c["to"])
    if MAX_SEEDS:
        hi = min(hi, lo + MAX_SEEDS)
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
            PREFIX_GATES, "gates", os.path.basename(c["gate"]))
        ruta = os.path.join(OUT, f"{lane}__{s}.json")   # SIN ceros: coincide con la matriz
        with open(ruta, "w") as f:
            json.dump([lane_plan], f, indent=1)
        hechas.append((lane, s, a, b, b - a))

# La matriz REAL que va a usar el workflow. Se genera aqui, a partir de los
# mismos datos que los planes, para que no se puedan desincronizar.
matriz = [{"celda": lane, "trozo": s} for lane, s, _, _, _ in hechas]
with open(os.path.join(OUT, "matriz.json"), "w") as f:
    json.dump(matriz, f)

total = sum(h[3] - h[2] for h in hechas)
print(f"{len(hechas)} planes, {total:,} semillas en total")
for lane in CELLS:
    sub = [h for h in hechas if h[0] == lane]
    print(f"  {lane:28s} {len(sub):2d} trozos, {sum(h[3]-h[2] for h in sub):,} semillas")
print(f"  por trozo: ~{hechas[0][3]-hechas[0][2]:,} semillas")
print(f"  prefijo de las puertas en el plan: {PREFIX_GATES!r}")
if MAX_SEEDS:
    print(f"  MODO SMOKE: --max-seeds {MAX_SEEDS:,}. NO produce datos.")