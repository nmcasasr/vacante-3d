#!/usr/bin/env python3
"""
¿Cuánto se tumba la pared, vuelta por vuelta, y dónde?

    python verificar_tumbado.py output/gusano-universal/modulo_D244_183mm.gcode
    python verificar_tumbado.py output/hongo/hongo_latest.gcode   # la referencia

Existe porque `verificar_pieza.py` no lo ve. Con `--separacion marcha` cada
vuelta se corre 0.8 mm SOBRE LA SUPERFICIE y pisa la anterior de costado, así
que una pared casi horizontal sale "0.00 % sin apoyo": el Ø244 que cierra
entero hasta un cuello de Ø38 da IMPRIMIBLE con 84° de voladizo. Puede que lo
sea, pero ese veredicto no distingue 84° de 60°, y para elegir entre las dos
hace falta el número.

Lo que mide: el radio medio y la altura media de cada vuelta (una vuelta = 2π
de ángulo acumulado alrededor del centro de la pieza), y entre dos vueltas
seguidas el ángulo de la pared desde la vertical, `atan(Δr/Δz)`. Informa el
peor, y cuánto RADIO recorre la pared más tumbada que 76° (la cintura de
Squeezy) y que 80°, separado en:

  - "afuera": la pared se abre al subir, o sea la panza de abajo de un lóbulo;
  - "adentro": la pared se cierra al subir, el hombro o la cúpula de arriba.

Las vueltas PLANAS —las pasadas del piso, que no suben nada dentro de la
vuelta— se descartan: son horizontales a propósito y están apoyadas en la cama.
Sin ese filtro el gusanito y el hongo daban "175°" en el piso. La primera vuelta
también se descarta: incluye el acercamiento desde la purga.

Para comparar contra algo impreso: `hongo_latest.gcode` (impreso y bueno)
llega a 84.0°, con 26 mm de radio a más de 76° adentro (la cúpula) y 7 mm
afuera (z 0.9..3.8, pegado a la cama).
"""
import argparse
import math
import re
import sys

MOV = re.compile(r'([XYZEF])(-?\d*\.?\d+)')


def cuerpo(ruta):
    """La tirada más larga de movimientos que extruyen seguidos (como verificar_continuidad)."""
    x = y = z = 0.0
    pts = []
    for ln in open(ruta):
        if not ln.startswith("G1"):
            continue
        d = dict(MOV.findall(ln.split(";")[0]))
        x, y, z = float(d.get("X", x)), float(d.get("Y", y)), float(d.get("Z", z))
        pts.append((x, y, z, float(d["E"]) if "E" in d else 0.0))
    mejor, i = (0, 0), 0
    while i < len(pts):
        if pts[i][3] <= 0:
            i += 1
            continue
        j = i
        while j < len(pts) and pts[j][3] > 0:
            j += 1
        if j - i > mejor[1] - mejor[0]:
            mejor = (i, j)
        i = j
    return pts[mejor[0]:mejor[1]]


def vueltas(pts):
    """(radio medio, z medio, cuánto sube dentro de la vuelta) de cada vuelta."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    acc, prev, cur, out = 0.0, None, [], []
    for x, y, z, _ in pts:
        a = math.atan2(y - cy, x - cx)
        if prev is not None:
            da = (a - prev + math.pi) % (2 * math.pi) - math.pi
            acc += abs(da)
        prev = a
        cur.append((math.hypot(x - cx, y - cy), z))
        if acc >= 2 * math.pi:
            zs = [c[1] for c in cur]
            out.append((sum(c[0] for c in cur) / len(cur), sum(zs) / len(zs), max(zs) - min(zs)))
            cur, acc = [], acc - 2 * math.pi
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gcode", nargs="+")
    a = ap.parse_args()
    for ruta in a.gcode:
        v = vueltas(cuerpo(ruta))
        tramos = []
        for (r0, z0, s0), (r1, z1, s1) in zip(v[1:], v[2:]):
            if s0 < 1e-4 or s1 < 1e-4:
                continue                       # pasada plana de piso
            ang = math.degrees(math.atan2(abs(r1 - r0), z1 - z0))
            tramos.append((ang, r1 - r0, r0, z0))
        if not tramos:
            sys.exit(f"{ruta}: no hay vueltas de pared")
        peor = max(tramos)
        print(f"{ruta}: {len(v)} vueltas")
        print(f"   peor {peor[0]:.1f}° desde la vertical (r {peor[2]:.1f}, z {peor[3]:.1f})")
        for umbral in (76, 80):
            for nombre, signo in (("afuera", 1), ("adentro", -1)):
                sel = [t for t in tramos if t[0] > umbral and t[1] * signo > 0]
                if not sel:
                    print(f"   > {umbral}° {nombre:7s}: nada")
                    continue
                radio = sum(abs(t[1]) for t in sel)
                print(f"   > {umbral}° {nombre:7s}: {radio:5.1f} mm de radio en {len(sel)} vueltas"
                      f" · z {min(t[3] for t in sel):.1f}..{max(t[3] for t in sel):.1f}"
                      f" · r {min(t[2] for t in sel):.1f}..{max(t[2] for t in sel):.1f}")


if __name__ == "__main__":
    main()
