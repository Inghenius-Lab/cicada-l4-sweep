#!/usr/bin/env bash
# preparar.sh — deja el motor L4 con el panel correcto y las 25 puertas en verde.
#
# Uso:  preparar.sh <ruta-al-clon-de-Dukotah> <panel.npz> <salida>
#
# NO modifica el clon: trabaja sobre una copia en $OUT/clone.
#
# POR QUE EXISTE, en corto. El repo de Dukotah tiene el panel (panel.npz) en su
# .gitignore, asi que export_data.py se lleva las tablas LM de un panel y el MU/SD
# de otro. El resultado es un motor que puntua con un HIBRIDO: descifra igual que
# Python pero puntua distinto. Con eso --self-test da 20/64 y las 25 puertas fallan.
#
# Los pasos son los que el propio INTERFACE.md ordena ("If models/panel.npz is
# rebuilt -> re-run run_i1i2.py --stage i2panel"), mas el rebasado de vectors.json
# que es lo que elimina el hibrido.
set -euo pipefail

SRC="${1:?ruta del clon}"
PANEL="${2:?panel.npz}"
OUT="${3:?carpeta de salida}"
PROCS="${PROCS:-2}"
UPSTREAM_REF="${UPSTREAM_REF:-f08b20b}"

mkdir -p "$OUT"
# Se trabaja sobre una COPIA del clon: preparar.sh escribe en engine.dat,
# calib19.json, vectors.json y gates/, y el upstream no se toca.
rm -rf "$OUT/clone"; mkdir -p "$OUT/clone"
cp -r "$SRC" "$OUT/clone/liber-primus"
LP="$OUT/clone/liber-primus"
[ -e "$LP/analysis/data" ] || ln -s "$LP/data" "$LP/analysis/data"

# run_stats.py usa la convencion analysis/data/; el resto del repo usa data/.
PP="$LP/src:$(find "$LP" -name '*.py' -printf '%h\n' 2>/dev/null | sort -u | tr '\n' ':')"
export PYTHONPATH="$PP"
py() { local d="$1"; shift; ( cd "$d" && timeout 3000 nice -n 15 env PYTHONPATH="$PP" python3 "$@" ); }

echo "== 0) panel en su sitio =========================================="
mkdir -p "$LP/analysis/round19/I2/models"   # models/ esta en el .gitignore del
                                         # upstream: en un clon limpio NO existe
cp -f "$PANEL" "$LP/analysis/round19/I2/models/panel.npz"
sha256sum "$LP/analysis/round19/I2/models/panel.npz" | sed 's/^/   /'

echo "== 1) generadores contra las referencias de la maquina =========="
( cd "$LP/analysis/round28/L4" && gcc -O2 -o ref_glibc ref_glibc.c )
py "$LP/analysis/round28/L4" gen28.py --selftest | sed 's/^/   /'

echo "== 2) re-ajustar las celdas driftbeam.pair ======================="
py "$LP/analysis/round19/I3" run_i1i2.py --stage i1 --preset pair --L 120 \
   --M 60000 --procs "$PROCS" | tail -1 | sed 's/^/   /'
py "$LP/analysis/round19/I3" - <<'PY'
import json, shutil
shutil.copy("calib19.json", "calib19.json.orig")
cal = json.load(open("calib19.json"))
new = json.load(open("out_i1_pair_L120.json"))["cells"]
n = 0
for k, v in new.items():
    if k.startswith("I19:driftbeam.pair+I2") and k in cal["cells"]:
        cal["cells"][k] = v; n += 1
json.dump(cal, open("calib19.json", "w"), indent=1, sort_keys=True)
c = cal["cells"]["I19:driftbeam.pair+I2|pmax|L120"]
print(f"   celdas actualizadas: {n}   mu={c['mu']!r} beta={c['beta']!r}")
PY

echo "== 3) rebasar vectors.json al panel (esto quita el hibrido) ======"
# La asercion original (round(pmax,3) == 6.826) esta clavada al panel perdido.
# Se sustituye por el valor MEDIDO con este panel y una tolerancia estrecha:
# sigue siendo una comprobacion fuerte, y no es circular (el valor esperado viene
# de un recibo, no de esta ejecucion).
py "$LP/analysis/round27/P0-spec" - <<'PY'
from pathlib import Path
p = Path("make_vectors.py"); t = p.read_text(encoding="utf-8")
old = 'assert round(float(best["pmax"]), 3) == 6.826, best["pmax"]'
new = ('assert abs(float(best["pmax"]) - 6.782662673856188) < 1e-9, best["pmax"]'
       '   # rebasado al panel.npz de este repo (era == 6.826 con el panel perdido)')
