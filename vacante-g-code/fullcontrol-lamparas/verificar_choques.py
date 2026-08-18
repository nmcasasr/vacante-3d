#!/usr/bin/env python3
"""
¿La boquilla atraviesa en algún momento material ya depositado?

Existe porque un archivo empaquetado rompió una pieza y golpeó la máquina. El
end g-code de la plantilla traía `G1 Z26.1 ; lower z a little` —26.1 es la
altura del objeto CON EL QUE SE EXPORTÓ LA PLANTILLA, más 0.5— y sobre una
pieza de 41.7 mm eso baja el cabezal 15 mm adentro y después la cruza a
300 mm/s. Ningún verificador lo vio: todos miraban el cuerpo, y esto pasa
DESPUÉS del cuerpo.

El método no supone nada sobre qué parte del archivo es qué. Recorre el archivo
entero —start g-code, cuerpo y end g-code— llevando dos cosas:

  1. un mapa de alturas: para cada celda de 1 mm en X/Y, hasta dónde llegó el
     material depositado ahí;
  2. la posición de la boquilla.

En cada movimiento, antes de depositar, se muestrea el trayecto y se pregunta si
la boquilla pasa por debajo del techo del material que ya hay en esa celda. Si
pasa, es un choque.

Uso:
    python3 verificar_choques.py pieza.gcode.3mf
    python3 verificar_choques.py output/hongo/hongo_squeezy.gcode
"""

import math
import sys
import zipfile
from collections import defaultdict

CELDA = 1.0        # mm, lado de la celda del mapa de alturas
PASO = 0.5         # mm, cada cuánto se muestrea un movimiento
# Cuánto se le perdona antes de llamarlo choque. En modo vaso la Z sube DENTRO
# de la vuelta, así que la boquilla pasa rozando el material de la vuelta
# anterior todo el tiempo; sin holgura eso sería un choque en cada segmento.
HOLGURA = 0.5
GRAVE = 1.0        # por encima de esto no es roce, es un golpe
# Material depositado dentro de estos mm de recorrido queda DETRÁS de la
# boquilla. Una vuelta de estas piezas mide 300 mm o más, así que 8 mm no puede
# tapar un choque contra la vuelta anterior; lo único que descarta es que un
# trazo se choque consigo mismo por la resolución de la celda.
RECIENTE = 8.0
# Por debajo de esta holgura el archivo no choca, pero pasa demasiado cerca:
# un hilo, un poco de curling o una pieza que se despegó lo convierten en
# choque. Orca deja 0.5 mm de fábrica, pensando en una cara superior plana.
AVISO = 3.0


def leer(ruta):
    """Devuelve las líneas del g-code, sea .gcode o .gcode.3mf."""
    if ruta.lower().endswith(".3mf"):
        with zipfile.ZipFile(ruta) as z:
            nombre = next((n for n in z.namelist()
                           if n.endswith("plate_1.gcode")), None)
            if nombre is None:
                raise ValueError(f"{ruta}: no tiene Metadata/plate_1.gcode")
            return z.read(nombre).decode("utf8", "ignore").splitlines()
    with open(ruta, errors="ignore") as f:
        return f.read().splitlines()


