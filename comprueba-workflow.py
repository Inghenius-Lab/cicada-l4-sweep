#!/usr/bin/env python3
"""comprueba-workflow.py — validacion estatica, SIN subir nada.

Un job sin actions/checkout tiene un workspace VACIO salvo lo que baja de
artefactos (docs: "GitHub provisions an isolated virtual machine for each job").
Eso hizo que bin/verifica-barriento.py no existiera y los 5 primeros jobs
fallaran. Este script lo coge antes de gastar un intento.
"""
import ast
import subprocess
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent
W = RAIZ / ".github" / "workflows" / "sweep.yml"

fallos = []

try:
    d = yaml.safe_load(W.read_text(encoding="utf-8"))
except Exception as e:
    raise SystemExit(f"YAML MAL: {e}")

# --- 1) TODO job que use un script del repo necesita checkout ---
print("  checkout por job:")
for jn, j in d["jobs"].items():
    pasos = j["steps"]
    usa_script = any("bin/" in str(s.get("run", "")) for s in pasos)
    tiene = any("checkout" in str(s.get("uses", "")) for s in pasos)
    if usa_script and not tiene:
        fallos.append(f"{jn} usa bin/ pero NO tiene actions/checkout")
        marca = "FALTA"
    else:
        marca = "ok "
    print(f"    {marca}  {jn:10s} checkout={tiene}  usa_bin={usa_script}")

# --- 2) todo lo que el workflow invoca existe y parsea ---
print("\n  scripts invocados por el workflow:")
invocados = set()
for j in d["jobs"].values():
    for s in j["steps"]:
        for tok in str(s.get("run", "")).replace("\\", " ").split():
            if tok.startswith("bin/"):
                invocados.add(tok.strip("\"'"))

for f in sorted(invocados):
    p = RAIZ / f
    if not p.is_file():
        print(f"    FALTA   {f}  (lo invoca el workflow y no existe)")
        fallos.append(f"el workflow invoca {f} y no existe")
        continue
    if f.endswith(".sh"):
        r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
        ok = r.returncode == 0
        print(f"    {'ok  ' if ok else 'MAL '}   {f}  (bash -n)")
        if not ok:
            print(f"           {r.stderr.strip()[:160]}")
            fallos.append(f"{f} no pasa bash -n")
    else:
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            print(f"    ok       {f}")
        except SyntaxError as e:
            print(f"    MAL      {f}: {e}")
            fallos.append(f"{f} no parsea: {e}")

# --- 3) la matriz viene de un output generado, no esta escrita a mano ---
print("\n  matriz de barrer:")
mat = str(d["jobs"]["barrer"]["strategy"]["matrix"])
if "fromJSON(needs.preparar.outputs.matriz)" in mat:
    print(f"    ok       dinamica desde preparar")
else:
    print(f"    AVISO    estatica: {mat}")

print("\n  planes.py genera matriz.json:")
txt = (RAIZ / "bin" / "planes.py").read_text(encoding="utf-8")
if "matriz.json" in txt:
    print("    ok")
else:
    print("    FALTA")
    fallos.append("planes.py no genera matriz.json")

# --- 4) el informe escribe el fichero que el workflow sube ---
print("\n  informe.py escribe lo que el workflow sube:")
inf = (RAIZ / "bin" / "informe.py").read_text(encoding="utf-8")
subidas = [s for s in yaml.safe_load(W.read_text(encoding="utf-8"))["jobs"]["informe"]["steps"]
           if "upload-artifact" in str(s.get("uses", ""))]
for s in subidas:
    ruta = str((s.get("with") or {}).get("path", ""))
    existe = any(ruta == nombre or ruta in nombre for nombre in
                 ("resultados.json", "informe.json")) if ruta else True
    print(f"    {'ok  ' if existe else 'MAL '}   sube {ruta!r}; "
          f"informe.py menciona resultados.json: {'resultados.json' in inf}")
    if not existe:
        fallos.append(f"el workflow sube {ruta} pero informe.py no lo escribe")

print()
if fallos:
    print("FALLOS:")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
print("VALIDACION ESTATICA: todo en verde.")
print("Ojo: esto NO prueba que los jobs corran. Solo que el workflow esta bien")
print("escrito. Para eso esta el modo smoke.")