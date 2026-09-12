"""
¿El recorrido es UNA sola línea continua, o tiene saltos?

    python verificar_continuidad.py output/florero-kadzi/florero_kadzi.gcode --vuelo 1.3

En modo vaso la pieza entera es una espiral: la boquilla no levanta nunca, la Z
sube de a poquito en cada segmento y el ángulo avanza siempre para el mismo
lado. Cualquier cosa que rompa eso —un viaje sin extruir, una retracción, una
bajada de Z, un salto de XY que no corresponda al patrón— se ve en la pieza
como una costura, un hilo cruzado o un escalón, y no aparece en
`verificar_pieza.py`, que mide apoyo y sección pero no continuidad.

`verificar_capas.py` no sirve para esto: lee las marcas `; CHANGE_LAYER`, que
las emite el INJERTO y no el cuerpo (ver `.agents/MAPA.md`). Acá se mide el
recorrido crudo.

## Las dos trampas al medir esto, las dos ya pisadas

**La extrusión es RELATIVA.** El cuerpo emite `M83`, así que cada `E0.166` es
lo que se empuja en ESE segmento, no la posición del filamento. Comparando
`E` contra el del movimiento anterior —que es lo que haría cualquiera viniendo
de un g-code absoluto— salen 90 299 "retracciones" en una pieza que tiene dos.
Una retracción es un `E` NEGATIVO, y ya está.

**El cuerpo no empieza en la primera línea del archivo.** Adelante hay purga,
homing y un `G0` de posicionamiento; atrás, levantar el cabezal. Esos
movimientos son los MÁS GRANDES del archivo —la purga cruza 180 mm de cama— así
que descartarlos por tamaño escondería exactamente el defecto que se busca, y
descartar "los primeros N" depende de cuántas líneas tenga el preámbulo hoy.
Acá el cuerpo se define por lo que es: **la tirada más larga de movimientos que
extruyen seguidos**. Eso lo encuentra sola y sobrevive a que cambie el
preámbulo.

## Qué es un salto y qué no

El paso de XY entre dos puntos no es constante ni tiene por qué serlo: en una
pieza con relieve angular, el segmento donde la boquilla sale a hacer un turupe
mide lo que mide el turupe. Ese es el patrón, no un defecto. Por eso el corte
no es un número fijo sino el vuelo declarado (`--vuelo`) más el avance de un
segmento: por debajo de eso, un paso grande es la pieza haciendo su trabajo.
"""

import argparse
import math
import re
import sys

MOV = re.compile(r'([XYZEF])(-?\d*\.?\d+)')


def leer(ruta):
    """
    Los movimientos del archivo, como (x, y, z, e, linea), más las pausas.

    Una PAUSA es el trío que escribe la referencia: `G1 E-r` / `G4 P…` /
    `G1 E+r`, sin mover XY. No es un corte del trazo —la boquilla no se va a
    ningún lado— así que sus dos movimientos de filamento se marcan y se saltan
    en vez de partir el cuerpo en dos.

    Sin esto el verificador se apaga solo: cada pausa cortaba la tirada, así
    que sobre un archivo con 192 pausas el "cuerpo" pasaba de 27 506
    movimientos a 4 105 y todo lo demás se medía sobre ese pedazo. Daba verde
    porque había dejado de mirar.
    """
    x = y = z = 0.0
    puntos = []
    pausas = []
    for n, ln in enumerate(open(ruta), 1):
        if ln.startswith("G4"):
            m = re.search(r'P(\d+)', ln)
            pausas.append((int(m.group(1)) if m else 0, n))
            continue
        if not (ln.startswith("G0 ") or ln.startswith("G1 ")):
            continue
        d = dict(MOV.findall(ln))
        if not d:
            continue
        # movimiento de SOLO filamento, sin XYZ: es media pausa, no un punto
        if "E" in d and not ({"X", "Y", "Z"} & set(d)):
            puntos.append((x, y, z, None, n, True))
            continue
        x = float(d.get("X", x))
        y = float(d.get("Y", y))
        z = float(d.get("Z", z))
        # extrusión RELATIVA (M83): esto es lo que se empuja en este segmento.
        puntos.append((x, y, z, float(d["E"]) if "E" in d else None, n, False))
    if not puntos:
        sys.exit(f"{ruta}: no hay movimientos G0/G1")
    return puntos, pausas


