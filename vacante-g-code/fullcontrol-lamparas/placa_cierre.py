"""
Placa de tres bolas para probar cómo cerrar la parte de arriba sin que se hunda.

Las tres son la MISMA geometría (la cabeza del hongo a escala 0.35) y sólo
cambia el proceso hacia el ápice, que es lo que el artículo de Claywoven
—el autor del `Squeezy Fidget Toy.gcode` que usamos de referencia— identifica
como la variable que decide. Ver `.agents/CIERRE-SUPERIOR.md`.

UNA TÉCNICA POR BOLA, aisladas, para ver qué aporta cada una:

    1  gradiente de velocidad    su "speed multiplier 0.18": 7.0 -> 1.26 mm/s
    2  sobre-extrusión 2.5 %     su "nozzle size 0.82 contra 0.8 física"
    3  gradiente + ventilador    el aire que tanto él como Squeezy sí usan

NO se prueba la velocidad constante: ya sabemos que hunde la punta.

NO se prueba su "surface incline". Medido sobre la imagen del artículo, su tapa
tiene 1.21° de inclinación —es una tapa PLANA a la que le dio un grado para que
no fuera exactamente horizontal—. La nuestra termina a 10.2°: ya tenemos diez
veces más inclinación que él. Su problema era una tapa plana; el nuestro es una
cúpula que converge. La técnica no aplica.

Sobre el ventilador de la 3: nuestras piezas van con 0 % en toda la altura, y
ese es el único caso que ni él ni la referencia usan. Su flujo estándar es
apagado en la primera capa y PRENDIDO el resto; `Squeezy Fidget Toy.gcode` lo
prende al 100 % en z 27.6 y lo deja así hasta el final, cúpula superior
incluida. Se prende de un solo escalón, como la referencia: el blower tarda
500-1000 ms en cambiar de régimen y no sigue una rampa fina.

    ./venv/bin/python placa_cierre.py
"""

import argparse
import math

import fullcontrol as fc

from lamparas.comun import Perfil, a_gcode, generar_pieza, guardar_gcode
from lamparas import perfil as _perfil

DXF = "../../gcodes/reference/hongis.dxf"
DESDE, HASTA = 124.4, 241.0
ESCALA = 0.35

ANCHO_LINEA = 1.2
ALTURA_CAPA = 0.8
VELOCIDAD = 420          # mm/min = 7.0 mm/s
TEMPERATURA = 245
HUECO = 11.55            # diámetro del agujero del piso

# La rampa hacia el ápice. Arranca donde la inclinación de la tapa cruza los
# ~34° y llega al mínimo en el borde del agujero de arriba.
Z_RAMPA_INI = 37.0
Z_RAMPA_FIN = 41.2
ESCALONES = 10
FACTOR_MINIMO = 0.18     # el de Claywoven: 3.6 mm/s sobre 20
# La tapa inclinada de la probeta 3. `perfil.limitar` recorta la pendiente de
# la silueta para que el radio no se corra más de un cordón por vuelta, o sea
# reemplaza los últimos milímetros casi horizontales por el cono más cerrado
# que sí apoya. Es la misma idea que el "surface incline" del artículo:
#
#   "When the enclosed section is completely flat, it becomes much harder to
#    get the layers to stack correctly."
#
# Nuestra tapa termina a 10.2° de la horizontal, que es el caso que él marca
# como difícil.

# SEPARACIÓN: manda el CUERPO del cabezal, no la punta.
#
# `placa_prueba.py` lo tiene medido a golpes: con 40 mm de centros el cabezal
# tumbó las probetas ya impresas, y con 80 mm sobre piezas de 28 mm no. O sea
# ~52 mm de aire entre superficies.
#
# Pero ese precedente es sobre probetas de 13.8 mm de alto y las nuestras miden
# 41.6: el cuerpo del cabezal pasa cerca de la vecina durante mucho más tiempo.
# Así que no se copia el número, se maximiza.
#
# EN TRIÁNGULO, NO EN DIAGONAL. Tres piezas en línea diagonal sobre una cama de
# 256 dan 113 mm entre centros; en triángulo dan 160. Es el mismo espacio usado
# mejor, y casi duplica el aire entre superficies sin costar nada.
CENTROS = [(48.0, 48.0), (208.0, 48.0), (128.0, 208.0)]

# Altura de viaje: por encima de la pieza más alta, con margen. Los viajes van
# en TRES movimientos (subir, viajar, bajar) porque en uno solo el descenso se
# interpola a lo largo del camino y la boquilla atraviesa la bola anterior.
ALTURA_VIAJE = 55.0


def rampa_velocidad():
    """Escalones de velocidad hacia el ápice, aproximando un gradiente.

    `fc.Printer` cambia de golpe, así que el gradiente del artículo —él lo pinta
    con aerógrafo— se aproxima con escalones cortos. El paso importa: su intento
    fallido fue bajar de una a 4 mm/s, y el que funciona llega al MISMO valor
    mínimo pero gradualmente.
    """
    cambios = {}
    for i in range(ESCALONES + 1):
        f = i / ESCALONES
        z = Z_RAMPA_INI + (Z_RAMPA_FIN - Z_RAMPA_INI) * f
        v = VELOCIDAD * (1.0 - f * (1.0 - FACTOR_MINIMO))
        cambios[round(z, 2)] = fc.Printer(print_speed=int(round(v)))
    return cambios


