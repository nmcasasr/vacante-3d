#!/usr/bin/env python3
"""
Los TRES criterios sobre un g-code, medidos juntos y separados por etiqueta.

Cada veredicto equivocado de la sesión anterior salió de medir uno solo:

1. **Fabricabilidad** — el cordón que se le pide a la boquilla tiene que
   existir. El g-code no dice el ancho ni el alto: dice cuánto filamento empuja
   por milímetro recorrido, o sea el ÁREA. Con el ancho nominal se despeja el
   alto. Por encima de ~10:1 de ancho contra alto, una boquilla de 0.8 no tiende
   una cinta: sale un hilo. Es lo que Orca pinta azul oscuro.

2. **Contacto** — `(dh/ancho)^2 + (dv/alto)^2 <= 1`. Comparar la distancia cruda
   contra el ANCHO da por sobre-extruida la vecindad vertical normal del modo
   vaso —las vueltas van a 0.4 en Z, que es correcto—; de ahí salió un
   "89 % sobre-extruido" que era falso.

   Solo cuenta como apoyo el material **ya impreso**: se busca entre los
   segmentos anteriores del recorrido, no entre todos. Lo que se deposita
   después no sostiene nada en el momento en que la boquilla pasa.

   Se descartan los vecinos cercanos EN EL RECORRIDO, medidos por longitud de
   arco recorrida y no por índice. Por índice se descartaban también los arcos
   de al lado de una lengua —que están a treinta y pico de segmentos— que son
   justamente su apoyo real.

3. **Puentes** — un tramo largo sin apoyo se descuelga aunque tenga material.
   Se miden en milímetros de recorrido seguido al aire, no en cantidad de
   segmentos: mil segmentos sueltos repartidos son otra cosa que mil seguidos.

La separación pared/lengua sale de los comentarios `;TIPO:` que el generador
deja al emitir. **No se deduce por geometría**: deducirla por radio fue lo que
hizo abandonar el enfoque correcto: los primeros arcos de cada lengua nacen
pegados a la pared y caían del lado equivocado del filtro.

Uso:
    python3 verificar_pieza.py output/glitch4.gcode [--ancho 1.8] [--alto 0.4]
"""

import argparse
import collections
import math
import re
import sys

AREA_FILAMENTO = math.pi * (1.75 / 2) ** 2

# Relación ancho/alto del cordón. Dos líneas, no una, y calibradas contra la
# referencia validada y no a ojo: `hongo.gcode` se imprime bien y tiene 13.3 %
# de cordones por encima de 10:1 y 5.5 % por encima de 20:1, con el peor en
# 23:1. O sea que 10:1 NO es la frontera de lo imposible — a esa altura el
# cordón sale fino y planchado, que es lo que hace la cúpula del hongo.
# La frontera de lo que directamente no sale queda en 20:1.
RELACION_FINA = 10.0
RELACION_MAXIMA = 20.0

