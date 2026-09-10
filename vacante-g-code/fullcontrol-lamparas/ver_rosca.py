#!/usr/bin/env python3
"""
Desenrolla el cilindro de un g-code de rosca y lo guarda como PNG.

Existe porque dibujar la FUNCIÓN del patrón en una grilla limpia no sirve para
juzgar nada: siempre se ve bien. Entre la función y la pieza está el hilo
helicoidal —filas cada 13.5 mm, cresta de 8 mm de alto— y el mismo dibujo se
comporta distinto. Todos los defectos reales de los patrones aparecieron sólo
mirando el g-code, nunca el render de la función.

    python ver_rosca.py output/rosca/caritas_lienzo_v2400.gcode

El PNG queda al lado del g-code. Claro = hilo saliente, oscuro = pared lisa.
"""
import math
import re
import sys

import numpy as np
from PIL import Image


def leer(ruta):
    x = y = z = 0.0
    pts = []
    for ln in open(ruta, errors="ignore"):
        if not ln.startswith("G1"):
            continue
        for c in "XYZ":
            m = re.search(c + r"(-?[\d.]+)", ln)
            if m:
                v = float(m.group(1))
                if c == "X":
                    x = v
                elif c == "Y":
                    y = v
                else:
                    z = v
        me = re.search(r"E(-?[\d.]+)", ln)
        if me and float(me.group(1)) > 0:
            pts.append((x, y, z))
    return np.array(pts)


def desenrollar(ruta, ancho_px=1400, alto_px=None, z0=5.0, z1=None):
    P = leer(ruta)
    # centro por mínimos cuadrados: el bounding box lo corre la línea de purga
    A = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]
    sol, *_ = np.linalg.lstsq(A, P[:, 0] ** 2 + P[:, 1] ** 2, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    R = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
    TH = np.arctan2(P[:, 1] - cy, P[:, 0] - cx) % (2 * math.pi)
    Z = P[:, 2]
    z1 = z1 if z1 is not None else Z.max()
    m = (Z >= z0) & (Z <= z1)
    R, TH, Z = R[m], TH[m], Z[m]

    # Una fila de píxeles por VUELTA de impresión. Más fino deja filas sin
    # ningún punto —la espiral sólo pasa una vez por altura— y el mapa sale
    # lleno de agujeros.
    if alto_px is None:
        vueltas = (Z.max() - Z.min()) / 0.31
        alto_px = max(50, int(vueltas))

    # -inf y no NaN: `np.maximum` contra NaN devuelve NaN y la grilla entera
    # sale vacía. Ya pasó dos veces en este proyecto.
    g = np.full((alto_px, ancho_px), -np.inf)
    gi = (TH / (2 * math.pi) * (ancho_px - 1)).astype(int)
    gj = ((Z - z0) / (z1 - z0) * (alto_px - 1)).astype(int)
    np.maximum.at(g, (gj, gi), R)
    g[np.isinf(g)] = np.nan
    # los huecos entre puntos se rellenan con el vecino de la izquierda
    for j in range(alto_px):
        fila = g[j]
        idx = np.where(~np.isnan(fila))[0]
        if len(idx) > 1:
            g[j] = np.interp(np.arange(ancho_px), idx, fila[idx])
    # filas que quedaron enteras vacías: se copian de la de abajo
    for j in range(alto_px):
        if np.all(np.isnan(g[j])) and j > 0:
            g[j] = g[j - 1]
    lo, hi = np.nanmin(g), np.nanmax(g)
    img = np.clip((g - lo) / max(hi - lo, 1e-9), 0, 1)
    return np.flipud(img), (lo, hi, z0, z1)


if __name__ == "__main__":
    ruta = sys.argv[1]
    z0 = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    z1 = float(sys.argv[3]) if len(sys.argv) > 3 else None
    img, (lo, hi, za, zb) = desenrollar(ruta, z0=z0, z1=z1)
    salida = ruta.rsplit(".", 1)[0] + ".png"
    Image.fromarray((img * 255).astype(np.uint8), "L").save(salida)
    print(f"{salida}")
    print(f"  desenrollado {2*math.pi*50.75:.0f} mm de circunferencia x "
          f"{zb-za:.0f} mm de alto (z {za:.0f}..{zb:.0f})")
    print(f"  radio {lo:.2f} .. {hi:.2f} mm  ->  claro = hilo, oscuro = pared")
