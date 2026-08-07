"""
Placa de probetas: varias celosías chiquitas en fila, cada una con una
configuración distinta, para compararlas en una sola impresión.

Por qué una placa y no una torre: `solape`, `amplitud_z` y `capas_transicion`
definen la geometría de la espiral entera, y la modulación por nodo vive dentro
de cada vuelta. Nada de eso se puede cambiar por bandas de altura como la
velocidad. Tienen que ser piezas separadas.

    ./venv/bin/python placa_prueba.py            # las probetas de PROBETAS
    ./venv/bin/python placa_prueba.py --nombre X # otro nombre de salida
"""

import argparse

import fullcontrol as fc

from lamparas.bowls import a_gcode, guardar_gcode, pasos_bowl
from lamparas.comun import Perfil

# Geometría de cada probeta. Chica para que la placa salga rápido, pero con el
# mismo puente al aire que la pieza real: 2*pi*14/12 = 7.3 mm, contra los
# 7.85 mm de la boca del bowl grande. Si no se conserva el puente, la prueba no
# dice nada sobre la pieza que importa.
ALTURA = 12.0
RADIO_BASE = 10.0
RADIO_BOCA = 14.0
N_NODOS = 12

# SEPARACIÓN: manda el ancho del CABEZAL, no el de la pieza.
#
# Con 40 mm el cabezal tumbó las probetas ya impresas. El chequeo de colisión
# validaba que la PUNTA despejara en Z — y despejaba. Lo que golpea es el
# cuerpo: ducto de ventilador y bloque calefactor se extienden varios
# centímetros a los lados de la punta, así que mientras la boquilla imprime el
# borde de una probeta, el cabezal ya está sobre la vecina.
SEPARACION = 80.0
Y = 128.0
ALTURA_VIAJE = ALTURA + 10.0  # las probetas suben más que ALTURA: el paso_z se pasa de largo

# Valores comunes a todas. Lo único que cambia entre probetas va en PROBETAS.
#
# EL VENTILADOR NO SE MODULA. Se intentó (menos aire en el cruce para soldar,
# más en la cresta para que no descuelgue) y el resultado fue que el ventilador
# NO ARRANCA NUNCA. Medido sobre el gcode: 6463 comandos en el cuerpo, cada
# nivel sostenido 64 ms, o sea 15.6 Hz. Un blower 5015 tarda 500-1000 ms en
# cambiar de régimen — le estábamos pidiendo 10x más rápido de lo que puede, y
# además el 20 % del cruce está por debajo del umbral con el que un blower
# arranca desde parado. Queda fijo por probeta.
#
# La velocidad y el ancho SÍ se modulan: el planificador de movimiento las
# obedece al instante (la aceleración es 500 mm/s², pasar de 10 a 2 mm/s toma
# 0.01 s), y el ancho es solo cuánta E se empuja.
BASE = dict(
    solape=0.30,
    amplitud_z=0.5,
    capas_transicion=6,
    ancho_linea=1.0,      # el cordón nunca baja de 1 mm (la boquilla es de 0.8)
    ancho_nodo=1.6,       # ESCALÓN: blob en el cruce, hilo fino en el vano
    espera=0,             # ms parado en cada cruce (0 = sin espera)
    espera_cada=1,
    velocidad=600,        # en el cruce
    velocidad_pico=120,   # en la cresta: 2 mm/s, el cordón va al aire
    # El ventilador sigue la ESTRUCTURA, no es un valor global. Copiado del
    # gcode de Squeezy Fidget Toy: 0 % en toda la seccion maciza (Z 0.4-27.6) y
    # 100 % en cuanto empieza el calado. Lo macizo sin aire queda mas fuerte y
    # transparente; los puentes con aire no se descuelgan. Resuelve el conflicto
    # claridad/calado: no son la misma zona de la pieza.
    ventilador=0,         # en la base maciza
    ventilador_calado=100,
    altura_calado=2.0,    # a que altura arranca el calado
    temperatura=240,      # PETG: mas caliente no solidifica y se descuelga
)