# Piso de altura de cordón, en mm. Por debajo de esto la boquilla no tiende una
# cinta: sale un hilo.
#
# Se mide como FRACCIÓN DEL RECORRIDO por debajo del piso, no por el peor
# segmento. Juzgar por el peor es frágil: `Squeezy Fidget Toy.gcode` es un
# objeto impreso y viable y tiene un segmento de 0.048 mm, y el jarrón tiene uno
# de 0.001 — todo g-code real tiene alguna transición degenerada. Lo que
# distingue a una pieza sana de una enferma es cuánto recorrido va fino:
#
#     Squeezy   0.26 %      vase   0.19 %      hongo   4.07 %      glitch2  24.31 %
ALTO_MINIMO = 0.10
# Radio de búsqueda de vecinos, en mm. Más allá de esto no hay contacto posible.
BUSQUEDA = 3.0
# Cuánto recorrido hay que alejarse, en mm de arco, para que un segmento cuente
# como vecino y no como la continuación del propio trazo.
ARCO_VECINO = 2.5
# Cada cuánto se muestrea un segmento para juzgarlo, en mm.
MUESTRA = 0.8
# Un tramo al aire más largo que esto se descuelga por su propio peso.
PUENTE_MAXIMO = 12.0
# Holgura del criterio de contacto, y va SOLO en el eje vertical. En modo vaso
# la vuelta de arriba queda EXACTAMENTE tangente a la de abajo —dv = alto por
# construcción, justo sobre el borde del elipse— y sin holgura la referencia
# buena daba 85 % suelto.
#
# Aplicarla también en horizontal fue un error caro: con cordón de 1.8 aceptaba
# ejes separados 1.98 mm, o sea cordones que NO SE TOCAN. Con eso di por buenas
# unas lenguas con 15 % de solape que el modo solape del preview pintaba rojas
# enteras. La holgura vertical corrige una tangencia de construcción; en
# horizontal no hay nada que corregir y solo afloja el criterio.
# --- el modelo de cordón --------------------------------------------------
#
# Un cordón de ancho w y alto h NO es un elipse: es un rectángulo de (w-h) x h
# con dos semicírculos de radio h/2 a los costados. Es el modelo que usa
# cualquier slicer, y la diferencia importa: el núcleo es PLANO, así que un
# corrimiento horizontal menor que (w-h) no cuesta nada de margen vertical.
# Eso es exactamente lo que hace el modo vaso, y con el elipse la tangencia del
# modo vaso caía justo sobre el borde del criterio: cualquier ruido la cruzaba y
# la referencia buena daba 56 % sin apoyo.
#
# Dos cordones se tocan si la distancia entre sus NÚCLEOS no pasa h.
#
# Las dos direcciones NO son simétricas, y tratarlas igual fue el error caro:
#
#   Vertical. En modo vaso la vuelta de arriba queda a dv = h de la de abajo por
#   construcción, o sea exactamente tangente. Ahí hace falta holgura, porque el
#   alto se reconstruye desde la extrusión y la tangencia exacta es un filo.
#
#   Lateral. Acá no hay ninguna tangencia de construcción que perdonar: dos
#   cordones a un ancho exacto de distancia se ROZAN, no se montan, y eso no es
#   apoyo. Aplicarle la misma holgura al eje horizontal aceptaba ejes separados
#   1.98 mm con cordón de 1.8 — cordones que no se tocan.
TOLERANCIA_V = 1.10     # holgura sobre la tangencia vertical de construcción
SOLAPE_LATERAL = 0.08   # solape mínimo que se exige de costado, en fracción de h


def _fusion(ancho, alto):
    """Separación a la que dos cordones planos vecinos se funden."""
    return ancho - 0.215 * alto


def tocan(dh, dv, ancho, alto):
    """¿Se tocan dos cordones cuyos ejes están a (dh, dv)?"""
    nucleo = max(0.0, ancho - alto)
    if dh <= nucleo:
        # El núcleo de arriba cae sobre el de abajo: solo pesa la altura.
        return abs(dv) <= alto * TOLERANCIA_V
    # Se salió del núcleo: hay que morder de costado, y de costado se exige
    # solape real, no rozar.
    return math.hypot(dh - nucleo, dv) <= alto * (1 - SOLAPE_LATERAL)


# Por debajo de esta fracción de la separación de fusión, los ejes están tan
# juntos que el material no entra: es el mismo lugar ocupado dos veces.
FRACCION_PISADO = 0.70

# La referencia es `Squeezy Fidget Toy.gcode`: un objeto impreso, viable, y de
# la misma familia de formas que la cabeza del hongo.
#
# NO es `hongo.gcode`, que fue la referencia durante toda una sesión y no
# servía: tiene el 4.07 % del recorrido con el cordón por debajo de 0.10 mm
# contra el 0.26 % de Squeezy, y su cordón mediano (0.366 mm²) es menos de la
# mitad del de las piezas de referencia (~0.9). Calibrar contra ella dejaba
# pasar justamente el defecto que había que cazar.
REFERENCIA = {
    # Medidos con este mismo script sobre las piezas impresas y viables. Se toma
    # el peor de los dos, que es el que define "no peor que algo que funciona".
    #
    #                       fino    contacto   puentes   choque
    #   Squeezy cúpulas     0.11 %    1.88 %      1      12.53 %
    #   jarrón              0.10 %    0.11 %      1      39.51 %
    #
    # Estos números salieron pasándole a cada pieza SU cordón. Medirlas con los
    # defaults que había antes (1.8 x 0.4) las condenaba a todas: la jarra daba
    # 96.13 % sin apoyo en vez de 0.11 %, y la referencia 45.32 % en vez de
    # 19.41 %. Por eso el cordón ahora se lee del archivo y, si no está, se
    # avisa. Si alguno de estos números no reproduce, lo primero a mirar es con
    # qué cordón se midió.
    "fino": 0.26,
    "sin_apoyo": 1.88,
    "puente_max": PUENTE_MAXIMO,
    # CHOQUE QUEDA FUERA DEL VEREDICTO, y no por conveniencia: marca el 39.51 %
    # del jarrón, que está impreso y funciona. Un criterio que condena a la
    # referencia no sirve para juzgar nada. Se sigue informando —es útil para
    # comparar dos versiones de la misma pieza— pero no decide.
    "pisado": None,
}