def cuerpo_de(pts):
    """
    La tirada más larga de movimientos que extruyen hacia adelante.

    Los movimientos de una pausa (marcados por `leer`) no la cortan: la
    boquilla sigue donde estaba.
    """
    def sigue(p):
        return p[5] or (p[3] is not None and p[3] > 0)

    mejor = (0, 0)
    i = 0
    while i < len(pts):
        if not sigue(pts[i]):
            i += 1
            continue
        j = i
        while j < len(pts) and sigue(pts[j]):
            j += 1
        if j - i > mejor[1] - mejor[0]:
            mejor = (i, j)
        i = j
    return mejor


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("gcode")
    p.add_argument("--vuelo", type=float, default=0.0, metavar="MM",
                   help="cuánto sale el patrón en mm. El corte de 'salto' es "
                        "este vuelo más el avance de un segmento; con 0 se "
                        "deduce del percentil 99.9 de los pasos.")
    args = p.parse_args()

    pts, pausas = leer(args.gcode)
    a, b = cuerpo_de(pts)
    cuerpo = [p for p in pts[a:b] if not p[5]]
    if len(cuerpo) < 2:
        sys.exit(f"{args.gcode}: no se encontró un cuerpo continuo")
    print(f"{args.gcode}: {len(pts)} movimientos · el cuerpo son "
          f"{len(cuerpo)} seguidos, líneas {cuerpo[0][4]}..{cuerpo[-1][4]}")

    # Retracciones y viajes se cuentan sobre el ARCHIVO ENTERO: los de la purga
    # son legítimos, pero uno dentro del rango del cuerpo no lo sería, y por eso
    # se informa dónde cae cada uno. Las de las PAUSAS no cuentan: no cortan el
    # trazo, sólo sueltan la presión mientras la boquilla está parada.
    lineas_pausa = set()
    for _, n in pausas:
        lineas_pausa.update((n - 1, n + 1))
    retracciones = [(e, n) for _, _, _, e, n, _ in pts
                    if e is not None and e < 0 and n not in lineas_pausa]
    dentro = [n for _, n in retracciones if cuerpo[0][4] <= n <= cuerpo[-1][4]]

    saltos, bajadas, subida, viajes = [], [], [], []
    for i in range(1, len(cuerpo)):
        x0, y0, z0, _, _, _ = cuerpo[i - 1]
        x1, y1, z1, e1, ln, _ = cuerpo[i]
        d = math.hypot(x1 - x0, y1 - y0)
        saltos.append((d, ln))
        subida.append(z1 - z0)
        if z1 < z0 - 1e-9:
            bajadas.append((z1 - z0, ln))
        if (e1 is None or e1 <= 0) and d > 0.01:
            viajes.append((d, ln))

    ds = sorted(d for d, _ in saltos)
    p50 = ds[len(ds) // 2]
    p999 = ds[min(len(ds) - 1, int(len(ds) * 0.999))]
    corte = (args.vuelo + p50) if args.vuelo > 0 else p999 * 1.5
    grandes = sorted(((d, ln) for d, ln in saltos if d > corte), reverse=True)

    print("\n1. CONTINUIDAD DEL TRAZO")
    if pausas:
        ms = sum(p for p, _ in pausas)
        print(f"   pausas deliberadas: {len(pausas)} · {ms / 1000:.1f} s en total "
              f"({ms / 1000 / 60:.1f} min de reloj). No cortan el trazo.")
    print(f"   viajes sin extruir dentro del cuerpo: {len(viajes)}")
    print(f"   retracciones en el archivo: {len(retracciones)}"
          f" · dentro del cuerpo: {len(dentro)}")

    print("\n2. LA Z SÓLO SUBE")
    print(f"   bajadas de Z: {len(bajadas)}")
    sub = sorted(subida)
    print(f"   subida por movimiento: min {sub[0]:.5f} · mediana "
          f"{sub[len(sub) // 2]:.5f} · max {sub[-1]:.5f} mm")

    print("\n3. PASO DE XY  (el patrón mueve la boquilla; un salto, no)")
    print(f"   mediana {p50:.3f} · p99.9 {p999:.3f} · max {ds[-1]:.3f} mm")
    print(f"   corte de salto: {corte:.3f} mm"
          + (f"  (vuelo {args.vuelo:g} + paso {p50:.3f})" if args.vuelo > 0
             else "  (p99.9 x 1.5, deducido)"))
    print(f"   por encima del corte: {len(grandes)}")
    for d, ln in grandes[:6]:
        print(f"        {d:7.3f} mm  en la línea {ln}")

    malo = bool(viajes or dentro or bajadas or grandes)
    print("\n-> " + ("HAY SALTOS" if malo else
                     "TRAZO CONTINUO: sin viajes ni retracciones en el cuerpo, "
                     "la Z sólo sube y ningún paso de XY excede el patrón"))
    return 1 if malo else 0


if __name__ == "__main__":
    sys.exit(main())
