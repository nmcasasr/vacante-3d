#!/usr/bin/env python3
"""
Render sólido de un g-code de rosca, tipo vista de laminador.

`ver_rosca.py` desenrolla el cilindro a un mapa plano: sirve para verificar que
el dibujo salió donde se pidió, pero no para juzgar cómo se va a ver la pieza.
Un relieve de 2 mm sobre un tubo de 100 se lee por su SOMBRA, y eso un mapa de
grises por radio no lo muestra.

Acá se reconstruye la superficie —r en función de (ángulo, altura)— se le saca
la normal y se sombrea con una luz. No es un trazador de rayos: es proyección
ortográfica con z-buffer, que para un cilindro alcanza y sobra.

    python ver_solido.py output/rosca/caritas_v2400.gcode
    python ver_solido.py output/rosca/caritas_v2400.gcode 40 160   # franja de z

El PNG queda al lado del g-code, con sufijo `_solido`.
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


def superficie(ruta, z0, z1, n_th=1440):
    """Grilla r[iz, ith] de la superficie, con los huecos rellenados."""
    P = leer(ruta)
    A = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]
    sol, *_ = np.linalg.lstsq(A, P[:, 0] ** 2 + P[:, 1] ** 2, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    R = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
    TH = np.arctan2(P[:, 1] - cy, P[:, 0] - cx) % (2 * math.pi)
    Z = P[:, 2]
    m = (Z >= z0) & (Z <= z1) & (R < R.max() * 0.6)   # fuera la línea de purga
    R, TH, Z = R[m], TH[m], Z[m]

    # una fila por vuelta de impresión: más fino deja filas sin ningún punto
    n_z = max(60, int((z1 - z0) / 0.31))
    g = np.full((n_z, n_th), -np.inf)          # -inf y no NaN: max contra NaN da NaN
    gi = np.clip((TH / (2 * math.pi) * n_th).astype(int), 0, n_th - 1)
    gj = np.clip(((Z - z0) / (z1 - z0) * (n_z - 1)).astype(int), 0, n_z - 1)
    np.maximum.at(g, (gj, gi), R)
    g[np.isinf(g)] = np.nan
    for j in range(n_z):                        # rellenar a lo ancho
        fila = g[j]
        idx = np.where(~np.isnan(fila))[0]
        if len(idx) > 1:
            g[j] = np.interp(np.arange(n_th), idx, fila[idx], period=n_th)
    for j in range(n_z):                        # filas enteras vacías
        if np.all(np.isnan(g[j])) and j > 0:
            g[j] = g[j - 1]
    return g, z0, z1


def render(ruta, z0=5.0, z1=None, ancho=760, luz=(-0.55, 0.62, 0.56)):
    P = leer(ruta)
    z1 = z1 if z1 is not None else P[:, 2].max() - 1
    g, z0, z1 = superficie(ruta, z0, z1)
    n_z, n_th = g.shape

    th = np.linspace(0, 2 * math.pi, n_th, endpoint=False)[None, :]
    zz = np.linspace(z0, z1, n_z)[:, None]
    dz = (z1 - z0) / (n_z - 1)
    dth = 2 * math.pi / n_th

    # normal de una superficie r(th, z) en cilíndricas:
    #   n = (r, -dr/dth, -r*dr/dz) en la base (radial, tangencial, axial)
    dr_th = (np.roll(g, -1, axis=1) - np.roll(g, 1, axis=1)) / (2 * dth)
    dr_z = np.gradient(g, dz, axis=0)
    nr, nt, nz = g, -dr_th, -g * dr_z
    largo = np.sqrt(nr ** 2 + nt ** 2 + nz ** 2)
    nr, nt, nz = nr / largo, nt / largo, nz / largo

    c, s = np.cos(th), np.sin(th)
    NX = nr * c - nt * s
    NY = nr * s + nt * c
    NZ = np.broadcast_to(nz, g.shape)

    X = g * c
    Y = g * s                                   # profundidad: +Y hacia la cámara
    Z3 = np.broadcast_to(zz, g.shape)

    lx, ly, lz = luz
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / n, ly / n, lz / n
    lam = np.clip(NX * lx + NY * ly + NZ * lz, 0, 1)
    # La luz va del MISMO lado que la cámara (ly > 0), o la cara que se ve
    # queda en sombra y la pieza sale negra. El ambiente evita que el lado
    # oscuro sea negro puro, y la potencia <1 levanta los medios tonos, que es
    # donde vive el relieve de 2 mm que queremos juzgar.
    color = 0.14 + 0.86 * lam ** 0.65

    rmax = np.nanmax(g)
    esc = (ancho * 0.44) / rmax
    alto = int((z1 - z0) * esc + ancho * 0.10)
    px = (X * esc + ancho / 2).astype(int)
    py = (alto - (Z3 - z0) * esc - ancho * 0.05).astype(int)
    ok = (px >= 0) & (px < ancho) & (py >= 0) & (py < alto)

    img = np.zeros((alto, ancho))
    prof = np.full((alto, ancho), -1e9)
    # z-buffer: gana el punto más cercano a la cámara (mayor Y)
    orden = np.argsort(Y[ok].ravel())
    pxo, pyo = px[ok].ravel()[orden], py[ok].ravel()[orden]
    co, yo = color[ok].ravel()[orden], Y[ok].ravel()[orden]
    # El splat se dimensiona con la relación entre píxeles y filas de datos.
    # Con un 2x2 fijo, una pieza alta deja filas enteras de la imagen sin
    # escribir —la grilla tiene una fila por vuelta y la imagen muchas más— y
    # salen rayas negras horizontales.
    sy = max(2, int(math.ceil(alto / n_z)) + 1)
    sx = max(2, int(math.ceil(ancho / n_th * 2)) + 1)
    for d in range(sx):
        for e in range(sy):
            xi, yi = np.clip(pxo + d, 0, ancho - 1), np.clip(pyo + e, 0, alto - 1)
            mejor = yo > prof[yi, xi]
            prof[yi[mejor], xi[mejor]] = yo[mejor]
            img[yi[mejor], xi[mejor]] = co[mejor]
    return img


if __name__ == "__main__":
    ruta = sys.argv[1]
    z0 = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    z1 = float(sys.argv[3]) if len(sys.argv) > 3 else None
    img = render(ruta, z0, z1)
    salida = ruta.rsplit(".", 1)[0] + "_solido.png"
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "L").save(salida)
    print(salida)
