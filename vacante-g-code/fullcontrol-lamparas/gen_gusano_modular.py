"""
Genera el gusano modular en `output/gusano-modular/`: por cada diámetro, un
MÓDULO (un lóbulo con labio, se imprimen los que hagan falta y se apilan) y
una TAPA (el mismo lóbulo cerrado en cúpula).

    python gen_gusano_modular.py                 # Ø58, Ø78 y Ø95
    python gen_gusano_modular.py 120 150 180     # los grandes
    python gen_gusano_modular.py 78 --holgura 0.4
    python gen_gusano_modular.py --labio 10 --solo-modulos
    python gen_gusano_modular.py 95 --solo-modulos --clic 1.0

`--clic` le pone al labio dos bolitas enfrentadas, pegadas al hombro: el
anillo de la boca del módulo de arriba pasa por encima y queda trabado debajo.
La boca no cambia, así que un módulo con clic encaja en uno sin clic y al revés.

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


# Las bolitas del clic. Arrancan apenas arriba de donde empieza el labio
# —pegadas al hombro— porque es lo único que toca el módulo de arriba: se
# apoya en el hombro con el anillo de su primera capa (~0.8 mm de alto) y su
# pared se abre enseguida (en Ø95, 2.5 mm de luz a 1.2 mm del asiento). Más
# arriba en el labio no tocarían nada.
#
# El labio arranca ~1 mm sobre el asiento, así que el anillo de la boca queda
# justo debajo de la bolita. Una protuberancia hacia ADENTRO en la boca, que era
# la otra opción, cae contra el hombro curvo y deja el módulo levantado sobre
# las dos bolitas.
#
# 3.2 mm de alto porque en el labio las vueltas suben de a 0.8: con menos, la
# espiral puede pasar 0.4 mm al costado del centro y la bolita sale a medias.
CLIC_ALTO = 3.2      # mm
CLIC_ANCHO = 6.0     # mm, alrededor
# Dónde arranca la bolita respecto del labio. El anillo de la boca de arriba
# termina ~0.25 mm DEBAJO del arranque del labio (el labio empieza ~1.05 sobre
# el asiento y el anillo mide 0.8), así que la bolita puede empezar un pelo
# antes del labio sin levantar el módulo. Más arriba deja juego: medido con la
# bolita arrancando 0.05 sobre el labio, el anillo subía ~1 mm antes de trabar.
# No se puede hacer más petisa: el radio no puede crecer más de ~0.6 mm por
# vuelta (sube 0.8) o la vuelta no apoya, y con 1.1 mm de bolita eso son dos
# vueltas de subida y dos de bajada.
CLIC_SOBRE_LABIO = -0.15  # mm


# Las pruebas de encastre (`--prueba`): la boca sola y el hombro con el labio,
# para probar el clic en minutos y no en una hora por módulo: la boca va
# encima de cada labio con bolitas. El labio liso no se saca, es el de siempre.
#   - boca: las primeras vueltas del módulo, igual que en la pieza (sin piso).
#     Es la parte que se apoya en el de abajo; más arriba la pared ya se abrió.
#   - labio: desde un poco debajo del asiento hasta el final, con piso para que
#     se pare solo. Incluye el hombro donde se apoya la boca, así que la prueba
#     asienta igual que dos módulos.
PRUEBA_BOCA_ALTO = 3.2        # mm: 4 vueltas
PRUEBA_LABIO_BAJO = 3.0       # mm de hombro debajo del labio (el asiento queda ~2 mm arriba del piso)
# La protuberancia hacia adentro en la boca —la otra idea—, para poder
# comparar: las dos primeras vueltas.
BOCA_ADENTRO_CENTRO = 0.8     # mm desde la boca
BOCA_ADENTRO_MEDIO = 1.6      # mm


def bolitas(z: float, medio: float, radio: float, fuerza: float, s, nota: str) -> dict:
    """Dos bolitas enfrentadas centradas a `z` mm del arranque de la pieza."""
    return {"tipo": "jalar", "forma": "circulo", "caida": "suave",
            "angulo": 0, "simetria": 2,
            "t": z / s.altura, "radio_t": medio / s.altura,
            "radio_grados": math.degrees(CLIC_ANCHO / 2 / radio),
            "fuerza": fuerza, "nota": nota}


def con_toques(cmd: list, toques: list, sufijo: str) -> list:
    """Escribe el archivo de toques junto a la pieza y lo pasa con `--toques`."""
    i = cmd.index("--nombre") + 1
    cmd[i] += sufijo
    ruta = os.path.join("output", cmd[i] + ".toques.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"toques": toques}, f, indent=1, ensure_ascii=False)
    return cmd[:i - 1] + ["--toques", ruta] + cmd[i - 1:]


def clic(cmd: list, s, fuerza: float) -> list:
    """Las dos bolitas del clic, pegadas al arranque del labio."""
    medio = CLIC_ALTO / 2
    t = bolitas(s.labio_desde + CLIC_SOBRE_LABIO + medio, medio, s.radio_labio, fuerza, s,
                "clic: dos bolitas en la base del labio")
    return con_toques(cmd, [t], f"_clic{fuerza:g}")


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
    subprocess.run(cmd, check=True)
    for f in a.boca_adentro:
        t = bolitas(BOCA_ADENTRO_CENTRO, BOCA_ADENTRO_MEDIO, r * 0.6405, -f, s,
                    "protuberancia hacia adentro en la boca")
        # Sin la mezcla de las primeras capas (`--capas-transicion`) ni la
        # primera vuelta lisa (`--capas-base`): las dos apagan la deformación
        # justo en las vueltas donde va esta protuberancia.
        sin_mezcla = con_toques(list(cmd), [t], f"_adentro{f:g}")
        i = sin_mezcla.index("--nombre")
        subprocess.run(sin_mezcla[:i] + ["--capas-transicion", "0", "--capas-base", "0"]
                       + sin_mezcla[i:], check=True)

    desde = entero.labio_desde - PRUEBA_LABIO_BAJO
    s = gusano_modulo(radio_max=r, desde=desde, **base)
    con_piso = [x for x in RECETA if x != "--sin-base"]
    cmd = comando(s, r, f"{carpeta}/prueba_labio_D{d:g}", con_piso, desde=desde, **base)
    for c in a.clic:
        subprocess.run(clic(list(cmd), s, c), check=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("diametros", nargs="*", type=float, default=[58, 78, 95])
    p.add_argument("--holgura", type=float, default=0.6)
    p.add_argument("--labio", type=float, default=6.0)
    p.add_argument("--solo-modulos", action="store_true",
                   help="no rehacer las tapas: no llevan labio ni holgura")
    p.add_argument("--clic", type=float, nargs="+", default=[], metavar="MM",
                   help="cuánto sale cada bolita del labio, en mm de radio. Con la holgura de "
                        "0.6, 1.0 deja 0.4 de traba. Varios valores = una pieza por valor. "
                        "Las tapas nunca lo llevan")
    p.add_argument("--prueba", action="store_true",
                   help="en vez de módulos y tapas, las piezas cortas de prueba de encastre: "
                        "la boca lisa y un labio por cada --clic")
    p.add_argument("--boca-adentro", type=float, nargs="+", default=[], metavar="MM",
                   help="con --prueba: también la boca con dos protuberancias hacia adentro "
                        "en las primeras vueltas, para comparar contra el clic del labio")
    a = p.parse_args()

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
                subprocess.run(clic(list(cmd), s, c) if c else cmd, check=True)


if __name__ == "__main__":
    main()
