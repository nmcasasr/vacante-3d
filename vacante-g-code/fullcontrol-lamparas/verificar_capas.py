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

TOL = 0.02          # mm


def leer_marcas(ruta):
    """(capas, movimientos) — capas es una lista de dicts por CHANGE_LAYER."""
    capas, moves = [], []
    z = None
    actual = None
    for linea in open(ruta, errors="ignore"):
        t = linea.strip()
        for patron, clave in ((r"^; Z_HEIGHT: ([0-9.]+)", "z_bambu"),
                              (r"^; LAYER_HEIGHT: ([0-9.]+)", "h_bambu"),
                              (r"^;Z:([0-9.]+)", "z_prusa"),
                              (r"^;HEIGHT:([0-9.]+)", "h_prusa"),
                              (r"^;WIDTH:([0-9.]+)", "w_prusa")):
            m = re.match(patron, t)
            if m and actual is not None:
                actual[clave] = float(m.group(1))
        if t.startswith("; CHANGE_LAYER"):
            actual = {"i": len(capas)}
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

    z_real = max(z for _, z in moves)
    check(abs(zs[-1] - z_real) < 0.5, "la última capa llega al techo de la pieza",
          f"declara {zs[-1]:.2f}, la pieza llega a {z_real:.2f}")

    fuera = 0
    for i, z in moves:
        techo, alto = zs[i], hs[i]
        if not (techo - alto - TOL <= z <= techo + TOL):
            fuera += 1
    check(fuera == 0, "cada movimiento cae dentro de su capa",
          f"{fuera} de {len(moves)} fuera de rango" if fuera else "")

    # Las marcas del cuerpo caen DESPUÉS del bloque que abre el injerto, así que
    # cada capa lleva las suyas y las de la siguiente. Se compara contra la que
    # el injerto declaró, con la tolerancia de un paso.
    dif = [i for i, c in enumerate(capas)
           if c.get("z_prusa") is not None
           and abs(c["z_prusa"] - c["z_bambu"]) > 0.5]
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
