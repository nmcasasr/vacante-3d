#!/usr/bin/env python3
"""
Coherencia de las marcas de capa que lee el visor del slicer.

Existe porque una incoherencia acá no rompe la impresión —son comentarios— pero
deja la pieza MAL DIBUJADA, y eso se confunde con un defecto de la pieza. Pasó:
se declaró como altura de capa la separación sobre la superficie (0.400) cuando
la vuelta sube 0.05 en Z, las 425 capas sumaban ~170 mm para una pieza de 117, y
Orca la mostró cortada por la mitad.

En modo vaso conviven dos alturas y NO son la misma:

    subida       cuánto sube la vuelta en Z. Es la que apila el visor.
    separación   distancia entre vueltas medida sobre la superficie. Es la que
                 manda en la extrusión. Donde la pared se tumba, 0.400 contra
                 0.05 de subida.

Lo que se comprueba:

  1. Z_HEIGHT crece siempre.
  2. El cordón no deja hueco: LAYER_HEIGHT[i] >= lo que subió la capa.
     NO se exige igualdad. Eso valdría si las capas embaldosaran, y en modo
     vaso no lo hacen: donde la pared se acuesta el cordón mide 1.265 mm de
     alto mientras la vuelta sube 0.050, y se solapan a propósito. Exigir
     igualdad marcaba 421 capas "rotas" que están bien.
  3. La última capa declarada llega al techo real de la pieza.
  4. Cada movimiento cae dentro del rango de la capa que lo contiene.
  5. Los dos dialectos (Bambu y Prusa) dicen lo mismo.

    python3 verificar_capas.py output/hongo_fix.gcode
"""

import re
import sys
import zipfile

TOL = 0.02          # mm


def lineas_de(ruta):
    """Las líneas del g-code, sea `.gcode` o `.gcode.3mf`.

    Sin esto, pasarle un `.3mf` —que es lo que de verdad se manda a imprimir—
    abría el zip como texto, no encontraba ni un `; CHANGE_LAYER` y salía por
    "no hay marcas". O sea que el verificador que existe para comprobar las
    marcas de capa NO comprobaba nada justo en el archivo que las lleva, y lo
    decía con un mensaje que parecía un problema del archivo.
    """
    if ruta.lower().endswith(".3mf"):
        with zipfile.ZipFile(ruta) as z:
            nombre = next((n for n in z.namelist()
                           if n.endswith("plate_1.gcode")), None)
            if nombre is None:
                raise ValueError(f"{ruta}: no tiene Metadata/plate_1.gcode")
            return z.read(nombre).decode("utf8", "ignore").splitlines()
    with open(ruta, errors="ignore") as f:
        return f.read().splitlines()


def leer_marcas(ruta):
    """(capas, movimientos) — capas es una lista de dicts por CHANGE_LAYER."""
    capas, moves = [], []
    z = None
    actual = None
    # El `;Z:` del cuerpo se emite JUSTO ANTES del `; CHANGE_LAYER` que abre su
    # capa, así que asignárselo a la capa abierta se lo da a la anterior. Se
    # guarda aparte y lo recoge el CHANGE_LAYER siguiente.
    #
    # Esto vivió escondido detrás de una tolerancia de 0.5 mm: mientras el paso
    # fue de 0.4, la Z de la capa siguiente caía dentro y el desfase no se veía.
    # Con capa de 0.8 —la de la referencia— 52 de 75 capas dieron "discrepan".
    z_prusa_pendiente = None
    for linea in lineas_de(ruta):
        t = linea.strip()
        m = re.match(r"^;Z:([0-9.]+)", t)
        if m:
            z_prusa_pendiente = float(m.group(1))
        for patron, clave in ((r"^; Z_HEIGHT: ([0-9.]+)", "z_bambu"),
                              (r"^; LAYER_HEIGHT: ([0-9.]+)", "h_bambu"),
                              (r"^;HEIGHT:([0-9.]+)", "h_prusa"),
                              (r"^;WIDTH:([0-9.]+)", "w_prusa")):
            m = re.match(patron, t)
            if m and actual is not None:
                actual[clave] = float(m.group(1))
        if t.startswith("; CHANGE_LAYER"):
            actual = {"i": len(capas)}
            if z_prusa_pendiente is not None:
                actual["z_prusa"] = z_prusa_pendiente
                z_prusa_pendiente = None
            capas.append(actual)
            continue
        crudo = t.split(";")[0].strip()
        if crudo.startswith(("G0", "G1")):
            for tok in crudo.split()[1:]:
                if tok[:1].upper() == "Z":
                    try:
                        z = float(tok[1:])
                    except ValueError:
                        pass
            if z is not None and actual is not None and "E" in crudo.upper():
                moves.append((actual["i"], z))
    return capas, moves


