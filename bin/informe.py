#!/usr/bin/env python3
"""informe.py — junta los trozos de cada celda y dice cuanto se cubrio de verdad.

    informe.py <dir-res/> <dist/> [--json]

LO QUE ESTE SCRIPT NO HACE, A PROPOSITO: no recalcula ninguna barra. La formula
de la barra es nullcurve19._fw, que esta en el upstream y no aqui, y reimplementarla
a ojo seria justo el tipo de error que este repo ya ha cometido una vez (ver el
bug del hibrido). Este script da los hechos; el umbral se calcula despues con su
codigo, y el propio informe lo dice.

  · n_claim_bar_hits de STATUS.json MIENTE tras cualquier reinicio (G_HITS se borra
    al arrancar y no se recarga). No se lee. Los candidatos se cuentan leyendo
    top_<lane>.json y candidates.jsonl.
  · La barra de cada celda esta calibrada para N = 2^32. Con cobertura parcial el
    umbral correcto es mas bajo: se calcula con panelmax_bar(rel, N=cubierto).
"""
import glob
import json
import os
import sys

RES, DIST = sys.argv[1], sys.argv[2]
AS_JSON = "--json" in sys.argv
N_TOTAL = 2 ** 32


def main():
    filas = []
    for d in sorted(glob.glob(os.path.join(RES, "res-*"))):
        st = os.path.join(d, "STATUS.json")
        if not os.path.exists(st):
            continue
        s = json.load(open(st))
        agg = s.get("aggregate", {})
        filas.append({
            "celda": s.get("current_lane", "?"),
            "relacion": s.get("relation", "?"),
            "claim_bar_2p32": s.get("claim_bar"),
            "cubiertos": agg.get("lane_words_covered", 0),
            "best_pmax": agg.get("best_pmax"),
            "best_seed": agg.get("best_word"),
            "n_candidatos": agg.get("n_candidates", 0),
        })

    por = {}
    for f in filas:
        # El lane NO lleva sufijo de trozo: los 20 trozos de una celda se llaman
        # igual (lo exige el gate) y se agrupan aqui por su nombre.
        base = f["celda"]
        p = por.setdefault(base, {"c": 0, "best": None, "seed": None, "cand": 0,
                                  "bar": f["claim_bar_2p32"], "rel": f["relacion"],
                                  "t": 0})
        p["t"] += 1
        p["c"] += f["cubiertos"]
        p["cand"] += f["n_candidatos"]
        if f["best_pmax"] is not None and (p["best"] is None or f["best_pmax"] > p["best"]):
            p["best"] = f["best_pmax"]
            p["seed"] = f["best_seed"]

    print(f"{'celda':30s} {'rel':6s} {'trozos':>7s} {'cobertura':>11s} "
          f"{'mejor pmax':>12s} {'semilla':>12s} {'cand':>8s}")
    print("-" * 92)
    salida = {"celdas": []}
    for base, p in sorted(por.items()):
        frac = p["c"] / N_TOTAL
        print(f"{base:30s} {p['rel']:6s} {p['t']:7d} {frac:10.2%} "
              f"{(p['best'] if p['best'] is not None else float('nan')):12.4f} "
              f"{(p['seed'] if p['seed'] is not None else -1):12d} {p['cand']:8d}")
        salida["celdas"].append({
            "celda": base, "relacion": p["rel"], "cobertura": frac,
            "best_pmax": p["best"], "best_seed": p["seed"],
            "candidatos": p["cand"], "trozos": p["t"],
            "claim_bar_de_2p32": p["bar"],
        })

    total_cand = sum(p["cand"] for p in por.values())
    print()
    print(f"total de candidatos sobre la barra de 2^32: {total_cand}")
    print()
    print("Avisos:")
    print("  · n_claim_bar_hits no se ha leido: miente tras cualquier reinicio.")
    print("  · ESTA TABLA NO CONTRASTA NADA todavia. La barra de cada celda esta")
    print("    calibrada para N = 2^32; con cobertura parcial hay que recalcularla")
    print("    con panelmax_bar(rel, N=cubierto) usando el codigo del upstream.")
    print("    Hasta que ese numero exista, un pmax alto aqui NO es un hallazgo.")
    if AS_JSON:
        # El nombre tiene que ser el que el workflow sube como artefacto.
        with open("resultados.json", "w", encoding="utf-8") as f:
            json.dump(salida, f, indent=1, ensure_ascii=False)
        print("\nresultados.json escrito")


if __name__ == "__main__":
    main()