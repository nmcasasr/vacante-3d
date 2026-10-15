"""
Genera el gusano modular en `output/gusano-modular/`: por cada diámetro, un
MÓDULO (un lóbulo con labio, se imprimen los que hagan falta y se apilan) y
una TAPA (el mismo lóbulo cerrado en cúpula).

    python gen_gusano_modular.py                 # Ø58, Ø78 y Ø95
    python gen_gusano_modular.py 120 150 180     # los grandes
    python gen_gusano_modular.py 78 --holgura 0.4
    python gen_gusano_modular.py --labio 10 --solo-modulos
    python gen_gusano_modular.py 95 --solo-modulos --clic 1.0

`--clic` es llave y cerradura: dos muescas arriba, al final del hombro, donde
caen las dos cuñas que la base del módulo de arriba lleva en sus dos primeras
vueltas. Las piezas cortas para probarlo salen con `--prueba`.

La geometría vive en `siluetas.gusano_modulo`. Este script sólo le pide al
generador la altura que la silueta dice que tiene —si no, la estira y el
encastre deja de coincidir— y usa la misma receta que el gusanito grande.
"""
import argparse
import json
import math
import os
import subprocess
import sys
sys.path.insert(0, '.')
from lamparas.bowls.siluetas import gusano_modulo

RECETA = [
    "--p", "mascara=ninguna", "--p", "amplitud=0", "--p", "dientes=0",
    "--sin-base", "--altura-capa", "0.8", "--ancho-linea", "1.2",
    "--material", "PETG", "--temp-primera-capa", "250", "--temperatura", "245",
    "--temp-cama", "70", "--velocidad", "480", "--segundos-vuelta", "25",
    "--ventilador", "0", "--ventilador-desde", "0.89", "--ventilador-desde-pct", "100",
    "--separacion", "marcha", "--segmentos", "240",
]

# Las tapas de cada diámetro, como (achatado, boca). Sin entrada: una sola,
# con la proporción del cuerpo y cerrada.
#
# La cúpula cerrada deja un tramo al aire en el ápice que crece con el radio
# (se descuelga a los 12 mm):
#   - Ø95: 12.6 mm. Estirándola un 9 % (0.80) baja a 7.4. No es monótono
#     —0.76 da 11.6, 0.78 10.2, 0.84 9.8—: depende de dónde cae la última
#     vuelta contra el ápice.
#   - Ø120: cierra sólo si es una esfera redonda (1.0): 9.7 mm. La cabeza
#     queda más grande que los lóbulos, así que va también la que hace juego,
#     abierta.
#   - Ø150 y Ø180: no cierran ni redondas (17 y 23 mm). Abiertas con una boca
#     del 20 % del diámetro no tienen nada al aire, y con la proporción del
#     cuerpo.
TAPAS = {
    95: [(0.80, 0.0)],
    120: [(1.0, 0.0), (0.7355, 0.2)],
    150: [(0.7355, 0.2)],
    180: [(0.7355, 0.2)],
}


