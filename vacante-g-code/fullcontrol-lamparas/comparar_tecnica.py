#!/usr/bin/env python3
"""
Compara la TÉCNICA de impresión de varios g-code sobre los mismos ejes.

    python3 comparar_tecnica.py A.gcode B.gcode ...
    python3 comparar_tecnica.py --z 0:28 "Squeezy Fidget Toy.gcode"

Existe porque "¿usamos la misma técnica que la referencia?" no se contesta
mirando los parámetros con los que se generó cada pieza: las referencias no
tienen parámetros, son g-code ajeno. Lo único común es el archivo emitido, así
que todo lo de acá se deriva de los movimientos.

## Qué mide, y por qué esas cosas

`cordón` — el ancho y el alto que se le pide a la boquilla. El alto sale por el
método de `MAPA.md`: la distancia vertical al material que está JUSTO DEBAJO
(dh < 0.2 mm), y el ancho es `área ÷ alto`. Sin suponer nada del generador.

`caudal` — `área × velocidad`, en mm3/s. Es el techo real de la impresora, y es
lo que decide si un tramo sale liso o con grumos. El piso también importa: por
debajo de ~3.8 la boquilla babea (ver `--caudal-minimo` en el CLI).

`s/vuelta` — cuánto tarda el cabezal en volver al mismo ángulo. Es el tiempo que
tiene el cordón para cuajar antes de que le apoyen el siguiente encima, y es el
número que la referencia fija en ~25 s. NO es lo mismo que la velocidad: una
pieza angosta a la misma velocidad da la vuelta mucho antes.

`separación` — distancia entre dos vueltas SOBRE LA SUPERFICIE, medida al mismo
ángulo. Es la que gobierna la extrusión y el solape (ver las tres alturas de
`MAPA.md`), y en una cúpula no coincide con lo que sube la vuelta.

## La trampa de Squeezy

Su tramo del medio (z 28..70) es una celosía cuyos hilos cruzan en el aire por
diseño, y ahí el ángulo no avanza de forma monótona: cualquier detección de
vueltas sobre la pieza entera da basura. Hay que medirla por sus CÚPULAS, con
`--z 0:28` y `--z 70:97`.
"""

import argparse
import collections
import math
import re
import statistics
import sys

AREA_FILAMENTO = math.pi * 1.75 ** 2 / 4     # mm2, filamento de 1.75
MARCADOR = "FIN DEL START GCODE"


def leer(ruta):
    """
    Los segmentos extruidos, más los comandos de máquina que interesan.

    Devuelve (segmentos, eventos). Cada segmento es
    (x0,y0,z0, x1,y1,z1, area, mm_s) y cada evento (z, texto).

    El start-gcode se saltea cuando el archivo trae el marcador: sus líneas de
    purga son un cordón de 20 mm2 que ensucia todas las medianas. Un g-code
    ajeno no lo tiene, y ahí se descartan los movimientos por debajo de la
    primera capa de la pieza.
    """
    segs, eventos = [], []
    x = y = z = 0.0
    f_mm_min = 1200.0
    relativa = True
    cuerpo = MARCADOR not in open(ruta, errors="ignore").read()
    for linea in open(ruta, errors="ignore"):
        if MARCADOR in linea:
            cuerpo = True
            continue
        s = linea.strip()
        if s.startswith("M83"):
            relativa = True
        elif s.startswith("M82"):
            relativa = False
        elif s.startswith(("M104", "M109", "M106", "M107", "G4")):
            eventos.append((z, s.split(";")[0].strip()))
        if not cuerpo or not s.startswith(("G1", "G0")):
            continue
        campos = dict(re.findall(r"([XYZEF])(-?\d+\.?\d*)", s.split(";")[0]))
        nx = float(campos.get("X", x))
        ny = float(campos.get("Y", y))
        nz = float(campos.get("Z", z))
        if "F" in campos:
            f_mm_min = float(campos["F"])
        e = float(campos.get("E", 0.0))
        largo = math.dist((x, y, z), (nx, ny, nz))
        if e > 0 and largo > 1e-9 and relativa:
            segs.append((x, y, z, nx, ny, nz,
                         e * AREA_FILAMENTO / largo, f_mm_min / 60.0))
        x, y, z = nx, ny, nz
    return segs, eventos


