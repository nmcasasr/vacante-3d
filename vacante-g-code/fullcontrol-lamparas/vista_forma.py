#!/usr/bin/env python3
"""
Render sombreado de una silueta + deformación, ANTES de generar g-code.

`vista_gcode.py` dibuja el recorrido ya emitido: alambre, y con 350 vueltas se
convierte en una mancha. Para decidir una FORMA hace falta ver la superficie
iluminada, porque lo que se juzga —dónde pega la luz, si el lóbulo se lee, si
los nervios serpentean— vive en la normal, no en el contorno.

Es el mismo campo `(ángulo, t) -> mm` que consume `pasos_pantalla_glitch`, así
que lo que se ve acá es lo que se imprime: no hay una segunda descripción de la
pieza que se pueda desincronizar.

    python3 vista_forma.py                              # todas las variantes
    python3 vista_forma.py --variante melt_a --salida a.png
    python3 vista_forma.py --variante melt_a --barrido lobulos=1.5,2,3 \
                           --barrido amplitud=8,12,16
"""
import argparse
import math
import sys

import numpy as np
from PIL import Image

TAU = 2 * math.pi


def malla(silueta, deformacion, altura, n_a=1500, n_t=1300):
    """Puntos de la superficie y su normal, vectorizado."""
    a = np.linspace(0, TAU, n_a, endpoint=False)
    t = np.linspace(0, 1, n_t)
    A, T = np.meshgrid(a, t)
    R = silueta(T) + deformacion(A, T)
    return np.stack([R * np.cos(A), R * np.sin(A), T * altura], axis=-1)


def _normales(P):
    """Normal por diferencias sobre la malla; se cierra en el ángulo."""
    du = np.roll(P, -1, axis=1) - np.roll(P, 1, axis=1)      # a lo largo del ángulo
    dv = np.empty_like(P)
    dv[1:-1] = P[2:] - P[:-2]                                 # a lo largo de la altura
    dv[0], dv[-1] = P[1] - P[0], P[-1] - P[-2]
    n = np.cross(du, dv)
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
    # que apunte hacia afuera del eje
    fuera = (n[..., 0] * P[..., 0] + n[..., 1] * P[..., 1]) < 0
    n[fuera] *= -1
    return n


def render(P, W=520, H=760, azimut=0.0, elevacion=12.0, color=(228, 96, 176),
           fondo=(250, 249, 247)):
    """
    Proyección ortográfica con z-buffer por dispersión ordenada.

    El z-buffer se hace ordenando los puntos de lejos a cerca y escribiendo en
    ese orden: el último que cae en un píxel es el más cercano. Es exacto y son
    dos líneas de numpy; un bucle sobre 900 000 puntos no termina nunca.
    """
    N = _normales(P)
    ca, sa = math.cos(math.radians(azimut)), math.sin(math.radians(azimut))
    ce, se = math.cos(math.radians(elevacion)), math.sin(math.radians(elevacion))
    # cámara: gira en azimut y se levanta `elevacion` grados sobre el horizonte
    ejeu = np.array([-sa, ca, 0.0])
    ejev = np.array([-ca * se, -sa * se, ce])
    ejew = np.array([ca * ce, sa * ce, se])        # hacia la cámara

    p = P.reshape(-1, 3)
    n = N.reshape(-1, 3)
    u, v, w = p @ ejeu, p @ ejev, p @ ejew

    m = 0.06
    esc = min(W * (1 - 2 * m) / max(np.ptp(u), 1e-6), H * (1 - 2 * m) / max(np.ptp(v), 1e-6))
    px = ((u - u.mean()) * esc + W / 2).astype(np.int32)
    py = (H / 2 - (v - (v.min() + v.max()) / 2) * esc).astype(np.int32)

    luz = np.array([-0.35, 0.55, 0.75]); luz /= np.linalg.norm(luz)
    relleno = np.array([0.6, -0.5, 0.2]); relleno /= np.linalg.norm(relleno)
    difusa = np.clip(n @ luz, 0, 1)
    rebote = np.clip(n @ relleno, 0, 1)
    # especular suave: es lo que hace legible el nervio fino
    h = luz + ejew; h /= np.linalg.norm(h)
    brillo = np.clip(n @ h, 0, 1) ** 28
    k = (0.30 + 0.62 * difusa + 0.16 * rebote)[:, None] * np.array(color) + 235 * brillo[:, None]

    img = np.tile(np.array(fondo, np.float64), (H, W, 1))
    dentro = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    orden = np.argsort(w[dentro])                  # de lejos a cerca
    idx = np.flatnonzero(dentro)[orden]
    img[py[idx], px[idx]] = np.clip(k[idx], 0, 255)
    return Image.fromarray(img.astype(np.uint8))