# Un solo parámetro distinto por probeta, para que el resultado sea legible.
PROBETAS = [
    ("sin espera", dict(espera=0)),
    ("espera 1.5s", dict(espera=1500)),
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--nombre", default="placa_prueba")
    args = p.parse_args()

    n = len(PROBETAS)
    x0 = 128.0 - SEPARACION * (n - 1) / 2

    pasos = []
    for i, (nombre, cambio) in enumerate(PROBETAS):
        cfg = {**BASE, **cambio}
        x = x0 + i * SEPARACION
        perfil = Perfil(
            ancho_linea=cfg["ancho_linea"],
            velocidad_impresion=cfg["velocidad"],
            ventilador=cfg["ventilador"],
            centro=(x, Y),
        )
        # Sin "ventilador": ver la nota en BASE. El blower no puede seguirlo.
        modulacion = {
            "velocidad": (cfg["velocidad"], cfg["velocidad_pico"]),
            "ancho": (cfg["ancho_nodo"], cfg["ancho_linea"]),
        }
        if cfg["espera"]:
            modulacion["espera"] = (cfg["espera"], 1.5, cfg["espera_cada"])
        propios = pasos_bowl(
            diseno="celosia",
            silueta="copa",
            altura=ALTURA,
            perfil=perfil,
            parametros=dict(n_nodos=N_NODOS, solape=cfg["solape"], amplitud_z=cfg["amplitud_z"]),
            parametros_silueta=dict(radio_base=RADIO_BASE, radio_boca=RADIO_BOCA),
            capas_transicion=cfg["capas_transicion"],
            modulacion=modulacion,
            # Cada probeta tiene su propio dict, asi que el cambio se dispara una
            # vez por pieza. Uno compartido lo consumiria la primera y las demas
            # imprimirian el calado sin ventilador.
            cambios={cfg["altura_calado"]: fc.Fan(speed_percent=cfg["ventilador_calado"])},
        )
        if i:
            # Tres movimientos, no uno. Si se sube y se viaja en el mismo paso,
            # el descenso se interpola a lo largo del recorrido y la boquilla
            # atraviesa la probeta recién terminada: medido, entraba a Z=8.9 mm
            # sobre una pieza de 13.8 mm.
            pasos.append(fc.Extruder(on=False))
            pasos.append(fc.Point(z=ALTURA_VIAJE))
            pasos.append(fc.Point(x=x, y=Y, z=ALTURA_VIAJE))
        # El ventilador se fija una vez por probeta. `pasos_iniciales` no lo
        # emite (vive en el start gcode, que el empaquetador descarta salvo el
        # de la primera), así que hay que ponerlo explícito o la probeta 2
        # heredaría el de la 1 y la comparación no valdría nada.
        pasos.append(fc.Fan(speed_percent=cfg["ventilador"]))
        pasos.extend(propios)
        print(f"  X={x:3.0f}  {nombre:8}  " + "  ".join(f"{k}={v}" for k, v in cambio.items()))

    # OJO con el ventilador de este Perfil: es el que escribe el start gcode, y
    # el empaquetador del .3mf lo lee como el estado inicial y lo restaura
    # después del injerto. Dejarlo en el default (100) hacía arrancar al 100 %
    # aunque la modulación pidiera 20 — mal para PETG, que no lo tolera.
    # Despues del marcador FIN DEL START GCODE: sobrevive al empaquetado del .3mf
    # y pisa la temperatura del template, que solo sirve para el calentado.
    pasos.insert(0, fc.ManualGcode(text=f"M104 S{BASE['temperatura']} ; temperatura de impresion"))

    gcode = a_gcode(
        pasos,
        Perfil(velocidad_impresion=BASE["velocidad"], ventilador=BASE["ventilador"]),
    )
    ruta = guardar_gcode(gcode, args.nombre)
    print(f"\nGenerado: {ruta} ({len(pasos)} pasos, {len(gcode.splitlines())} líneas)")


if __name__ == "__main__":
    main()
