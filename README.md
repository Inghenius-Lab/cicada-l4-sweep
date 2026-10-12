# cicada-l4-sweep

Corrida de las **3 celdas `pair` de mayor prioridad** de `Round 28 / L4` de
[`Dukotah/cicada3301`](https://github.com/Dukotah/cicada3301), sobre runners
gratis de GitHub Actions.

## Qué es y qué no es

- **NO** descifra el Liber Primus. La cryptanálisis sigue cerrada por instrumento.
- **SÍ** cubre el último eje sin barrer de la familia de claves derivadas: tres
  generadores PHP de `mt_rand` bajo la relación `pair` (= `keyskip2` = `skip_by_two`,
  la construcción que reproduce el doublet rate observado en el LP2), 2³² semillas
  cada uno.
- El resultado es un **dato de cobertura y mejor pmax**, no un veredicto. Lo
  convierte en veredicto el adjudication de tres cláusulas de `hitfn20`, con el
  umbral recalculado para la cobertura real.

## Por qué este repo existe

Porque `Dukotah/cicada3301` **no puede correr su propio instrumento** desde un clon
limpio. Motivo, medido y con SHA-256:

| entrada | estado upstream |
|---|---|
| `analysis/round19/I2/models/panel.npz` | **`models/` está en su `.gitignore` (línea 3)** y **no hay ningún `.npz`/`.npy` commiteado en todo el repo** |
| `analysis/round27/P0-spec/vectors.json` | commiteado, pero calculado contra **otro** panel |
| `analysis/round19/I3/calib19.json` | commiteado, con las barras calibradas contra ese otro panel |

Y el efecto es silencioso. `export_data.py` saca las tablas `LM` del panel y el
`MU`/`SD` de `vectors.json`, así que el motor resultante puntúa con un **híbrido**:
descifra **idéntico** a la referencia Python (las 120 runas coinciden) pero puntúa
distinto. `--self-test` da 20/64 y las 25 puertas fallan, sin ningún error visible.

**Aquí se lleva el `panel.npz` que falta**, con su procedencia:

```
sha256 8e77a4a542c95170946645c30780e343afd9772233b87d34654ba78bd1653eb5
origen  Dukotah/cicada3301 @ f08b20b, arbol de trabajo (NO versionado upstream)
       -> blob panel_lm.f32 derivado: sha256 82b92342605e6367...
```

## Qué hace `bin/preparar.sh`

La cadena completa, en el orden que el propio `INTERFACE.md` del upstream ordena:

1. `gen28.py --selftest` — los generadores contra las referencias de la máquina (`pass=True`, 50 checks)
2. `run_i1i2.py --stage i1 --preset pair` — **re-ajusta las 13 celdas `driftbeam.pair`**
3. re-basa `vectors.json` al panel ⇒ **esto elimina el híbrido**
4. `export_data.py` → `engine.dat` con `MU`/`SD` del panel correcto
5. `make_gates.py` → las 25 puertas
6. `grind28 --self-test` **y** las 25 `--gate-check`

Si el self-test o las 25 puertas no pasan, el script **aborta** y no se barre nada.

Coste medido: **≈10 minutos** en un runner de 2 núcleos.

### ⭐ El cambio en las barras

| | antes | después |
|---|---|---|
| barra `pair` a N = 2³² | 9,638182362052774 | **≈10,44** |
| `mu` de la celda | 2,4199696989376633 | ≈2,153 |

**+0,80 ± 0,03.** La barra estaba **0,8 z por debajo** de donde debe: el
instrumento era demasiado estricto. Tres re-ajustes independientes dieron
10,410084 / 10,461785 / 10,443295, así que **el propio ajuste tiene ~0,05 de
dispersión** y `M = 60000` es bajo para una barra.

⚠️ **Las 5 celdas `exact` conservan la barra VIEJA** (10,031081507059358):
`--preset exact` produce la celda `I19:driftbeam.exact+I2` pero la barra sale de
`I19:vecbeam.keyskip1+I2`, que son claves distintas. Por eso aquí solo se barren
celdas `pair`.

## Cómo corre

```
preparar  ->  SELF-TEST PASS + 25/25 puertas, sube dist/ y 60 planes
barrer    ->  matriz 3 celdas x 20 trozos = 60 jobs, 20 a la vez
             cada trozo: 2^32/20 = 214.748.364 semillas  (~1,2 h)
informe   ->  une los trozos, dice cobertura real y mejor pmax
```

Tiempo de reloj esperado: **≈3,6 h** para las 3 celdas completas.

Coste: **0 €.** Los minutos de un repo **público** con runners estándar son
gratis ([docs](https://docs.github.com/en/billing/concepts/product-billing/github-actions)).
Los límites que importan: **20 jobs concurrentes** (plan Free) y **6 h por job** —
por eso las celdas van troceadas.

## Las tres cosas que este repo NO te va a decir

1. **No hay veredicto aquí.** `informe.py` **no recalcula ninguna barra**: eso es
   `nullcurve19._fw`, que vive en el upstream, y reimplementarlo a mano sería
   exactamente el error que este repo acaba de encontrar.
2. **`n_claim_bar_hits` de `STATUS.json` miente** tras cualquier reinicio:
   `G_HITS` se borra al arrancar (`G_NHITS = 0`) y nunca se recarga, mientras que
   `best_pmax` sí. Por eso el informe **no lo lee**.
3. **La cobertura parcial no se contrasta con la barra de 2³².** El umbral propio
   de una cobertura `c` es `panelmax_bar(rel, N=c)`, más bajo. Hasta que ese
   número exista, un `pmax` alto **no es un hallazgo**.

## Reproducir

```bash
git clone https://github.com/Inghenius-Lab/cicada-l4-sweep
bash bin/preparar.sh /ruta/al/clon/Dukotah/liber-primus panel/panel.npz /tmp/work
```

Y una celda suelta, en local:

```bash
python3 bin/planes.py /tmp/work/dist /tmp/work/planes 20 L4-php_mt_scale-pair
/tmp/work/dist/grind28 --plan /tmp/work/planes/L4-php_mt_scale-pair__00.json \
                       --run-dir /tmp/run --threads 2
```