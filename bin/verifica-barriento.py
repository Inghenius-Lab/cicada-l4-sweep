#!/usr/bin/env python3
"""verifica-barriento.py — un job que no barre NADA no puede salir verde.

    verifica-barriento.py <run-dir>/STATUS.json

Este script es la red que faltaba. En el primer intento 26 de los 60 jobs de
barrido seonoraron VERDE con un artefacto de 148 bytes: el motor habia impreso
    FATAL: cannot open gate file work/dist/gates/...
pero como la orden estaba dentro de un `| tee`, el estado que veia `set -e` era
el de tee, que es 0. El jobfilledlight verde sin haber barriido una sola semilla.

Un job que reporta exito y no ha hecho el trabajo es peor que un job que falla:
el primero te hace creer que ya tienes el dato. Asi que ahora cada job comprueba,
con su propio STATUS.json, que hay semillas contadas. Salida distinta de 0 si no.
"""
import json
import sys


def main():
    if len(sys.argv) < 2:
        print("falta la ruta del STATUS.json")
        return 2
    try:
        d = json.load(open(sys.argv[1], encoding="utf-8"))
    except Exception as e:
        print(f"  NO SE PUEDE LEER el STATUS.json: {type(e).__name__}: {e}")
        return 1

    a = d.get("aggregate", {})
    hechos = a.get("seeds_done", 0)

    print(f"  lane                = {d.get('current_lane')}")
    print(f"  relacion            = {d.get('relation')}")
    print(f"  claim_bar (2^32)    = {d.get('claim_bar')}")
    print(f"  seeds_done          = {hechos:,}")
    print(f"  mejor pmax          = {a.get('best_pmax')}")
    print(f"  mejor semilla       = {a.get('best_word')}")
    print(f"  candidatos          = {a.get('n_candidates')}")
    print(f"  cadencia            = {a.get('throughput_seeds_per_s')} semillas/s")

    if not hechos or hechos <= 0:
        print("CERO semillas barrenadas: este job no ha hecho nada")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())