#!/usr/bin/env python3
"""
El piso de la pieza, medido sobre el g-code: cuánto apoya y cuánto queda libre.

Existe porque los dos números que gobiernan la base —el diámetro del disco de
apoyo y el del agujero del encastre— no están escritos en ninguna parte del
archivo. El del hueco es un parámetro (`--piso`), pero el del disco SALE del
corte del perfil (`--perfil-desde`), así que moverlo es a ciegas: hay que
generar, abrir en Orca y leer la cota a ojo.

Y no alcanza con creerle al generador. `--piso` es el diámetro que tiene que
QUEDAR libre, no el del recorrido: el cordón va centrado en la trayectoria y se
come medio cordón por lado (ver `comun.radio_de_hueco`). O sea que entre el
parámetro y la pieza hay una cuenta, y esa cuenta es justo la que hay que
comprobar cuando se mueve la base — porque el pedido es que el hueco NO cambie
mientras el disco sí.

**Cómo se mide.** Se toma la primera capa —todo lo que esté por debajo del
primer cordón más un alto de capa— y se miran los radios de sus segmentos
extruidos respecto del centro:

  - el disco de apoyo llega hasta el radio MÁXIMO más medio cordón, porque el
    cordón sobresale medio ancho del eje de la trayectoria;
  - el hueco libre llega hasta el radio MÍNIMO menos medio cordón, por lo mismo
    y del otro lado.

Se informan las dos convenciones —lo depositado y el recorrido— porque el visor
mide el recorrido y el encastre mide lo depositado, y confundirlas es un cordón
entero de error justo donde entra otra pieza.

El diámetro del piso puede dar hasta ~1 mm más que el que anuncia el generador,
y no es un desacuerdo: la pared arranca a la MISMA altura que el disco y se abre
mientras sube, y su primera fracción de vuelta todavía se escribe con la z del
disco (el g-code lleva tres decimales). Eso también apoya en la cama, así que
cuenta.

Los viajes sin extruir no cuentan: el collar del refuerzo baja al centro sin
material y arrastraría el mínimo hasta el eje.

    python3 verificar_piso.py output/hongo/hongo_latest.gcode [--ancho 1.2]
"""

import argparse
import math
import sys

from verificar_pieza import leer


def medir(segs, ancho, centro=(128.0, 128.0)):
    cx, cy = centro
    z0 = min(min(s[2], s[5]) for s in segs)
    # Solo lo PLANO, no "la primera capa".
    #
    # La espiral del piso vive entera a una sola altura y la pared arranca
    # subiendo desde ahí, así que una ventana de un cordón de alto ya se come
    # las primeras vueltas de pared — que en un bol abierto son más anchas que
    # el disco. Medido en el hongo, eso daba Ø163.8 contra los Ø160.7 que apoyan
    # de verdad: 3 mm de más, justo del orden de lo que se quiere distinguir al
    # mover el corte.
    #
    # La tolerancia es de una micra, no "unas décimas": la pared arranca a la
    # MISMA altura que el disco y sube desde ahí abriéndose, así que una ventana
    # de 0.05 mm ya deja entrar 154 segmentos de pared que sobresalen 0.4 mm del
    # piso real. El disco es estrictamente plano y con eso alcanza para aislarlo.
    techo = z0 + 1e-6
    radios = []
    for s in segs:
        if max(s[2], s[5]) > techo:
            continue
        radios.append(math.hypot(s[0] - cx, s[1] - cy))
        radios.append(math.hypot(s[3] - cx, s[4] - cy))
    if not radios:
        raise SystemExit("no encontré segmentos extruidos en la primera capa")
    r_int, r_ext = min(radios), max(radios)
    return {
        "z": z0,
        "segmentos": len(radios) // 2,
        "hueco": max(0.0, 2 * (r_int - ancho / 2)),
        "hueco_recorrido": 2 * r_int,
        "piso": 2 * (r_ext + ancho / 2),
        "piso_recorrido": 2 * r_ext,
        "anillo": (r_ext - r_int),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("gcode", nargs="+")
    p.add_argument("--ancho", type=float, default=1.2, help="ancho del cordón en mm")
    p.add_argument("--centro", type=float, nargs=2, default=(128.0, 128.0))
    a = p.parse_args(argv)

    for ruta in a.gcode:
        d = medir(leer(ruta, a.ancho), a.ancho, tuple(a.centro))
        print(f"{ruta}")
        print(f"  disco plano en z {d['z']:.2f} · {d['segmentos']} segmentos")
        print(f"  piso  Ø{d['piso']:7.1f} mm  (recorrido Ø{d['piso_recorrido']:.1f})"
              f"   <- lo que apoya en la cama")
        print(f"  hueco Ø{d['hueco']:7.1f} mm  (recorrido Ø{d['hueco_recorrido']:.1f})"
              f"   <- lo que queda libre para el encastre")
        print(f"  anillo {d['anillo']:6.1f} mm de ancho")
        if d["anillo"] < 2 * a.ancho:
            print("  OJO: el anillo del piso mide menos de dos cordones; eso no es un "
                  "piso, es un aro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
