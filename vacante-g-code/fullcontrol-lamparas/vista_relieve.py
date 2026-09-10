#!/usr/bin/env python3
"""
La pieza DESENROLLADA, para ver el dibujo antes de imprimirlo.

Existe porque `vista_gcode.py` no sirve para una pieza texturada: de frente,
un tubo cubierto de púas es un rectángulo gris, y en planta las 500 vueltas se
pisan unas a otras. Lo que hay que mirar en estas piezas es otra cosa —cuánto
sobresale la superficie en cada punto— y eso es exactamente lo que dibuja una
máscara, así que se puede comparar con `lamparas.superficie` a ojo.

Dos paneles:

- **Relieve desenrollado**: el ángulo en horizontal (0°..360°), la altura en
  vertical, y el brillo es cuánto sale el radio por encima de la pared en ese
  punto. Oscuro = liso, claro = púa afuera. Acá aparecen las flores.
- **Detalle en planta**: un sector de 16° de una sola vuelta, a escala, con el
  recorrido tal cual. Acá se ve la FORMA de la púa —si el pulso salió cuadrado
  o si el muestreo lo redondeó— que en el desenrollado no se distingue.

El radio se mide contra el MÍNIMO de cada franja de altura y no contra el
radio medio: en una pieza con púas el promedio se corre hacia afuera según
cuánta púa haya en esa franja, así que una franja llena de flores —o sea lisa—
daba más "relieve" que una texturada. El mínimo es la pared, que es contra lo
que sobresale la púa de verdad.

    python3 vista_relieve.py output/florero.gcode vista.png
    python3 vista_relieve.py output/florero.gcode vista.png --ancho 1.0 --z 5:200
"""
import sys, math, zlib, struct
sys.path.insert(0, '.')
from verificar_pieza import leer

W, H = 1180, 660
PANEL, MARGEN = 760, 20
COLS, FILAS = PANEL, H - 2 * MARGEN


def _args(argv):
    ruta, salida = argv[1], argv[2]
    ancho, z0, z1 = 1.0, None, None
    i = 3
    while i < len(argv):
        if argv[i] == "--ancho":
            ancho = float(argv[i + 1]); i += 2
        elif argv[i] == "--z":
            a, b = argv[i + 1].split(":"); z0, z1 = float(a), float(b); i += 2
        else:
            raise SystemExit(f"opción desconocida: {argv[i]}")
    return ruta, salida, ancho, z0, z1


