#!/usr/bin/env python3
"""
Banco de pruebas del verificador, con casos de respuesta conocida.

Existe porque el verificador dio dos veces un veredicto equivocado sobre una
pieza entera, y las dos veces el error era una sola constante mal puesta:

- `HOLGURA` aplicada también en horizontal aceptaba cordones separados 1.98 mm
  con cordón de 1.8, o sea que NO SE TOCAN. Con eso di por buenas unas lenguas
  que el modo solape del preview pintaba rojas enteras.
- Antes de eso, el `M83` del start gcode se leía fuera de rango y todos los
  cordones daban 0.000 mm de alto.

Ninguno de los dos se veía mirando una pieza de 180 000 segmentos. Los dos se
ven en cuatro líneas de g-code con la respuesta sabida de antemano.

    python3 test_verificar.py
"""

import math
import subprocess
import sys
import tempfile
from pathlib import Path

ANCHO, ALTO = 1.8, 0.4
AREA_FIL = math.pi * (1.75 / 2) ** 2
LARGO = 20.0            # cada cordón es un segmento recto de 20 mm
# El verificador juzga por muestras a lo largo del cordón, no por segmento: un
# cordón de 20 mm da 25 muestras. Un "1" acá sería un cordón apoyado en casi
# todo su largo, que no es lo que estos casos plantean.
N = 25

import verificar_pieza as V


def gcode(cordones, area=ANCHO * ALTO):
    """
    Un g-code mínimo. Cada cordón es (x, y, z, etiqueta): un segmento recto de
    20 mm en Y, con la extrusión que corresponde a `area`.
    """
    e = area * LARGO / AREA_FIL
    lineas = ["M83 ; relative extrusion", ";===== FIN DEL START GCODE ====="]
    for x, y, z, tipo in cordones:
        lineas.append(f";TIPO:{tipo}")
        lineas.append(f"G0 X{x} Y{y} Z{z}")
        lineas.append(f"G1 X{x} Y{y + LARGO} Z{z} E{e:.5f}")
    f = Path(tempfile.mkdtemp()) / "t.gcode"
    f.write_text("\n".join(lineas) + "\n")
    return str(f)


def analizar(cordones, area=ANCHO * ALTO):
    """Devuelve (sin_apoyo, pisados) contando solo los cordones de la capa 2+."""
    segs = V.leer(gcode(cordones, area), ANCHO)
    assert len(segs) == len(cordones), f"se leyeron {len(segs)} de {len(cordones)}"
    import io, contextlib
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        V.medir(segs, ANCHO, ALTO)
    texto = salida.getvalue()
    sueltos = sum(int(l.split(":")[1].split("/")[0])
                  for l in texto.splitlines() if "sin apoyo" in l)
    pisados = sum(int(l.split(":")[1].split("/")[0])
                  for l in texto.splitlines() if "pisadas" in l)
    finos = sum(int(l.split("(>20:1)")[1].split("/")[0])
                for l in texto.splitlines() if "irrealizable" in l)
    return sueltos, pisados, finos


# Cada caso: nombre, cordones, (sueltos, pisados, irrealizables) esperados.
# El primero de cada caso está en la capa 1 y el verificador lo da por apoyado
# en la cama; lo que se juzga es el segundo.
CASOS = [
    ("apilado justo encima",
     [(0, 0, 0.4, "a"), (0, 0, 0.8, "b")], (0, 0, 0)),

    ("al lado a la separación de fusión (1.71 = ancho - 0.215*alto)",
     [(0, 0, 0.4, "a"), (1.71, 0, 0.4, "b")], (0, 0, 0)),

    ("al lado a 1.26: se toca de sobra y NO cuenta como pisado",
     [(0, 0, 0.4, "a"), (1.26, 0, 0.4, "b")], (0, 0, 0)),

    ("al lado a 0.6: los ejes casi coinciden, es material de más",
     [(0, 0, 0.4, "a"), (0.6, 0, 0.4, "b")], (0, N - 3, 0)),

    ("al lado SIN solape: ejes a un cordón entero, se rozan",
     [(0, 0, 0.4, "a"), (0, 0, 0.8, "a2"), (1.80, 0, 0.8, "b")], (N, 0, 0)),

    ("al aire, lejos de todo",
     [(0, 0, 0.4, "a"), (50, 0, 0.8, "b")], (N, 0, 0)),

    ("voladizo del 25 % en una capa: se sostiene",
     [(0, 0, 0.4, "a"), (0.45, 0, 0.8, "b")], (0, 0, 0)),

    # 1.26 de corrimiento con cordón de 1.8 deja 0.54 mm montados, o sea 30 %
    # del ancho: es un voladizo empinado pero se sostiene. El modelo de elipse
    # lo daba por suelto y por eso el generador llenaba de pasadas cortas donde
    # no hacía falta.
    ("voladizo con 30 % de solape: se sostiene",
     [(0, 0, 0.4, "a"), (1.26, 0, 0.8, "b")], (0, 0, 0)),

    # Con 1.70 quedan 0.10 mm montados sobre un cordón de 1.8: eso es rozar.
    ("voladizo con 6 % de solape: NO se sostiene",
     [(0, 0, 0.4, "a"), (1.70, 0, 0.8, "b")], (N, 0, 0)),

    ("el mismo lugar dos veces",
     [(0, 0, 0.4, "a"), (0, 0, 0.4, "b")], (0, N - 3, 0)),

    ("dos capas de altura de golpe",
     [(0, 0, 0.4, "a"), (0, 0, 1.2, "b")], (N, 0, 0)),
]


def main():
    fallos = 0
    for nombre, cordones, esperado in CASOS:
        obtenido = analizar(cordones)
        bien = obtenido == esperado
        fallos += not bien
        print(f"  {'ok  ' if bien else 'FALLA'}  {nombre}")
        if not bien:
            print(f"          esperaba (sueltos,pisados,finos)={esperado} "
                  f"y dio {obtenido}")

    # Fabricabilidad: el mismo cordón con un décimo del área es 45:1.
    obtenido = analizar([(0, 0, 0.4, "a"), (0, 0, 0.8, "b")], area=ANCHO * 0.04)
    bien = obtenido[2] == 2
    fallos += not bien
    print(f"  {'ok  ' if bien else 'FALLA'}  cordón de 1.8 x 0.04 (45:1) es irrealizable")
    if not bien:
        print(f"          esperaba 2 irrealizables y dio {obtenido[2]}")

    # El piso absoluto: un cordón de 0.04 mm tiene que salir IMPOSIBLE aunque
    # la referencia tenga cordones parecidos.
    import io, contextlib
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        V.medir(V.leer(gcode([(0, 0, 0.4, "a"), (0, 0, 0.8, "b")], ANCHO * 0.04),
                       ANCHO), ANCHO, ALTO)
    # El criterio informa qué FRACCIÓN DEL RECORRIDO va por debajo del piso, no
    # el peor segmento: una pieza entera de cordón imposible tiene que dar 100 %.
    fila = [l for l in salida.getvalue().splitlines() if "línea fina" in l]
    bien = bool(fila) and "100.00%" in fila[0] and "PEOR" in fila[0]
    fallos += not bien
    print(f"  {'ok  ' if bien else 'FALLA'}  el piso de altura de cordón se mide sobre el recorrido")
    if not bien:
        print(f"          dio: {fila[0].strip() if fila else '(sin fila)'}")

    print(f"\n{len(CASOS) + 2} casos · {fallos} fallando")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