# La misma referencia medida ENTERA, que es como se imprimió y funciona.
#
# Los números de arriba salen de sus CÚPULAS, que son pared maciza. Contra ellos
# cualquier pieza calada da "NO IMPRIMIBLE" por definición: un calado puentea al
# aire a propósito, y ahí "sin apoyo" no es un defecto sino el diseño.
#
# Medido con este script sobre SU ZONA CALADA (--z 28:70) y con su cordón real,
# 1.2 x 0.8 mm — que no lo declara, así que hay que pasárselo a mano:
#
#     fino 0.06 %  ·  sin apoyo 63.85 %  ·  choque 19.92 %  ·  peor puente 15.2 mm
#
# Va la zona calada y no el archivo entero porque el archivo entero es 60 % de
# pared maciza, que arrastra el promedio a 19.41 % y deja un baremo que ninguna
# pieza 100 % calada puede cumplir. Y se puede acotar sin sesgo recién ahora:
# `--z` acota QUÉ SE PUNTÚA, no qué sostiene (ver `medir`). Con el sesgo viejo
# esta misma medición daba un puente de 4531 mm.
#
# El 1.2 x 0.8 no es a ojo: su zona maciza extruye 0.960 mm² por mm, que es
# exactamente 1.2 x 0.8. Con los defaults de antes (1.8 x 0.4) el mismo archivo
# daba 45.32 % sin apoyo. Y estos números sí se parecen a los documentados
# arriba (choque 12.53 %, fino 0.11 %), lo que confirma de dónde venía el
# desfase.
#
# 15.2 mm de puente es mucho, y es real: la referencia cruza huecos de 10.8 mm
# y se imprime. Lo que lo hace posible es que espera 1.5 s en CADA nodo.
#
# Va el archivo ENTERO y no la banda `--z 28:70` a propósito: acotar por altura
# sesga la medición, porque el material que queda debajo de la banda desaparece
# del mapa de apoyo y la primera vuelta de la banda sale "al aire". Es lo que
# hace que `--z 70:97` reporte un puente de 4531 mm que no existe, y casi con
# seguridad es de dónde salía el 1.88 % de arriba.
REFERENCIA_CALADA = {
    "fino": 0.26,
    "sin_apoyo": 63.85,
    # EN MILÍMETROS, no en cantidad de tramos. Contar tramos castiga a la pieza
    # por ser grande: la referencia entera tiene 98 y su propia celosía 95, así
    # que se condenaba a sí misma. Lo que descuelga un puente es su LARGO.
    "puente_max": 15.2,
    "pisado": None,
}