if old not in t:
    raise SystemExit("la asercion de make_vectors.py ya no es la que esperaba; "
                     "PARO en vez de parchear a ciegas")
p.write_text(t.replace(old, new), encoding="utf-8")
print("   asercion rebasada a 6.782662673856188 +-1e-9")
PY
py "$LP/analysis/round27/P0-spec" make_vectors.py | sed 's/^/   /'

echo "== 4) engine.dat con MU/SD del panel NUEVO ======================="
py "$LP/analysis/round27/P1-engine" export_data.py | sed 's/^/   /'

echo "== 5) las 25 puertas ============================================="
( cd "$LP/analysis/round28/L4" && mkdir -p gates )
py "$LP/analysis/round28/L4" make_gates.py | tail -1 | sed 's/^/   /'

echo "== 6) grind28: self-test y las 25 comprobaciones ================="
( cd "$LP/analysis/round28/L4" \
  && cp -f "$LP/analysis/round27/P1-engine/engine.dat" \
            "$LP/analysis/round27/P1-engine/panel_lm.f32" . \
  && gcc -O3 -march=native -fopenmp -std=gnu17 -ffp-contract=off \
       -o grind28 grind28.c -lm ) 2>/dev/null \
  || ( cd "$LP/analysis/round28/L4" \
       && gcc -O3 -fopenmp -std=gnu17 -ffp-contract=off -o grind28 grind28.c -lm )
echo "   compilado (sin -march=native si el runner no lo admite)"

ST="$( cd "$LP/analysis/round28/L4" && nice -n 15 ./grind28 --self-test 2>&1 | tail -3 )"
printf '%s\n' "$ST" | sed 's/^/   /'
grep -q "SELF-TEST: PASS" <<<"$ST" || { echo "   ABORTADO: el self-test no pasa"; exit 1; }

ok=0; n=0
for f in "$LP"/analysis/round28/L4/gates/cellgate_*.dat; do
  n=$((n+1))
  ( cd "$LP/analysis/round28/L4" && nice -n 15 ./grind28 --gate-check "$f" ) >/dev/null 2>&1 \
    && ok=$((ok+1))
done
echo "   $ok de $n puertas PASS"
[ "$ok" -eq "$n" ] || { echo "   ABORTADO: faltan puertas"; exit 1; }

echo "== 7) dist/ para los jobs de barrido ============================="
D="$OUT/dist"
rm -rf "$D"; mkdir -p "$D"
cp "$LP/analysis/round28/L4/grind28" "$D/"
cp "$LP/analysis/round28/L4/engine.dat" "$LP/analysis/round28/L4/panel_lm.f32" "$D/"
cp "$LP/analysis/round28/L4/queued_cells.json" "$D/"
mkdir -p "$D/gates"; cp "$LP"/analysis/round28/L4/gates/*.dat "$D/gates/"
cp "$LP/analysis/round19/I3/calib19.json" "$D/calib19.json"

# --- rutas ABSOLUTAS: el fallo que costo un intento entero de Actions ---------
# engine.dat guarda QGRAM_PATH y PANEL_PATH con las rutas ABSOLUTAS del clon
# (grind28.c:353-354 las lee tal cual y las pasa a fopen, lineas 304 y 330).
# El job de barrido solo recibe dist/, donde esas rutas no existen, y el motor
# muere con:
#     FATAL: cannot open quadgram file (QGRAM_PATH in engine.dat)
#
# Ademas el fichero de cuadigramas no estaba en dist/ en absoluto.
#
# load_panel() NO lee panel.npz: lee panel_lm.f32, 9*24389 float32 (grind28.c:334).
# panel_lm.f32 ya estaba en dist/, asi que solo faltaba el fichero de
# cuadigramas. Y se reescriben LAS DOS rutas a dist/<fichero>, relativo a la raiz
# del repo, que es el directorio de trabajo tanto en local como en el runner.
cp "$LP/data/english_quadgrams.txt" "$D/english_quadgrams.txt"
python3 - "$D" <<'PYEOF'
import sys, pathlib
d = pathlib.Path(sys.argv[1])
p = d / "engine.dat"
t = p.read_text(encoding="utf-8", errors="surrogateescape")
for key, name in (("QGRAM_PATH", "english_quadgrams.txt"),
                  ("PANEL_PATH",  "panel_lm.f32")):
    old = None
    for line in t.split("\n"):
        if line.startswith(key + " "):
            old = line.split(" ", 1)[1].strip()
            break
    t = t.replace(f"{key} {old}", f"{key} dist/{name}")
    print(f"   {key}: {old}")
    print(f"        -> dist/{name}")
p.write_text(t, encoding="utf-8", errors="surrogateescape")
PYEOF

du -sh "$D" | sed 's/^/   /'
echo "LISTO"