# El clic es llave y cerradura: la base de cada módulo lleva dos cuñas hacia
# adentro (ver BOCA_*) y arriba van dos MUESCAS hacia adentro en el mismo
# ángulo, donde entran esas cuñas. La muesca va SÓLO en el labio, desde donde
# arranca para arriba: en el hombro se vería y no hace falta. Simulado con los
# cordones de los dos g-code, la base queda 0.4 mm más alta que sin clic (la
# cuña apoya en la última vuelta del hombro, justo debajo del labio).
#
# Apoyada, la cuña ocupa UNA vuelta del labio: la segunda vuelta de la base ya
# se abrió y no llega. La muesca es esa vuelta a fondo y poco más, del ancho
# de la cuña: la primera prueba (muescas de 1.2-1.6 mm, cuatro vueltas de alto
# y 8 mm de ancho, contra una cuña en punta) dejaba levantar la base 3 mm y
# girarla 4 mm sin tocar nada, y no trababa. Así se levanta ~0.8 y gira ~1 mm.
CLIC_ANCHO = 7.0     # mm, alrededor: la cuña plana (6) con ~0.5 de juego a cada lado
# En altura la muesca entra y sale en RAMPA RECTA, como mucho `CLIC_CORRE` mm
# por vuelta: impresa de un salto (1.2-1.6 mm en una vuelta) la vuelta quedaba
# en el aire por dentro de la de abajo y salía derretida hacia adentro. El
# hombro ya se corre 0.67 por vuelta y sale bien. En el medio, `CLIC_PLANO` a
# fondo, arrancando `CLIC_FONDO` sobre el labio: la vuelta donde queda la cuña.
CLIC_CORRE = 0.55    # mm por vuelta
CLIC_PLANO = 0.8     # mm
CLIC_VUELTA = 0.8    # mm que sube una vuelta en el labio
CLIC_FONDO = 0.5     # mm sobre el arranque del labio: la primera vuelta entera del labio, la de la cuña


# Las pruebas de encastre (`--prueba`): la boca sola y el hombro con el labio,
# para probar el clic en minutos y no en una hora por módulo: la boca clic
# (protuberancias hacia adentro, `--boca-adentro`) contra cada labio clic
# (bolitas hacia afuera, `--clic`). Sin `--boca-adentro` sale la boca lisa.
#   - boca: las primeras vueltas del módulo, igual que en la pieza (sin piso).
#     Es la parte que se apoya en el de abajo; más arriba la pared ya se abrió.
#   - labio: desde un poco debajo del asiento hasta el final, con piso para que
#     se pare solo. Incluye el hombro donde se apoya la boca, así que la prueba
#     asienta igual que dos módulos.
PRUEBA_BOCA_ALTO = 3.2        # mm: 4 vueltas
PRUEBA_LABIO_BAJO = 3.38      # mm de hombro debajo del labio: medido en Ø95, así las vueltas caen donde las del módulo
# La cuña de la boca clic: hacia adentro SÓLO en las dos primeras vueltas, las
# que se apoyan en la cama (la plana y la primera de la espiral). El resto es
# la boca del módulo tal cual. La cuña corta seco (`columna`: el peso depende
# sólo del ángulo y en altura se apaga de golpe a 1.5 radios); el corte cae
# entre el final de la 2.ª vuelta (270°) y el principio de la 3.ª (90°).
# Alrededor es plana (`meseta`): con `suave` era una punta que llegaba a fondo
# en 1 mm de los 6 y bailaba en la muesca.
BOCA_ALTO = 0.85             # mm de silueta donde corta la cuña: medido, 0.80 y 0.90 dejan las dos vueltas
BOCA_ANGULO = 90
BOCA_ANCHO = 6.0              # mm, alrededor; plana en los 3.4 del medio