def tira(silueta, deformacion, altura, azimuts=(0, 55, 110), **kw):
    """Varias vistas del mismo objeto, lado a lado. Una sola no alcanza:
    estas formas son asimétricas a propósito y el perfil cambia con el ángulo."""
    P = malla(silueta, deformacion, altura)
    ims = [render(P, azimut=az, **kw) for az in azimuts]
    out = Image.new("RGB", (sum(i.width for i in ims), ims[0].height), (250, 249, 247))
    x = 0
    for i in ims:
        out.paste(i, (x, 0)); x += i.width
    return out


def contacto(casos, ancho=340, alto=520, azimut=25.0, cols=None):
    """
    Hoja de contacto: la misma forma con un parámetro barrido, lado a lado.

    Existe porque una forma no se juzga sola. `amplitud=12` no quiere decir
    nada; lo que se ve es que 8 se queda corta y 16 se pasa, y eso solo aparece
    con las tres al lado. Cada celda lleva su etiqueta impresa encima: sin ella
    ya pasó —está anotado en ESTADO.md— reportar como distintas tres corridas
    que eran el mismo archivo.

    `casos` es una lista de (etiqueta, silueta, deformacion, altura).
    """
    from PIL import ImageDraw
    cols = cols or len(casos)
    filas = (len(casos) + cols - 1) // cols
    hoja = Image.new("RGB", (cols * ancho, filas * (alto + 18)), (250, 249, 247))
    dib = ImageDraw.Draw(hoja)
    for i, (etiqueta, sil, deform, altura) in enumerate(casos):
        im = render(malla(sil, deform, altura), W=ancho, H=alto, azimut=azimut)
        x, y = (i % cols) * ancho, (i // cols) * (alto + 18)
        hoja.paste(im, (x, y))
        dib.text((x + 8, y + alto + 3), etiqueta, fill=(40, 40, 45))
    return hoja


if __name__ == "__main__":
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser()
    ap.add_argument("--variante", default=None)
    ap.add_argument("--barrido", action="append", default=[], metavar="clave=v1,v2",
                    help="barre un parámetro de la deformación (hasta dos veces)")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()
    from gen_melt import VARIANTES, construir

    if args.barrido:
        base = args.variante or next(iter(VARIANTES))
        ejes = []
        for kv in args.barrido:
            k, _, vs = kv.partition("=")
            ejes.append([(k, float(v)) for v in vs.split(",")])
        if len(ejes) == 1:
            ejes.append([()])
        casos = []
        for a in ejes[0]:
            for b in ejes[1]:
                cambios = dict([a] + ([b] if b else []))
                etiqueta = " ".join(f"{k}={v:g}" for k, v in cambios.items())
                casos.append((etiqueta, *construir(base, **cambios)))
        ruta = args.salida or f"output/melt/barrido_{base}.png"
        contacto(casos, cols=len(ejes[1])).save(ruta)
        print("barrido:", ruta)
    else:
        for nom in ([args.variante] if args.variante else list(VARIANTES)):
            sil, deform, altura = construir(nom)
            ruta = args.salida or f"output/melt/vista_{nom}.png"
            tira(sil, deform, altura).save(ruta)
            print("vista:", ruta)