def main() -> int:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    ruta, salida, ancho, z0, z1 = _args(sys.argv)
    segs = leer(ruta, ancho)
    if not segs:
        raise SystemExit("el g-code no tiene segmentos extruyendo")

    # El centro sale SOLO de la pieza, nunca de todo el archivo: las líneas de
    # purga corren por el borde de la cama y con ellas adentro el centro se va
    # varios centímetros, el ángulo de cada punto queda mal y el desenrollado
    # sale con una costura que no existe. Es el mismo error que ya está anotado
    # en `comun.py` sobre las "fases 0.25/0.76".
    zs = sorted(s[2] for s in segs)
    piso = zs[len(zs) // 20] + 1.0        # por encima de la purga
    cuerpo = [s for s in segs if s[2] > piso]
    if not cuerpo:
        cuerpo = segs
    cx = (max(s[0] for s in cuerpo) + min(s[0] for s in cuerpo)) / 2
    cy = (max(s[1] for s in cuerpo) + min(s[1] for s in cuerpo)) / 2

    # --- panel 1: el relieve, por celda (ángulo, altura) ---
    #
    # UNA FILA DE LA REJILLA ES UNA VUELTA, no un píxel de alto. Con filas de
    # píxel, en una pieza de 60 mm cada fila abarcaba 0.09 mm de altura contra
    # los 0.4 que sube una vuelta: cada fila se quedaba con un cuarto de vuelta,
    # el resto de sus columnas vacías, y el contador de púas devolvía 33 de las
    # 150 que hay. El número salía mal por la rejilla, no por la pieza — es el
    # patrón que ya está anotado en `.agents/MAPA.md`: sospechar del medidor.
    #
    # Las vueltas se cuentan integrando el ángulo del recorrido, que es lo
    # único que no depende de suponer un paso de capa constante (y en modo vaso
    # no lo es: `marcha_vertical` lo acorta donde hace falta).
    giro = 0.0
    previo = None
    for x, y, z, *_ in cuerpo:
        a = math.atan2(y - cy, x - cx)
        if previo is not None:
            giro += abs((a - previo + math.pi) % (2 * math.pi) - math.pi)
        previo = a
    vueltas = max(1, round(giro / (2 * math.pi)))
    print(f"  {vueltas} vueltas medidas sobre el recorrido")

    zmin = z0 if z0 is not None else min(s[2] for s in cuerpo)
    zmax = z1 if z1 is not None else max(s[2] for s in cuerpo)
    if zmax <= zmin:
        raise SystemExit("el rango de z está vacío")

    ALTO_REJILLA = min(vueltas, 4000)
    rejilla = [[None] * COLS for _ in range(ALTO_REJILLA)]
    for x, y, z, *_ in cuerpo:
        if not (zmin <= z <= zmax):
            continue
        f = min(ALTO_REJILLA - 1,
                int((z - zmin) / (zmax - zmin) * ALTO_REJILLA))
        a = math.atan2(y - cy, x - cx) % (2 * math.pi)
        c = int(a / (2 * math.pi) * COLS) % COLS
        r = math.hypot(x - cx, y - cy)
        v = rejilla[f][c]
        rejilla[f][c] = r if v is None or r > v else v

    # la pared de cada vuelta: el mínimo de la vuelta, no el promedio
    pared = []
    for fila in rejilla:
        vals = [v for v in fila if v is not None]
        pared.append(min(vals) if vals else 0.0)
    relieve = max(
        (max(v - pared[i] for v in fila if v is not None) for i, fila in enumerate(rejilla)
         if any(v is not None for v in fila)), default=0.0)
    # Piso absoluto a la escala. Sin esto, una pieza sin relieve amplifica el
    # ruido de coma flotante hasta saturar y se ve un mapa lleno de textura
    # donde no hay nada — ya pasó dos veces en el preview (ver .agents/SKILL.md).
    escala = max(relieve, 0.15)

    # --- cuántas púas hay POR VUELTA, medidas sobre el g-code ---
    #
    # No es adorno: es la verificación de que la pieza tiene la textura que se
    # pidió, hecha sobre el archivo y no sobre el parámetro. Y hace falta acá
    # por un motivo de dibujo: con 150 púas repartidas en 760 columnas, cada
    # púa cae en una columna y deja cuatro oscuras al lado, así que el mapa sale
    # rayado y las flores no se leen. Sabiendo el período, cada píxel toma el
    # MÁXIMO de una ventana de una púa de ancho: el rayado desaparece sin que se
    # mueva el borde de la figura, que es lo que hay que mirar acá.
    def _picos(fila, base):
        n = 0
        for c in range(COLS):
            v = fila[c]
            if v is None:
                continue
            izq, der = fila[(c - 1) % COLS], fila[(c + 1) % COLS]
            if izq is None or der is None:
                continue
            if v - base > escala * 0.30 and v >= izq and v > der:
                n += 1
        return n

    # Se toma la vuelta MÁS texturada, no el promedio ni un percentil: en una
    # pieza con figura, la mayoría de las vueltas cruza zonas lisas y ahí no hay
    # púas que contar. Lo que se quiere verificar es el período de la textura, y
    # ese está entero en la vuelta que va toda texturada.
    por_vuelta = max((_picos(fila, pared[i]) for i, fila in enumerate(rejilla)),
                     default=0)
    print(f"  púas contadas en el g-code: {por_vuelta} por vuelta "
          f"(en la vuelta más texturada)")
    ventana = max(1, round(COLS / por_vuelta)) if por_vuelta else 1

    buf = bytearray(b'\x18' * (W * H * 3))

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            buf[i:i + 3] = bytes(c)

    # A ESCALA, los dos ejes con los mismos mm por píxel. Sin esto el mapa
    # miente sobre el DIBUJO, que es lo único que se viene a mirar acá: en una
    # prueba de 60 mm de alto y 214 de perímetro, estirar cada eje a su panel
    # daba 3.6 px/mm a lo ancho contra 10.7 a lo alto, y unas flores redondas
    # se veían como manchas estiradas. Se decidía sobre una deformación del
    # visor, no sobre la pieza.
    perimetro = 2 * math.pi * (sum(pared) / max(1, len(pared)))
    alto_mm = zmax - zmin
    esc = min(PANEL / max(perimetro, 1e-9), (H - 2 * MARGEN) / max(alto_mm, 1e-9))
    ancho_px, alto_px = int(perimetro * esc), int(alto_mm * esc)
    ox = MARGEN + (PANEL - ancho_px) // 2
    oy = MARGEN + (H - 2 * MARGEN - alto_px) // 2

    for y_panel in range(alto_px):
        f = min(ALTO_REJILLA - 1, int(y_panel / alto_px * ALTO_REJILLA))
        y = oy + (alto_px - 1 - y_panel)
        for c_px in range(ancho_px):
            c = int(c_px / ancho_px * COLS)
            v = None
            for d in range(-(ventana // 2), ventana - ventana // 2):
                w = rejilla[f][(c + d) % COLS]
                if w is not None and (v is None or w > v):
                    v = w
            if v is None:
                continue
            k = min(1.0, max(0.0, (v - pared[f]) / escala))
            px(ox + c_px, y, (int(30 + 205 * k), int(45 + 195 * k), int(35 + 120 * k)))

    # --- panel 2: una vuelta en planta, un sector, a escala ---
    x0 = MARGEN + PANEL + MARGEN
    lado = W - x0 - MARGEN
    zc = (zmin + zmax) / 2
    vuelta = [s for s in cuerpo if abs(s[2] - zc) < 0.5]
    def linea(ax, ay, bx, by, col):
        n = int(max(abs(bx - ax), abs(by - ay))) + 1
        for k in range(n + 1):
            t = k / n
            px(int(ax + (bx - ax) * t), int(ay + (by - ay) * t), col)
    if vuelta:
        rmax = max(math.hypot(s[0] - cx, s[1] - cy) for s in vuelta)
        # El sector se ELIGE, no se fija en 0°: en una pieza con figura, el 0°
        # cae adentro de una flor la mitad de las veces y el detalle sale liso,
        # que es justo lo que este panel no viene a mostrar. Se busca el sector
        # con más relieve.
        SECTOR = math.radians(16)
        mejor, centro = -1.0, 0.0
        for k in range(72):
            a0 = k / 72 * 2 * math.pi - math.pi
            rr = [math.hypot(q[0] - cx, q[1] - cy) for q in vuelta
                  if abs((math.atan2(q[1] - cy, q[0] - cx) - a0 + math.pi)
                         % (2 * math.pi) - math.pi) < SECTOR / 2]
            if len(rr) > 4 and max(rr) - min(rr) > mejor:
                mejor, centro = max(rr) - min(rr), a0
        # un sector, no la vuelta entera: en la vuelta entera 150 púas sobre
        # 300 px no se distinguen de una circunferencia gruesa
        # El sector se encuadra por su ALTO —que es lo que crece con el
        # ángulo— y se centra poniendo el punto medio del arco en el medio del
        # panel. Encuadrándolo por el ancho, el arco de 16° se iba entero fuera
        # del panel y el detalle salía en negro.
        esc_d = (H - 2 * MARGEN) / (2 * rmax * math.sin(SECTOR / 2)) * 0.92
        cyp = H / 2
        cxp = x0 + lado / 2 - rmax * esc_d
        for x1_, y1_, _z, x2_, y2_, _z2, *_ in vuelta:
            a1 = math.atan2(y1_ - cy, x1_ - cx)
            if abs((a1 - centro + math.pi) % (2 * math.pi) - math.pi) > SECTOR / 2:
                continue
            ca, sa = math.cos(-centro), math.sin(-centro)
            ux1, uy1 = x1_ - cx, y1_ - cy
            ux2, uy2 = x2_ - cx, y2_ - cy
            linea(cxp + (ux1 * ca - uy1 * sa) * esc_d, cyp - (ux1 * sa + uy1 * ca) * esc_d,
                  cxp + (ux2 * ca - uy2 * sa) * esc_d, cyp - (ux2 * sa + uy2 * ca) * esc_d,
                  (235, 235, 235))

    filas_png = b''.join(b'\x00' + bytes(buf[y * W * 3:(y + 1) * W * 3]) for y in range(H))

    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c))

    open(salida, 'wb').write(
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(filas_png, 6)) + chunk(b'IEND', b''))
    print(f"{salida}: relieve desenrollado (izq, 0°..360° x z {zmin:.0f}..{zmax:.0f}) "
          f"y detalle en planta a z {zc:.0f} (der)")
    print(f"  relieve máximo medido: {relieve:.2f} mm  (escala del mapa: {escala:.2f} mm)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