def revisar(lineas):
    # Solo las celdas donde REALMENTE se depositó algo. Un defaultdict(float)
    # daba 0.0 en todas las demás, y entonces cualquier movimiento a Z negativa
    # —el `G1 Z-5` relativo del home de la A1— parecía un choque de 5 mm contra
    # material inexistente. La cama no es la pieza.
    altura = {}          # celda -> (techo, arco al que se depositó)
    arco = 0.0           # mm de recorrido acumulado
    x = y = z = 0.0
    e = 0.0
    relativo = False       # M83/M82: extrusión
    rel_xyz = False        # G91/G90: posición. El start g-code de la A1 mete
                           # varios bloques G91 y sus Z son incrementos, no
                           # alturas: leerlas como absolutas inventa choques.
    choques = []
    margen = []      # (holgura POSITIVA = cuánto le sobró, linea, texto, x, y, z, techo)

    fase = 0
    for n, linea in enumerate(lineas, 1):
        s = linea.strip()
        # El start g-code de la maquina RASPA sus propias lineas de purga a
        # proposito (la calibracion de extrusion, en Y -0.5). Medir holgura ahi
        # da -0.15 mm y no significa nada. Lo que importa es el cuerpo y, sobre
        # todo, la cola: ahi fue el choque que rompio la pieza.
        if "CHANGE_LAYER" in s and fase == 0:
            fase = 1
        elif "end of grafted body" in s:
            fase = 2
        if s.startswith("M83"):
            relativo = True
        elif s.startswith("M82"):
            relativo = False
        elif s.startswith("G91"):
            rel_xyz = True
        elif s.startswith("G90"):
            rel_xyz = False
        if not s.startswith(("G0", "G1")):
            continue

        nx, ny, nz, ne = x, y, z, None
        for tok in s.split():
            if tok.startswith(";"):
                break
            c, v = tok[:1].upper(), tok[1:]
            try:
                v = float(v)
            except ValueError:
                continue
            if c == "X":
                nx = x + v if rel_xyz else v
            elif c == "Y":
                ny = y + v if rel_xyz else v
            elif c == "Z":
                nz = z + v if rel_xyz else v
            elif c == "E":
                ne = v

        de = (ne if relativo else ne - e) if ne is not None else 0.0
        extruye = de > 0

        d = math.hypot(nx - x, ny - y)
        d3 = math.hypot(d, nz - z)
        pasos = max(1, int(d / PASO))
        for i in range(1, pasos + 1):
            t = i / pasos
            px, py = x + (nx - x) * t, y + (ny - y) * t
            pz = z + (nz - z) * t
            arco_p = arco + d3 * t
            celda = (int(px // CELDA), int(py // CELDA))
            techo, arco_techo = altura.get(celda, (None, 0.0))
            # El material que se acaba de depositar está DETRÁS de la boquilla,
            # no delante: no se puede chocar con él.
            #
            # Sin esta condición, una celosía de arcos altos se autodenuncia. La
            # celda mide 1 mm y guarda una sola altura, así que una pata que sube
            # 58° —la de un arco de 2.5 mm de paso— entra en la celda a z 1.99 y
            # sale a z 0.95, y al salir se compara contra su propia entrada: 1.04
            # mm "dentro del material", GRAVE, 188 veces. La pieza está bien; lo
            # que no da es la resolución del mapa.
            #
            # Se descartan sólo los últimos RECIENTE mm de recorrido. Una vuelta
            # de estas piezas mide 300 mm o más, así que esto nunca puede tapar
            # un choque contra la vuelta anterior, que es lo que importa.
            reciente = arco_p - arco_techo < RECIENTE
            if techo is not None and not reciente and techo - pz > HOLGURA:
                choques.append((n, s[:60], px, py, pz, techo, techo - pz))
            # Cuánto le sobró. Un archivo que no choca pero pasa a 0.2 mm de la
            # pieza no es seguro: es un choque que todavía no ocurrió. Solo
            # cuenta en movimientos SIN extrusión — mientras deposita, la
            # boquilla está pegada al material a propósito.
            # Solo cuando la boquilla se MUEVE en X/Y. Parada en el sitio
            # —la retracción del final, con el cabezal donde terminó— la
            # holgura es 0 por definición y no es un peligro.
            if techo is not None and not reciente and not extruye and d > 0:
                margen.append((pz - techo, n, s[:60], px, py, pz, techo, fase))
            if extruye:
                if techo is None or pz >= techo:
                    altura[celda] = (pz, arco_p)
                else:
                    altura[celda] = (techo, arco_techo)

        # Un movimiento que solo baja/sube en Z tampoco es inocente: puede
        # clavarse sobre material que está justo debajo.
        if d == 0 and nz != z:
            celda = (int(nx // CELDA), int(ny // CELDA))
            techo, arco_techo = altura.get(celda, (None, 0.0))
            if (techo is not None and arco + abs(nz - z) - arco_techo >= RECIENTE
                    and techo - nz > HOLGURA):
                choques.append((n, s[:60], nx, ny, nz, techo, techo - nz))

        arco += d3 if d3 else abs(nz - z)
        if ne is not None:
            e = ne if relativo else ne
        x, y, z = nx, ny, nz

    return choques, margen, max((h for h, _ in altura.values()), default=0.0)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    fallando = 0
    for ruta in sys.argv[1:]:
        try:
            choques, margen, alto = revisar(leer(ruta))
        except (OSError, ValueError, zipfile.BadZipFile) as err:
            print(f"{ruta}: {err}", file=sys.stderr)
            fallando += 1
            continue

        nombre = ruta.split("/")[-1]
        graves = [c for c in choques if c[6] > GRAVE]
        if not choques:
            print(f"  {nombre:34s} pieza {alto:7.2f} mm · sin choques")
            for fase, etiqueta in ((1, "cuerpo"), (2, "cola (end gcode)")):
                del_tramo = [m for m in margen if m[7] == fase]
                if not del_tramo:
                    continue
                h, ln, txt, mx, my, mz, techo, _ = min(del_tramo)
                sello = "OK" if h >= AVISO else "JUSTO"
                print(f"       {etiqueta:18s} holgura mínima {h:6.2f} mm   {sello}")
                if h < AVISO:
                    print(f"           línea {ln}: {txt}  "
                          f"(Z{mz:.2f} sobre material de {techo:.2f})")
            continue

        peor = max(choques, key=lambda c: c[6])
        fallando += 1
        print(f"  {nombre:34s} pieza {alto:7.2f} mm · "
              f"{len(choques)} muestras en choque ({len(graves)} graves)   CHOCA")
        print(f"       el peor: {peor[6]:.2f} mm dentro del material, "
              f"en X{peor[2]:.1f} Y{peor[3]:.1f} Z{peor[4]:.2f} "
              f"(el material llega a {peor[5]:.2f})")
        print(f"       línea {peor[0]}: {peor[1]}")
    return 1 if fallando else 0


if __name__ == "__main__":
    sys.exit(main())
