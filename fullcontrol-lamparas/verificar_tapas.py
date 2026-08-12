#!/usr/bin/env python3
"""
Superficie horizontal destapada: dónde se ve hacia adentro de la pieza.

Una espiral que salta hacia afuera entre dos vueltas deja un anillo horizontal
sin nada encima. No es falta de apoyo —los dos bordes están perfectamente
sostenidos— y por eso ninguno de los otros criterios lo ve. Es un agujero.

**Cómo se mide, y por qué así.** Se corta la pieza en rebanadas de un cordón de
alto y en sectores angulares. Dentro de cada celda se ordenan los radios que
tienen material: si entre dos consecutivos hay más de un cordón de hueco, ese
anillo está destapado, y su área es `hueco x radio x delta_angulo`.

Distingue las dos topologías, que es lo que hace falta:

  - Una espiral que salta: la celda tiene el radio viejo y el nuevo, y entre
    ellos nada. Hueco detectado.
  - Pasadas planas de relleno: la celda tiene todos los radios intermedios
    separados menos de un cordón. Sin hueco.

Intentos anteriores midieron la separación entre vueltas consecutivas ordenadas
por z. Eso NO es lo mismo y da resultados al revés: en una zona rellena con
pasadas planas hay muchos puntos a la misma altura y el orden por z los mezcla,
así que la pieza rellena medía PEOR que la que tiene el agujero.

    python3 verificar_tapas.py output/glitch8.gcode [--ancho 1.8] [--alto 0.4]
"""

import argparse
import collections
import math
import sys

from verificar_pieza import leer


def medir(segs, ancho, alto, grados=1.0, centro=(128.0, 128.0)):
    cx, cy = centro
    celdas = collections.defaultdict(list)
    z_base = min(min(s[2], s[5]) for s in segs)
    # Se muestrea A LO LARGO del segmento, no por su punto medio.
    #
    # Un segmento radial que cruza de un sector al otro mide hasta 33 mm: por su
    # punto medio aporta UN radio en el centro, y el medidor ve un hueco de 33 mm
    # donde en realidad hay una línea de material uniendo los dos lados. Con el
    # punto medio esta pieza daba 890 anillos destapados; casi todos eran eso.
    paso_m = min(alto, ancho) / 2
    for s in segs:
        largo = math.dist(s[:3], s[3:6])
        n = max(1, int(math.ceil(largo / paso_m)))
        for q in range(n):
            f = (q + 0.5) / n
            mx = s[0] + (s[3] - s[0]) * f
            my = s[1] + (s[4] - s[1]) * f
            mz = s[2] + (s[5] - s[2]) * f
            if mz < z_base + alto:      # el piso no cuenta: apoya en la cama
                continue
            a = math.degrees(math.atan2(my - cy, mx - cx)) % 360
            celdas[(int(mz / alto), int(a / grados))].append(math.hypot(mx - cx, my - cy))

    huecos = []
    for (kz, ka), radios in celdas.items():
        radios.sort()
        for r1, r2 in zip(radios, radios[1:]):
            if r2 - r1 > ancho:
                huecos.append((r2 - r1, kz * alto, ka * grados, (r1 + r2) / 2))
    area = sum(h * rm * math.radians(grados) for h, _, _, rm in huecos)
    return huecos, area, len(celdas)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gcode")
    ap.add_argument("--ancho", type=float, default=1.8)
    ap.add_argument("--alto", type=float, default=0.4)
    a = ap.parse_args()
    segs = leer(a.gcode, a.ancho)
    if not segs:
        print(f"{a.gcode}: sin segmentos extruidos", file=sys.stderr)
        return 1
    huecos, area, celdas = medir(segs, a.ancho, a.alto)
    print(f"{len(segs)} segmentos · {celdas} celdas (altura de cordón x 1°)")
    print(f"anillos destapados: {len(huecos)}  ·  {100 * len(huecos) / max(celdas, 1):.2f} % "
          f"de las celdas  ·  {area / 100:.1f} cm² de superficie a la vista")
    if huecos:
        huecos.sort(reverse=True)
        print(f"   el peor: {huecos[0][0]:.1f} mm de hueco en z {huecos[0][1]:.1f}, "
              f"ángulo {huecos[0][2]:.0f}°")
        h = collections.Counter(round(v[1] / 10) * 10 for v in huecos)
        print("   por franja de altura: "
              + " · ".join(f"z{k}:{v}" for k, v in sorted(h.items())[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