def leer(ruta, ancho, marcador="FIN DEL START GCODE"):
    """
    Segmentos extruidos: (x1,y1,z1,x2,y2,z2, area, etiqueta, arco).

    El marcador de fin del start gcode solo existe en los archivos que genera
    este proyecto. Los g-codes de referencia de otra gente no lo tienen, y la
    primera versión de esto devolvía una lista vacía sin decir nada: el informe
    salía en blanco y parecía que el archivo no tenía nada raro. Si no aparece,
    se lee el archivo entero.
    """
    x = y = z = e = 0.0
    # El modo de extrusión y la posición se siguen desde la PRIMERA línea del
    # archivo, aunque los segmentos solo se junten después del marcador: el
    # `M83` vive en el start gcode. Leyendo solo desde el marcador, el archivo
    # parecía de extrusión absoluta y todos los cordones daban 0.000 mm de alto.
    absoluto = True
    etiqueta = "sin etiqueta"
    texto = open(ruta, errors="ignore").read()
    hay_marcador = marcador in texto
    empezo = not hay_marcador
    arco = 0.0
    segs = []
    for cruda in texto.splitlines(True):
        if marcador in cruda:
            empezo = True
            continue
        if ";TIPO:" in cruda:
            etiqueta = cruda.split(";TIPO:")[1].strip()
            continue
        linea = cruda.split(";")[0].strip()
        if not linea:
            continue
        if linea.startswith("M83"):
            absoluto = False
            continue
        if linea.startswith("M82"):
            absoluto = True
            continue
        if linea.startswith("G92"):
            for tok in linea.split()[1:]:
                if tok[:1].upper() == "E":
                    e = float(tok[1:])
            continue
        if not linea.startswith(("G0", "G1")):
            continue
        px, py, pz, pe = x, y, z, e
        for tok in linea.split()[1:]:
            k = tok[0].upper()
            try:
                v = float(tok[1:])
            except ValueError:
                continue
            if k == "X":
                x = v
            elif k == "Y":
                y = v
            elif k == "Z":
                z = v
            elif k == "E":
                e = v if absoluto else pe + v
        if not empezo:
            continue
        largo = math.dist((px, py, pz), (x, y, z))
        if largo < 1e-9:
            continue
        de = e - pe
        if de <= 1e-9:          # viaje o retracción: no deposita nada
            continue
        arco += largo
        # El g-code solo sabe el área. El alto sale de dividirla por el ancho
        # nominal, que es el que la impresora tiene configurado en la geometría.
        segs.append((px, py, pz, x, y, z, de * AREA_FILAMENTO / largo, etiqueta, arco))
    return segs