# (nombre, ¿rampa de velocidad?, ancho de cordón, tope de dr/dz de la tapa)
#
# El tope se traduce a `limitar` como ancho = tope * altura_capa, porque esa
# función acota el corrimiento por vuelta y no la pendiente directamente.
# 4.50 da una tapa de 12.5°, contra los 10.2° que trae el DXF.
#
# La sobre-extrusión sale de su relación: 0.82 declarado sobre 0.8 real es
# +2.5 %, que sobre nuestro cordón de 1.2 da 1.23.
# (nombre, ¿rampa de velocidad?, ancho de cordón, ¿ventilador arriba?)
PROBETAS = [
    ("1 gradiente velocidad",  True,  ANCHO_LINEA, False),
    ("2 sobre-extrusion 2.5%", False, 1.23,        False),
    ("3 gradiente + aire",     True,  ANCHO_LINEA, True),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nombre", default="hongo/cierre")
    # UNA PIEZA POR ARCHIVO, no una placa.
    #
    # La A1 tiene la varilla inferior del pórtico a 25 mm de la cama
    # (`extruder_clearance_height_to_rod` en el perfil de Orca) y la cama se
    # mueve en Y por debajo. Una bola ya impresa de 41.6 mm pasa por debajo de
    # esa varilla cada vez que la cama la lleva ahí, y ninguna separación
    # horizontal lo evita: el choque es vertical. Imprimir por objeto sólo es
    # seguro con piezas más bajas que 25 mm.
    ap.add_argument("--placa", action="store_true",
                    help="las tres en una placa (PELIGROSO con piezas > 25 mm)")
    args = ap.parse_args()

    curva = _perfil.elegir(_perfil.curvas(DXF))
    radio, info = _perfil.radio_de(curva, DESDE, HASTA)
    altura = info["alto"] * ESCALA
    silueta = lambda t: radio(t) * ESCALA          # noqa: E731

    print(f"  bola: {2 * info['r_max'] * ESCALA:.1f} mm de diámetro x {altura:.1f} de alto")
    d = min(math.hypot(a[0] - b[0], a[1] - b[1])
            for i, a in enumerate(CENTROS) for b in CENTROS[i + 1:])
    print(f"  separación mínima entre centros: {d:.0f} mm "
          f"({d - 2 * info['r_max'] * ESCALA:.0f} mm de aire entre superficies)")

    pasos = []
    for i, ((nombre, con_rampa, ancho, con_aire), (cx, cy)) in enumerate(zip(PROBETAS, CENTROS)):
        if not args.placa:
            cx, cy = 128.0, 128.0     # cada una sola y centrada
        perfil = Perfil(
            ancho_linea=ancho,
            altura_capa=ALTURA_CAPA,
            velocidad_impresion=VELOCIDAD,
            temp_boquilla=TEMPERATURA,
            temp_cama=80,
            ventilador=0,
            centro=(cx, cy),
        )
        cambios = rampa_velocidad() if con_rampa else {}
        if con_aire:
            # Un solo escalón, donde arranca la zona del ápice. Igual que la
            # referencia, que pasa de 0 a 100 % de una en z 27.6.
            cambios[Z_RAMPA_INI - 0.01] = fc.Fan(speed_percent=100)
        propios = generar_pieza(
            funcion_radio=lambda ang, t: silueta(t),
            altura=altura,
            perfil=perfil,
            segmentos_por_capa=240,
            base_solida=True,
            hueco=HUECO,
            refuerzo_hueco=0,
            cambios=cambios or None,
        )
        if args.placa and i:
            # Tres movimientos. En uno solo el descenso se interpola y la
            # boquilla entra por arriba de la bola recién terminada.
            pasos.append(fc.Extruder(on=False))
            pasos.append(fc.Point(z=ALTURA_VIAJE))
            pasos.append(fc.Point(x=cx, y=cy, z=ALTURA_VIAJE))
        # El ventilador, explícito por probeta: el start gcode de la segunda en
        # adelante lo descarta el empaquetador, y heredaría el de la primera.
        pasos.append(fc.Fan(speed_percent=0))
        pasos.extend(propios)
        print(f"    {nombre:24s} vel {'7.0->1.3' if con_rampa else '7.0 fija '} · "
              f"cordon {ancho} · aire {'100% desde z37' if con_aire else 'apagado'}")
        if not args.placa:
            ruta = guardar_gcode(a_gcode(pasos, perfil), f"{args.nombre}{i+1}")
            print(f"      -> {ruta.name}")
            pasos = []

    if not args.placa:
        return
    ruta = guardar_gcode(a_gcode(pasos, Perfil(
        ancho_linea=ANCHO_LINEA, altura_capa=ALTURA_CAPA,
        velocidad_impresion=VELOCIDAD, temp_boquilla=TEMPERATURA,
        temp_cama=80, ventilador=0, centro=CENTROS[0])), args.nombre)
    print(f"  guardado: {ruta}")


if __name__ == "__main__":
    main()