def con_toques(cmd: list, toques: list, sufijo: str) -> list:
    """Escribe el archivo de toques junto a la pieza y lo pasa con `--toques`."""
    i = cmd.index("--nombre") + 1
    cmd[i] += sufijo
    ruta = os.path.join("output", cmd[i] + ".toques.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"toques": toques}, f, indent=1, ensure_ascii=False)
    return cmd[:i - 1] + ["--toques", ruta] + cmd[i - 1:]


def muesca(s, hondo: float, angulo: float) -> dict:
    """Dos muescas enfrentadas (`angulo` y `angulo`+180) donde entran las cuñas."""
    rampa = hondo / CLIC_CORRE * CLIC_VUELTA
    # El fondo arranca a la misma altura sea cual sea la profundidad, en la
    # vuelta donde queda la cuña; la rampa de entrada va por debajo. Las dos
    # piezas son espirales: girar la base `giro` grados para que su cuña caiga
    # acá corre las vueltas del labio esa fracción de vuelta respecto de la
    # cuña, y el fondo se corre con ellas.
    giro = (angulo - BOCA_ANGULO + 90) % 180 - 90
    fondo = s.labio_desde + CLIC_FONDO + giro / 360 * CLIC_VUELTA
    medio = CLIC_PLANO / 2 + rampa
    return {"tipo": "jalar", "forma": "ranura", "caida": "pico",
            "rampa_u": 0.4, "rampa_v": rampa / medio,
            "angulo": angulo, "simetria": 2,
            "t": (fondo + CLIC_PLANO / 2) / s.altura, "radio_t": medio / s.altura,
            "radio_grados": math.degrees(CLIC_ANCHO / 2 / s.radio_labio),
            "fuerza": -hondo, "nota": f"muesca de {hondo:g} mm para la cuña de la base"}


def cuna(s, r: float, adentro: float) -> dict:
    """Las dos cuñas de la base, hacia adentro en sus dos primeras vueltas."""
    return {"tipo": "jalar", "forma": "columna", "caida": "meseta",
            "angulo": BOCA_ANGULO, "simetria": 2, "t": 0.0,
            "radio_t": BOCA_ALTO / 1.5 / s.altura,
            "radio_grados": math.degrees(BOCA_ANCHO / 2 / (r * 0.6405)),
            "fuerza": -adentro, "nota": "cuña hacia adentro en las dos primeras vueltas"}


def clic(cmd: list, s, r: float, hondo: float, adentro: float) -> list:
    """El módulo: las dos muescas arriba y, con `adentro`, las dos cuñas abajo."""
    toques = [muesca(s, hondo, BOCA_ANGULO)] + ([cuna(s, r, adentro)] if adentro else [])
    return sin_mezcla(con_toques(cmd, toques, f"_clic{hondo:g}" + (f"_cuna{adentro:g}" if adentro else "")))


def muestrario(cmd: list, s, hondos: list) -> list:
    """
    La prueba: TODAS las profundidades en una sola boca. Cada una es un par
    enfrentado (la base tiene dos cuñas enfrentadas) y los pares van cada
    180/n grados, arrancando a 30° de la costura (0°, +X): mirando desde arriba
    y girando antihorario desde la costura, de la menos honda a la más honda.
    """
    paso = 180.0 / len(hondos)
    toques = [muesca(s, h, paso / 2 + k * paso) for k, h in enumerate(sorted(hondos))]
    return sin_mezcla(con_toques(cmd, toques, "_muescas" + "_".join(f"{h:g}" for h in sorted(hondos))))


def sin_mezcla(cmd: list) -> list:
    """
    La subida sobre la silueta lisa (si no, el borde de la muesca se lee como
    pared acostada y las vueltas de alrededor suben menos) y sin la mezcla de
    las primeras capas (con relieve en la pieza, la mezcla toca las primeras
    vueltas aunque no tengan nada). Lo mismo que lleva la cuña de la base.
    """
    i = cmd.index("--nombre")
    return cmd[:i] + ["--pendiente-silueta", "--capas-transicion", "0"] + cmd[i:]


def comando(s, r: float, nombre: str, receta: list, **ps) -> list:
    return [sys.executable, "-m", "lamparas.bowls", "zigzag", "--silueta", "gusano_modulo",
            *[x for k, v in ps.items() for x in ("--ps", f"{k}={v:g}")],
            *receta, "--radio-max", f"{r:g}", "--altura", f"{s.altura:.2f}",
            "--nombre", nombre]


def pruebas(d: float, a) -> None:
    r = d / 2.0
    base = dict(labio=a.labio, holgura=a.holgura, achatado=0.7355)
    entero = gusano_modulo(radio_max=r, **base)
    carpeta = "gusano-modular/pruebas-clic"

    s = gusano_modulo(radio_max=r, hasta=PRUEBA_BOCA_ALTO, **base)
    cmd = comando(s, r, f"{carpeta}/prueba_boca_D{d:g}", RECETA, hasta=PRUEBA_BOCA_ALTO, **base)
    if not a.boca_adentro:
        subprocess.run(cmd, check=True)
    for f in a.boca_adentro:
        t = cuna(s, r, f)
        # Sin la mezcla de las primeras capas (`--capas-transicion`): apaga la
        # deformación justo en las vueltas donde va esta protuberancia. Y la
        # subida medida sobre la silueta lisa (`--pendiente-silueta`): si no, el
        # salto de radio donde termina la protuberancia se lee como pared
        # acostada y la vuelta siguiente casi no sube (0.05 mm en vez de 0.44).
        sin_mezcla = con_toques(list(cmd), [t], f"_clic{f:g}")
        i = sin_mezcla.index("--nombre")
        subprocess.run(sin_mezcla[:i] + ["--capas-transicion", "0", "--pendiente-silueta"]
                       + sin_mezcla[i:], check=True)

    desde = entero.labio_desde - PRUEBA_LABIO_BAJO
    s = gusano_modulo(radio_max=r, desde=desde, **base)
    con_piso = [x for x in RECETA if x != "--sin-base"]
    cmd = comando(s, r, f"{carpeta}/prueba_labio_D{d:g}", con_piso, desde=desde, **base)
    if a.clic:
        subprocess.run(muestrario(list(cmd), s, a.clic), check=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("diametros", nargs="*", type=float, default=[58, 78, 95])
    p.add_argument("--holgura", type=float, default=0.6)
    p.add_argument("--labio", type=float, default=6.0)
    p.add_argument("--solo-modulos", action="store_true",
                   help="no rehacer las tapas: no llevan labio ni holgura")
    p.add_argument("--clic", type=float, nargs="+", default=[], metavar="MM",
                   help="qué tan honda es cada muesca de arriba, en mm de radio. Varios "
                        "valores = una pieza por valor. Las tapas nunca lo llevan")
    p.add_argument("--prueba", action="store_true",
                   help="en vez de módulos y tapas, las piezas cortas de prueba de encastre: "
                        "una boca por cada --boca-adentro (o la lisa) y un labio por cada --clic")
    p.add_argument("--boca-adentro", type=float, nargs="+", default=[], metavar="MM",
                   help="la base clic, con dos cuñas hacia adentro en las primeras vueltas, de "
                        "estos mm. Con --prueba, una base por valor; en los módulos con --clic, "
                        "un solo valor")
    a = p.parse_args()
    if not a.prueba and len(a.boca_adentro) > 1:
        p.error("en los módulos --boca-adentro lleva un solo valor")
    adentro = a.boca_adentro[0] if a.boca_adentro else 0.0

    for d in a.diametros:
        if a.prueba:
            pruebas(d, a)
            continue
        r = d / 2.0
        piezas = [("modulo", 0, 0.7355, 0.0)]
        if not a.solo_modulos:
            piezas += [("tapa", 1, ach, boca)
                       for ach, boca in TAPAS.get(d, [(0.7355, 0.0)])]
        for nombre, tapa, ach, boca in piezas:
            s = gusano_modulo(radio_max=r, labio=a.labio, holgura=a.holgura,
                              tapa=tapa, achatado=ach, boca=boca)
            cmd = [sys.executable, "-m", "lamparas.bowls", "zigzag",
                   "--silueta", "gusano_modulo",
                   "--ps", f"tapa={tapa}", "--ps", f"labio={a.labio:g}",
                   "--ps", f"holgura={a.holgura:g}", "--ps", f"achatado={ach:g}",
                   "--ps", f"boca={boca:g}",
                   *RECETA,
                   "--radio-max", f"{r:g}", "--altura", f"{s.altura:.2f}",
                   "--nombre", f"gusano-modular/{nombre}_D{d:g}_{s.altura:.0f}mm"
                               + (f"_boca{d * boca:.0f}" if boca else "")
                               + ("" if tapa else f"_labio{a.labio:g}")]
            for c in ([None] if tapa or not a.clic else a.clic):
                subprocess.run(clic(list(cmd), s, r, c, adentro) if c else cmd, check=True)


if __name__ == "__main__":
    main()