def main():
    ruta = sys.argv[1]
    capas, moves = leer_marcas(ruta)
    if not capas:
        print(f"{ruta}: no hay marcas '; CHANGE_LAYER'", file=sys.stderr)
        return 1
    fallos = 0

    def check(ok, texto, detalle=""):
        nonlocal fallos
        fallos += not ok
        print(f"  {'ok  ' if ok else 'FALLA'}  {texto}{'   ' + detalle if detalle else ''}")

    zs = [c.get("z_bambu") for c in capas]
    hs = [c.get("h_bambu") for c in capas]
    check(all(v is not None for v in zs + hs), "todas las capas declaran Z_HEIGHT y LAYER_HEIGHT")

    bajadas = [i for i, (a, b) in enumerate(zip(zs, zs[1:])) if b <= a]
    check(not bajadas, "Z_HEIGHT crece siempre",
          f"{len(bajadas)} violaciones, primera en la capa {bajadas[0]}" if bajadas else "")

    huecos = [(i + 1, (b - a) - h) for i, (a, b, h) in enumerate(zip(zs, zs[1:], hs[1:]))
              if (b - a) - h > TOL]
    solapes = [h - (b - a) for a, b, h in zip(zs, zs[1:], hs[1:]) if h > (b - a)]
    check(not huecos, "el cordón cubre lo que sube la capa (sin huecos)",
          f"{len(huecos)} capas dejan hueco, el peor {max(v for _, v in huecos):.3f} mm"
          if huecos else
          f"solape máximo {max(solapes):.3f} mm donde la pared se acuesta"
          if solapes else "")

    # Cuánto sube y baja el patrón DENTRO de una vuelta, medido del propio
    # archivo. Hace falta antes de juzgar la última capa: en una pieza calada la
    # cresta de la última vuelta queda por encima de su marca, por construcción,
    # y ese margen es la amplitud de la onda y no un número fijo.
    onda = 0.0
    for i, z in moves:
        techo, alto = zs[i], hs[i]
        if z < techo - alto:
            onda = max(onda, techo - alto - z)
        elif z > techo:
            onda = max(onda, z - techo)

    # La tolerancia de 0.5 mm que había acá estaba calibrada con `amplitud_z`
    # 0.5. Al subir la amplitud a 0.7 la misma pieza sana empezó a fallar por
    # 0.70 mm: la cresta de la última vuelta sobresale exactamente lo que
    # ondula el patrón. Atada a la onda medida, el criterio deja de depender de
    # con qué amplitud se generó la pieza.
    z_real = max(z for _, z in moves)
    sobra = z_real - zs[-1]
    check(-0.5 < sobra <= onda + 0.5, "la última capa llega al techo de la pieza",
          f"declara {zs[-1]:.2f}, la pieza llega a {z_real:.2f} "
          f"({sobra:+.2f}, la onda da {onda:.2f})")

    # Cuánto se sale de su capa cada movimiento, no solo si se sale.
    #
    # En una pieza CALADA la mitad de los puntos se sale por construcción: la
    # boquilla sube y baja dentro de la vuelta para abrir el patrón, y una
    # "capa" es una rebanada plana. Contarlos como fallas daba 53152 de 117166
    # en la caperuza y no significaba nada.
    #
    # Lo que sí es una falla es un movimiento que cae en OTRA capa, o sea que se
    # sale por más de una altura de capa entera: eso ya no es la onda, es la
    # marca de capa puesta en el lugar equivocado —el defecto que dejó una pieza
    # de 58 mm renderizada como un panqueque—. La onda está acotada por su
    # amplitud; un desfase de marca no está acotado por nada.
    #
    # Medido en la caperuza: excursión máxima 0.500 mm, que es exactamente su
    # `amplitud_z`. Ni un punto por encima. Con capas de 0.647 mm, cero fallas.
    # Lo que se mide es la MEDIANA de cada capa, no cada punto suelto.
    #
    # La onda es simétrica alrededor del centro de la vuelta, así que su mediana
    # cae dentro de la banda por más que la mitad de los puntos se salga. Una
    # marca corrida de capa mueve la mediana entera y no la tapa nada. Así el
    # criterio separa las dos cosas sin depender de ningún umbral inventado.
    #
    # Se sigue informando la excursión máxima de un punto, porque dice cuán
    # profundo baja el patrón, pero no decide el ok/falla.
    por_capa = {}
    for i, z in moves:
        por_capa.setdefault(i, []).append(z)
    corridas = []
    for i, v in por_capa.items():
        v.sort()
        med = v[len(v) // 2]
        techo, alto = zs[i], hs[i]
        if med < techo - alto - TOL:
            corridas.append((i, techo - alto - med))
        elif med > techo + TOL:
            corridas.append((i, med - techo))

    fuera = []
    for i, z in moves:
        techo, alto = zs[i], hs[i]
        if z < techo - alto - TOL:
            fuera.append(techo - alto - z)
        elif z > techo + TOL:
            fuera.append(z - techo)
    peor = max(fuera, default=0.0)

    check(not corridas, "la marca de capa cae donde está el material",
          f"{len(corridas)} capas con la mediana fuera de su banda, la peor "
          f"{max(d for _i, d in corridas):.3f} mm (capa {max(corridas, key=lambda c: c[1])[0]})"
          if corridas else
          f"{len(fuera)} de {len(moves)} puntos ondulan fuera de su capa, hasta "
          f"{peor:.3f} mm: es el patrón calado, y está acotado" if fuera else "")

    # Ahora que cada `;Z:` va con su capa, los dos dialectos declaran el mismo
    # número y la tolerancia puede ser estrecha. La de 0.5 que había acá era la
    # que escondía el desfase de una capa, y con paso de 0.8 dejaba de tapar.
    dif = [i for i, c in enumerate(capas)
           if c.get("z_prusa") is not None
           and abs(c["z_prusa"] - c["z_bambu"]) > 0.001]
    check(not dif, "los dos dialectos declaran lo mismo",
          f"{len(dif)} capas discrepan" if dif else "")

    anchos = {c.get("w_prusa") for c in capas if c.get("w_prusa") is not None}
    check(len(anchos) >= 1, "el ancho de cordón se declara explícito",
          f"valores: {sorted(anchos)}")

    print(f"\n{len(capas)} capas · z {zs[0]:.2f} a {zs[-1]:.2f} · "
          f"altura de capa {min(hs):.3f} a {max(hs):.3f} · {fallos} fallando")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