def medir(segs, ancho, alto_nominal, franja=None):
    """
    `franja` = (z_min, z_max) acota QUÉ SE PUNTÚA, no qué existe.

    Filtrar los segmentos antes de entrar acá —que es lo que hacía `--z`— borra
    del mapa de apoyo el material que queda DEBAJO del corte, así que la primera
    vuelta de la banda sale flotando y arrastra a las siguientes. Sobre la
    referencia eso inventaba un puente de 4531 mm que el archivo entero no
    tiene. Acá los segmentos de fuera de la banda siguen sosteniendo; lo único
    que cambia es que no se los cuenta.
    """
    if not segs:
        print("no hay segmentos extruidos", file=sys.stderr)
        return 1

    z_base = min(min(s[2], s[5]) for s in segs)
    area_nominal = ancho * alto_nominal

    # ¿Es una pieza CALADA? Se detecta del recorrido, no de una etiqueta.
    #
    # En una espiral maciza la Z nunca baja mientras se extruye: sube parejo
    # vuelta tras vuelta. En un calado la boquilla BAJA a propósito en cada
    # cruce, para morder la vuelta de abajo y soldar ahí. Miles de segmentos
    # extruyendo cuesta abajo es la firma del patrón, y no la produce ninguna
    # otra cosa.
    #
    # De esto depende contra qué se compara: la celosía de la referencia da
    # 49.75 % sin apoyo y sus cúpulas 1.88 %. Elegir mal el baremo condena a
    # cualquier calado, incluida la propia referencia.
    bajando = sum(1 for s in segs if s[5] - s[2] < -0.05)
    calada = bajando > 0.01 * len(segs)
    baremo = REFERENCIA_CALADA if calada else REFERENCIA

    # --- 1. fabricabilidad -------------------------------------------------
    finos = collections.Counter()
    imposibles = collections.Counter()
    total = collections.Counter()
    mm_tot = collections.Counter()
    mm_fino = collections.Counter()
    peor = {}
    altos = []
    for s in segs:
        alto = s[6] / ancho
        altos.append(alto)
        total[s[7]] += 1
        rel = ancho / max(alto, 1e-9)
        if rel > RELACION_FINA:
            finos[s[7]] += 1
        if rel > RELACION_MAXIMA:
            imposibles[s[7]] += 1
        if s[7] not in peor or alto < peor[s[7]]:
            peor[s[7]] = alto
        largo_s = math.dist(s[:3], s[3:6])
        mm_tot[s[7]] += largo_s
        if alto < ALTO_MINIMO:
            mm_fino[s[7]] += largo_s

    # --- 2. contacto -------------------------------------------------------
    # Se evalúa POR MUESTRAS a lo largo del segmento, no por su punto medio, y
    # la rejilla guarda cada segmento en TODAS las celdas que atraviesa.
    #
    # Antes guardaba solo los extremos y preguntaba por el medio: un segmento
    # de 20 mm cae en siete celdas y no estaba en la del medio, así que era
    # invisible para la búsqueda. Con cordones de 1 mm casi no se notaba, pero
    # los cruces radiales de un sector duro miden 38 mm — justo los que hay que
    # medir. Un cordón largo tampoco se sostiene entero por un extremo: puede
    # estar apoyado en la punta y al aire en el medio, y eso solo se ve
    # muestreando.
    rejilla = collections.defaultdict(list)
    sueltos = []          # (indice_segmento, largo_de_la_muestra)
    pisados = []
    muestras_tot = collections.Counter()
    muestras_malas = collections.Counter()
    muestras_pisadas = collections.Counter()
    for i, s in enumerate(segs):
        x1, y1, z1, x2, y2, z2, area, tipo, arco = s
        puntuar = franja is None or franja[0] <= (z1 + z2) / 2 <= franja[1]
        largo = math.dist((x1, y1, z1), (x2, y2, z2))
        alto = area / ancho
        n_m = max(1, int(math.ceil(largo / MUESTRA)))
        d_m = largo / n_m
        for q in range(n_m):
            f = (q + 0.5) / n_m
            mx, my, mz = x1 + (x2-x1)*f, y1 + (y2-y1)*f, z1 + (z2-z1)*f
            arco_m = arco - largo + largo * f
            apoyado = mz < z_base + alto     # la primera capa se apoya en la cama
            choque = False
            gz, gx, gy = int(mz // BUSQUEDA), int(mx // BUSQUEDA), int(my // BUSQUEDA)
            for bz in (gz, gz - 1):
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for j in rejilla.get((bz, gx + dx, gy + dy), ()):
                            o = segs[j]
                            # Altura del vecino en el punto más cercano; para un
                            # segmento casi plano da igual, y para la rampa de
                            # una espiral evita errores de medio cordón.
                            dh2, oz = _cerca(mx, my, o)
                            dv = mz - oz
                            if dv < -0.02 or dv > BUSQUEDA:
                                continue          # lo de arriba no sostiene
                            hh = (alto + o[6] / ancho) / 2
                            if abs(arco_m - o[8]) < ARCO_VECINO and dv < hh / 2:
                                # El propio trazo, que no se sostiene a sí mismo.
                                # Solo si está a la MISMA altura: en el salto de
                                # capa de una lengua, el cordón de abajo es el
                                # vecino inmediato del recorrido y además su
                                # apoyo real.
                                continue
                            dh = math.sqrt(dh2)
                            w = _fusion(ancho, hh)
                            if dh < FRACCION_PISADO * w and abs(dv) < 0.5 * hh:
                                choque = True      # el mismo lugar dos veces
                            if tocan(dh, dv, ancho, hh):
                                apoyado = True
                            if apoyado and choque:
                                break
                        if apoyado and choque:
                            break
                    if apoyado and choque:
                        break
                if apoyado and choque:
                    break
            if not puntuar:
                continue
            muestras_tot[tipo] += 1
            if not apoyado:
                muestras_malas[tipo] += 1
                sueltos.append((i, arco_m, d_m, tipo, mz))
            if choque:
                muestras_pisadas[tipo] += 1
                pisados.append(i)
        # rasterizar el segmento en la rejilla: todas las celdas que cruza
        n_r = max(1, int(math.ceil(largo / (BUSQUEDA / 2))))
        vistas = set()
        for q in range(n_r + 1):
            f = q / n_r
            px, py, pz = x1 + (x2-x1)*f, y1 + (y2-y1)*f, z1 + (z2-z1)*f
            vistas.add((int(pz // BUSQUEDA), int(px // BUSQUEDA), int(py // BUSQUEDA)))
        for c in vistas:
            rejilla[c].append(i)

    # --- 3. puentes --------------------------------------------------------
    # Tramos de recorrido seguido sin apoyo: se cortan cuando hay un salto de
    # arco (o sea, un segmento apoyado en el medio).
    # Tramos de recorrido SEGUIDO sin apoyo: las muestras sueltas se encadenan
    # mientras sigan consecutivas en la longitud de arco.
    largos = []
    mm = 0.0
    ini_tipo, ini_z, ult_arco = None, 0.0, None
    for _, arco_m, d_m, tipo, zz in sueltos:
        if ult_arco is not None and abs(arco_m - ult_arco) > 1.6 * MUESTRA:
            largos.append((mm, ini_tipo, ini_z))
            mm, ini_tipo = 0.0, None
        if ini_tipo is None:
            ini_tipo, ini_z = tipo, zz
        mm += d_m
        ult_arco = arco_m
    if ini_tipo is not None:
        largos.append((mm, ini_tipo, ini_z))

    # --- informe -----------------------------------------------------------
    tipos = sorted(total)
    print(f"{len(segs)} segmentos extruidos · cordón nominal "
          f"{ancho} x {alto_nominal} mm (área {area_nominal:.3f} mm²)")
    print()
    print("1. FABRICABILIDAD  (ancho/alto del cordón que se le pide a la boquilla)")
    print(f"   referencia validada, hongo.gcode: {RELACION_FINA:.0f}:1 en 13.3 % · "
          f"{RELACION_MAXIMA:.0f}:1 en 5.5 % · peor 23:1")
    for tipo in tipos:
        f, m = finos[tipo], imposibles[tipo]
        print(f"   {tipo:>12}: fino (>{RELACION_FINA:.0f}:1) "
              f"{100 * f / total[tipo]:5.2f} % · "
              f"irrealizable (>{RELACION_MAXIMA:.0f}:1) {m:7d} / {total[tipo]:7d} "
              f"({100 * m / total[tipo]:5.2f} %) · más fino "
              f"{peor[tipo]:.3f} mm ({ancho / max(peor[tipo], 1e-9):.1f}:1)")

    print()
    print("2. CONTACTO  (núcleos de cordón que se tocan, contra material ya impreso)")
    for tipo in tipos:
        n, tt = muestras_malas[tipo], muestras_tot[tipo]
        print(f"   {tipo:>12}: {n:7d} / {tt:7d} muestras sin apoyo "
              f"({100 * n / max(tt, 1):5.2f} %)")

    print()
    print(f"4. CHOQUE  (cordón depositado donde ya hay material: ejes a menos "
          f"del {FRACCION_PISADO:.0%} de la separación de fusión)")
    for tipo in tipos:
        n, tt = muestras_pisadas[tipo], muestras_tot[tipo]
        print(f"   {tipo:>12}: {n:7d} / {tt:7d} muestras pisadas "
              f"({100 * n / max(tt, 1):5.2f} %)")

    print()
    print(f"3. PUENTES  (recorrido seguido al aire; > {PUENTE_MAXIMO:.0f} mm se descuelga)")
    if not largos:
        print("   ninguno")
    else:
        malos = [l for l in largos if l[0] > PUENTE_MAXIMO]
        largos.sort(reverse=True)
        print(f"   {len(largos)} tramos al aire · el peor {largos[0][0]:.1f} mm "
              f"({largos[0][1]}, z {largos[0][2]:.1f})")
        print(f"   por encima de {PUENTE_MAXIMO:.0f} mm: {len(malos)}")
        for mm, tipo, zz in largos[:6]:
            if mm > PUENTE_MAXIMO:
                print(f"      {mm:6.1f} mm  {tipo:>8}  z {zz:6.1f}")

    print()
    fab = sum(imposibles.values())
    con = sum(muestras_malas.values())
    pue = max((l[0] for l in largos), default=0.0)
    cho = sum(muestras_pisadas.values())
    n = len(segs)
    n_m = max(1, sum(muestras_tot.values()))
    pc_fino = 100 * sum(mm_fino.values()) / max(sum(mm_tot.values()), 1e-9)
    filas = [
        (f"línea fina (<{ALTO_MINIMO:.2f}mm)", pc_fino, baremo["fino"], "%"),
        ("contacto", 100 * con / n_m, baremo["sin_apoyo"], "%"),
        ("choque", 100 * cho / n_m, baremo["pisado"], "%"),
        ("peor puente", pue, baremo["puente_max"], "mm"),
    ]
    zona = "su CELOSÍA (z 28-70)" if calada else "sus CÚPULAS (pared maciza)"
    print(f"VEREDICTO  (contra Squeezy Fidget Toy.gcode, objeto impreso y viable)")
    print(f"   la pieza {'ES calada' if calada else 'es maciza'}: "
          f"{bajando} de {len(segs)} segmentos extruyen bajando "
          f"-> se compara contra {zona}")
    ok = True
    filas = [f for f in filas if f[2] is not None]
    for nombre, valor, tope, u in filas:
        # se compara redondeado a lo que se muestra: la referencia se midió con
        # este mismo script y su propio número no puede salir "PEOR" que él
        bien = round(valor, 2) <= tope + 1e-9
        ok = ok and bien
        print(f"   {nombre:>21}: {valor:8.2f} {u:<2} contra {tope:6.2f} {u:<2} "
              f"de la referencia   {'ok' if bien else 'PEOR'}")
    print(f"   -> {'IMPRIMIBLE' if ok else 'NO IMPRIMIBLE'}")
    veredicto = "IMPRIMIBLE" if ok else "NO IMPRIMIBLE"
    return 0 if veredicto == "IMPRIMIBLE" else 2


def _cordon_declarado(ruta):
    """
    Ancho y alto de cordón que declara el propio g-code, o None.

    Se toma la MEDIANA y no el primero: el alto varía a lo largo de una pieza de
    paso adaptativo (en la caperuza va de 0.085 a 0.700), y el primero es el de
    la capa de arranque, que es la menos representativa de todas.

    Los dos dialectos: ';WIDTH:' / ';HEIGHT:' es el de PrusaSlicer, que es el
    que emite este generador; '; LINE_WIDTH:' / '; LAYER_HEIGHT:' es el de Orca,
    que es el que agrega el empaquetador. Un archivo empaquetado trae los dos y
    dicen lo mismo (lo comprueba `verificar_capas.py`).
    """
    anchos, altos = [], []
    pat = re.compile(r"^;\s*(?:LINE_)?WIDTH:\s*([0-9.]+)|^;\s*(?:LAYER_)?HEIGHT:\s*([0-9.]+)")
    try:
        with open(ruta, errors="ignore") as fh:
            for l in fh:
                if not l.startswith(";"):
                    continue
                m = pat.match(l.strip())
                if not m:
                    continue
                if m.group(1):
                    anchos.append(float(m.group(1)))
                elif m.group(2):
                    altos.append(float(m.group(2)))
    except OSError:
        return None, None, "?"
    med = lambda v: sorted(v)[len(v) // 2] if v else None
    a, h = med(anchos), med(altos)
    return a, h, "declarado en el archivo" if (a and h) else "?"


def _cerca(px, py, o):
    """
    Distancia² en planta de un punto al segmento `o`, y la altura de `o` ahí.

    Devuelve las dos cosas juntas porque el punto más cercano es el mismo: usar
    la z del medio de un segmento que sube —la rampa de una espiral— mete medio
    cordón de error justo en el eje que más pesa en el criterio.
    """
    x1, y1, z1, x2, y2, z2 = o[0], o[1], o[2], o[3], o[4], o[5]
    vx, vy = x2 - x1, y2 - y1
    ll = vx * vx + vy * vy
    t = 0.0 if ll < 1e-12 else max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / ll))
    return (px - (x1 + t * vx)) ** 2 + (py - (y1 + t * vy)) ** 2, z1 + (z2 - z1) * t


def _dist2(px, py, x1, y1, x2, y2):
    """Distancia² de un punto al segmento, en planta."""
    vx, vy = x2 - x1, y2 - y1
    ll = vx * vx + vy * vy
    t = 0.0 if ll < 1e-12 else max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / ll))
    return (px - (x1 + t * vx)) ** 2 + (py - (y1 + t * vy)) ** 2


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gcode")
    ap.add_argument("--ancho", type=float, default=None,
                    help="ancho de cordón, mm. Por defecto se lee del archivo "
                         "(';WIDTH:' / '; LINE_WIDTH:').")
    ap.add_argument("--alto", type=float, default=None,
                    help="altura del cordón, mm. Por defecto se lee del archivo "
                         "(';HEIGHT:' / '; LAYER_HEIGHT:'). NO es un detalle: "
                         "es el eje que más pesa en el criterio de apoyo, y "
                         "pasarlo mal da un resultado sin sentido. La jarra "
                         "medida con 1.8x0.4 daba 96.13 %% sin apoyo; con su "
                         "cordón real (1.2x0.8) da 3.46 %%.")
    ap.add_argument("--z", default=None, metavar="MIN:MAX",
                    help="acotar a una franja de altura. Hace falta para medir "
                         "`Squeezy Fidget Toy.gcode`: es DOS CÚPULAS con una "
                         "celosía en el medio, y los hilos de la celosía cruzan "
                         # Los %% van dobles: argparse pasa el help por un
                         # formateo con %, y un % suelto lo hace explotar con
                         # `ValueError: incomplete format` al pedir --help.
                         "en el aire por diseño. OJO: acotar SESGA el apoyo. "
                         "El material que queda debajo del corte desaparece "
                         "del mapa, así que la primera vuelta de la banda sale "
                         "'al aire' y arrastra el resto. Sobre la referencia, "
                         "--z 70:97 inventa un puente de 4531 mm que el "
                         "archivo entero no tiene. Sirve para COMPARAR dos "
                         "versiones de la misma pieza en la misma banda, no "
                         "para juzgar una sola.")
    a = ap.parse_args()

    # El cordón sale del archivo, no de un default.
    #
    # Esto fue un agujero caro: con los valores que había por defecto (1.8 x 0.4)
    # la jarra —que está impresa y funciona— medía 96.13 % del recorrido sin
    # apoyo y un "puente" de 35 metros. Con su cordón real (1.2 x 0.8) da 3.46 %.
    # El criterio de apoyo compara la separación vertical contra la ALTURA del
    # cordón, así que pasarle 0.4 a una pieza de 0.8 declara que ninguna vuelta
    # toca la de abajo, en toda la pieza. El número salía, se veía plausible, y
    # no significaba nada.
    #
    # Los g-codes de este generador declaran las dos cosas. Los ajenos no, y por
    # eso ahí se avisa en vez de inventar.
    ancho, alto, de_donde = _cordon_declarado(a.gcode)
    if a.ancho is not None:
        ancho, de_donde = a.ancho, "--ancho/--alto"
    if a.alto is not None:
        alto, de_donde = a.alto, "--ancho/--alto"
    if ancho is None or alto is None:
        ancho = ancho if ancho is not None else 1.8
        alto = alto if alto is not None else 0.4
        print(f"AVISO: {a.gcode} no declara su cordón y no se pasó --ancho/--alto.\n"
              f"       Se usa {ancho} x {alto} mm, que probablemente no es el de "
              f"esta pieza.\n"
              f"       El apoyo y los puentes salen sin sentido si el alto no es "
              f"el real.", file=sys.stderr)
        de_donde = "DEFAULT SIN VALIDAR"
    print(f"cordón {ancho} x {alto} mm ({de_donde})")

    segs = leer(a.gcode, ancho)
    franja = None
    if a.z:
        lo, hi = (float(v) for v in a.z.split(":"))
        franja = (lo, hi)
    if not segs:
        print(f"{a.gcode}: no se leyó ningún segmento extruido. "
              f"¿El archivo tiene movimientos G1 con E creciente?", file=sys.stderr)
        return 1
    return medir(segs, ancho, alto, franja)


if __name__ == "__main__":
    sys.exit(main())