def centro(segs):
    """
    El eje, por caja envolvente de la MITAD DE ABAJO.

    `MAPA.md` avisa que la caja envolvente sólo da el eje si la pieza llega a su
    radio máximo en todas las direcciones. Acá alcanza igual porque las tres
    piezas son de revolución en su parte ancha, y se toma la mitad de abajo para
    que un ápice o un ala no la corran.
    """
    zs = [s[2] for s in segs]
    corte = (min(zs) + max(zs)) / 2
    bajos = [s for s in segs if s[2] <= corte] or segs
    xs = [s[0] for s in bajos] + [s[3] for s in bajos]
    ys = [s[1] for s in bajos] + [s[4] for s in bajos]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def alto_del_cordon(segs, cx, cy, muestras=4000):
    """
    El alto del cordón: distancia vertical al material justo debajo.

    "Justo debajo" es al mismo (x,y) con menos de 0.2 mm de corrimiento
    horizontal, que es lo que distingue apilar de poner al lado. Los segmentos
    se indexan por celdas de 1 mm para no comparar todos contra todos.
    """
    rejilla = collections.defaultdict(list)
    for i, s in enumerate(segs):
        mx, my, mz = (s[0] + s[3]) / 2, (s[1] + s[4]) / 2, (s[2] + s[5]) / 2
        rejilla[(int(mx), int(my))].append((mz, i))
    alturas = []
    paso = max(1, len(segs) // muestras)
    for i in range(0, len(segs), paso):
        s = segs[i]
        mx, my, mz = (s[0] + s[3]) / 2, (s[1] + s[4]) / 2, (s[2] + s[5]) / 2
        mejor = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for oz, j in rejilla.get((int(mx) + dx, int(my) + dy), ()):
                    if j == i or oz >= mz - 1e-6:
                        continue
                    o = segs[j]
                    ox, oy = (o[0] + o[3]) / 2, (o[1] + o[4]) / 2
                    if math.hypot(ox - mx, oy - my) > 0.2:
                        continue
                    if mejor is None or oz > mejor:
                        mejor = oz
        if mejor is not None and 0 < mz - mejor < 2.0:
            alturas.append(mz - mejor)
    return alturas


def vueltas(segs, cx, cy):
    """
    Tiempo y separación de cada vuelta, siguiendo el ángulo acumulado.

    Devuelve (segundos_por_vuelta, separaciones). La separación se mide entre
    dos pasadas por el MISMO ángulo, o sea el corrimiento real de una vuelta a
    la siguiente sobre la superficie — no lo que sube en Z.
    """
    acum = 0.0
    ang_prev = None
    t_vuelta = 0.0
    tiempos = []
    # (angulo_acumulado, radio, z) para cruzar cada vuelta con la anterior
    huella = []
    for x0, y0, z0, x1, y1, z1, area, v in segs:
        mx, my, mz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
        a = math.atan2(my - cy, mx - cx)
        if ang_prev is not None:
            d = a - ang_prev
            while d > math.pi:
                d -= 2 * math.pi
            while d < -math.pi:
                d += 2 * math.pi
            acum += d
        ang_prev = a
        largo = math.dist((x0, y0, z0), (x1, y1, z1))
        t_vuelta += largo / max(v, 1e-6)
        huella.append((acum, math.hypot(mx - cx, my - cy), mz))
        if abs(acum) >= 2 * math.pi:
            tiempos.append(t_vuelta)
            t_vuelta = 0.0
            acum -= math.copysign(2 * math.pi, acum)
    # separación: por cada punto, el punto de la vuelta anterior al mismo ángulo
    seps = []
    por_angulo = collections.defaultdict(list)
    total = 0.0
    ang_prev = None
    for a, r, z in huella:
        clave = round(a % (2 * math.pi), 2)
        por_angulo[clave].append((r, z))
    for clave, pasadas in por_angulo.items():
        for i in range(1, len(pasadas)):
            r0, z0 = pasadas[i - 1]
            r1, z1 = pasadas[i]
            d = math.hypot(r1 - r0, z1 - z0)
            if 0 < d < 3.0:
                seps.append(d)
    return tiempos, seps


def p(vals, q):
    if not vals:
        return float("nan")
    v = sorted(vals)
    return v[min(len(v) - 1, int(q * len(v)))]


def informe(ruta, franja=None):
    segs, eventos = leer(ruta)
    if franja:
        segs = [s for s in segs if franja[0] <= (s[2] + s[5]) / 2 <= franja[1]]
    if not segs:
        print(f"{ruta}: sin segmentos extruidos en la franja")
        return
    cx, cy = centro(segs)
    zs = [s[2] for s in segs] + [s[5] for s in segs]
    rs = [math.hypot((s[0] + s[3]) / 2 - cx, (s[1] + s[4]) / 2 - cy) for s in segs]
    areas = [s[6] for s in segs]
    vels = [s[7] for s in segs]
    caudales = [s[6] * s[7] for s in segs]
    alturas = alto_del_cordon(segs, cx, cy)
    tiempos, seps = vueltas(segs, cx, cy)
    h = statistics.median(alturas) if alturas else float("nan")
    w = statistics.median(areas) / h if alturas else float("nan")

    nombre = ruta.split("/")[-1]
    print(f"\n=== {nombre}" + (f"  (z {franja[0]}..{franja[1]})" if franja else "") + " ===")
    print(f"  pieza        alto {max(zs)-min(zs):6.1f} mm · Ø max {2*max(rs):6.1f} mm"
          f" · {len(segs)} segmentos")
    print(f"  cordón       {w:.2f} x {h:.3f} mm   (área mediana {statistics.median(areas):.3f} mm²,"
          f" p10 {p(areas,.1):.3f} p90 {p(areas,.9):.3f})")
    print(f"  velocidad    {statistics.median(vels):5.1f} mm/s   (p10 {p(vels,.1):.1f}"
          f" p90 {p(vels,.9):.1f}, tope {max(vels):.1f})")
    print(f"  caudal       {statistics.median(caudales):5.2f} mm³/s (p10 {p(caudales,.1):.2f}"
          f" p90 {p(caudales,.9):.2f}, tope {max(caudales):.2f})")
    if tiempos:
        print(f"  s/vuelta     {statistics.median(tiempos):5.1f} s      (p10 {p(tiempos,.1):.1f}"
              f" p90 {p(tiempos,.9):.1f}) · {len(tiempos)} vueltas")
    if seps:
        print(f"  separación   {statistics.median(seps):5.3f} mm    (p90 {p(seps,.9):.3f},"
              f" peor {max(seps):.3f}) · solape {100*(w-p(seps,.9))/w:.0f}% sobre el ancho")
    temps = [e for e in eventos if e[1].startswith(("M104", "M109"))]
    fans = [e for e in eventos if e[1].startswith(("M106", "M107"))]
    esperas = [e for e in eventos if e[1].startswith("G4")]
    if temps:
        print("  temperatura  " + " · ".join(f"z{z:.1f} {t}" for z, t in temps[:6]))
    if fans:
        vistos, txt = set(), []
        for z, t in fans:
            if t not in vistos or len(txt) < 6:
                vistos.add(t)
                txt.append(f"z{z:.1f} {t}")
        print("  ventilador   " + " · ".join(txt[:8]))
    print(f"  esperas G4   {len(esperas)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gcodes", nargs="+")
    ap.add_argument("--z", action="append", default=[], metavar="Z0:Z1",
                    help="medir solo esa franja de altura, repetible. Squeezy hay que "
                         "medirlo por sus cúpulas: --z 0:28 --z 70:97")
    args = ap.parse_args()
    franjas = [tuple(float(v) for v in f.split(":")) for f in args.z] or [None]
    for g in args.gcodes:
        for f in franjas:
            informe(g, f)


if __name__ == "__main__":
    main()
